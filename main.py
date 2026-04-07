
import warnings
warnings.filterwarnings('ignore')
import os
from dotenv import load_dotenv
load_dotenv()


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pyngrok import ngrok
import uvicorn


import instructor
from groq import Groq


from llm_client import *
from call_HF_FLUX import *



app = FastAPI()

# --- 1. تفعيل الـ CORS لضمان اتصال المتصفح بالسيرفر ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. تعديل الـ Model لاستقبال الـ session_id ---
class ChatRequest(BaseModel):
    text: str
    session_id: str  # المعرف الفريد الذي يرسله المتصفح للفصل بين المستخدمين
    is_article: bool = False 

# --- 3. إدارة الذاكرة المنفصلة (Global Dictionary) ---
# بدلاً من قائمة واحدة لكل الناس، نستخدم قاموساً يخزن تاريخ كل session_id على حدة
all_chats = {}

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    global all_chats
    
    # الحصول على المعرف الفريد من الطلب
    s_id = request.session_id

    # إذا كان هذا المستخدم جديداً (أو فتح تبويب جديد)، ننشئ له مساحة ذاكرة خاصة
    if s_id not in all_chats:
        all_chats[s_id] = []
    
    # استخراج تاريخ المحادثة الخاص بهذا المستخدم فقط
    user_history = all_chats[s_id]

    try:
        # الحالة الأولى: طلب تلخيص (Add Article)
        if request.is_article:
            summary_prompt = request.text
            system_prmpt = """You are a Storytelling Content Creator. Your goal is to rewrite the provided text into a smooth, engaging social media post (English).

                            Follow this exact logical sequence:
                                1. THE HOOK: Start with a catchy, bold opening sentence that grabs attention immediately.
                                2. THE SET UP: Briefly set the stage. Why are we talking about this? Use a friendly tone.
                                3. THE PROGRESSION (The Chain): Break the main event/topic into a logical sequence of ideas:
                                  - Use numbered points or bold sub-headings.
                                  - Each point must naturally lead to the next (Idea A leads to Idea B).
                                  - Use simple, everyday analogies to explain each idea clearly.
                                4. THE "SO WHAT?": Explain the impact or the final result of this story in a simple way.
                                5. THE REFLECTION: Close with a personal or thought-provoking question to the audience.
                                Avoid category titles (e.g., 'THE SO WHAT', 'THE REFLECTION')

                            STYLISH RULES:
                                - Tone: Conversational, friendly, and "Human" (Not robotic).
                                - Formatting: Use short paragraphs and emojis for readability.
                                - Language: Output must be in English."""

            # استدعاء الموديل للتلخيص
            summary_result = production_client.chat(
                messages=[
                    {"role": "system", "content": system_prmpt},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.3
            )
            summary_text = summary_result.get('content', '')

            # إضافة الملخص لذاكرة هذا المستخدم فقط
            user_history.append({"role": "user", "content": f"[Article Submitted]: {request.text[:100]}..."})
            user_history.append({"role": "assistant", "content": summary_text})

            image_system_prompt = """You are an expert prompt engineer for FLUX.1.
                                      Create a detailed, high-quality visual description based on the article summary.
                                      Focus on composition, realistic textures, and specific lighting.
                                      Keep the prompt concise but descriptive.
                                      Output ONLY the prompt in English."""

            # توليد برومبت الصورة
            prompt_result = production_client.chat(
                messages=[
                    {"role": "system", "content": image_system_prompt},
                    {"role": "user", "content": summary_text}
                ]
            )
            image_prompt = prompt_result.get('content', '')

            # الحصول على الصورة
            image = get_ai_image(image_prompt)

            return {"content": summary_text, "image": image}

        # الحالة الثانية: دردشة عادية (Chat)
        else:
            # إضافة رسالة المستخدم الحالية لذاكرته الخاصة
            user_history.append({"role": "user", "content": request.text})

            # إرسال آخر 10 رسائل من تاريخ هذا المستخدم لضمان السياق
            chat_result = production_client.chat(
                messages=user_history[-10:],
                temperature=0.7
            )
            bot_response = chat_result.get('content', '')

            # إضافة رد البوت لذاكرة هذا المستخدم
            user_history.append({"role": "assistant", "content": bot_response})

            return {"content": bot_response, "image": None}

    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- تشغيل السيرفر ---
NGROK_TOKEN = os.getenv("NGROK_AUTH_TOKEN")
if __name__ == "__main__":
    try:
        if NGROK_TOKEN:
            ngrok.set_auth_token(NGROK_TOKEN) 
            public_url = ngrok.connect(8000).public_url
            print(f" * Public URL: {public_url}")
    except Exception as e:
        print(f" * Ngrok failed to start: {e}")
        print(" * Working on Localhost only.")

    uvicorn.run(app, host="127.0.0.1", port=8000)