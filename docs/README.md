A conversational AI web app that supports smart chat and automatic article rewriting into engaging social media posts — with AI-generated images.

---

## Features

- **Chat Mode** — multi-turn conversation with memory (last 10 messages kept in context)
- **Article Mode** — paste any English article and get a structured, storytelling social media post
- **AI Image Generation** — every article summary comes with an auto-generated relevant image via FLUX.1-schnell
- **Markdown rendering** — bot responses support full markdown formatting
- **Copy to clipboard** — one-click copy for any bot response
- **Streaming-style typing effect** — responses appear character by character

---



## 🚀 Core AI Architecture

The system utilizes a dual-model strategy to ensure high-quality content generation and 100% service availability:
### 1. Primary Reasoning Engine
* **Model:** `openai/gpt-oss-120b`
* **Provider:** `Groq`
* **Type:** Native Reasoning Model (MoE Architecture).

### 2. Smart Fallback Engine
* **Model:** `google/gemini-3-flash-preview`
* **Provider:** `Google AI studio`
* **Type:** Adaptive Reasoning Model.


---


## Tech Stack

| Layer            | Technology                                          |
|------------------|-----------------------------------------------------|
| Backend          | Python, FastAPI                                     |
| AI Model         | Custom `production_client` (chat)                   |
| Image Generation | Hugging Face `FLUX.1-schnell` via `InferenceClient` |
| Tunneling        | Ngrok                                               |
| Frontend         | HTML, Tailwind CSS, Vanilla JS                      |
| Markdown         | `marked.js`                                         |

---

## Setup & Installation

### 1. Install dependencies

```bash
python -m pip install fastapi uvicorn nest-asyncio pyngrok huggingface-hub pillow python-dotenv pillow huggingface_hub instructor pydantic google-generativeai
```

### 2. Configure API keys

Inside the Python file, set your keys:

```python
# Hugging Face (image generation)
api_key = "your_hf_api_key"

# Ngrok (public URL tunnel)
ngrok.set_auth_token("your_ngrok_token")
```

### 3. Run the server

```bash
python app.py
```

After running, the terminal will print your public URL:

```
🌍 Your Public URL: https://xxxx.ngrok-free.app
🔗 Copy this to your HTML 'API_URL': https://xxxx.ngrok-free.app/chat
```

### 4. Connect the frontend

Open `index.html` and update the API URL at the top of the script:

```javascript
const API_URL = "https://your-ngrok-url.ngrok-free.app/chat";
```

Then open `index.html` in any browser.

---

## Usage

### Chat Mode
Type any message in the input bar and press **Send** or hit **Enter**.

### Article Mode
1. Click the **Article** button
2. Paste your English article in the modal
3. Click **Process Article**
4. Receive a storytelling social media post + an AI-generated image






## Notes

- Chat history is stored **in-memory** (resets when server restarts)
- CORS is open (`allow_origins=["*"]`) — restrict this in production
- Ngrok free tier URL changes on every restart — update `API_URL` in HTML accordingly
