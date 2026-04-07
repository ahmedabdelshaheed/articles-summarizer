import os
from dotenv import load_dotenv
load_dotenv()


from huggingface_hub import InferenceClient
import base64
from io import BytesIO


def get_ai_image(prompt: str) -> str:
    client = InferenceClient(
        provider="hf-inference",
        api_key=os.getenv("HF_TOKEN")
    )

    image = client.text_to_image(
        prompt,
        model="black-forest-labs/FLUX.1-schnell"
    )

    # تحويل لـ base64 عشان يتبعت بسهولة في الـ API response
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{img_base64}"

