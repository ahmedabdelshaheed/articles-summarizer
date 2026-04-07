# 🏗️ Architecture Document — Social Media Post Generator API

## Overview

A FastAPI-based backend that takes raw articles or chat messages and transforms them into engaging social media posts, complete with AI-generated images. Exposed publicly via Ngrok tunneling.

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                        CLIENT                           │
│              (Browser / Mobile / Frontend)              │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP POST /chat
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    NGROK TUNNEL                         │
│              Public URL → localhost:8000                │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  FASTAPI APPLICATION                    │
│                                                         │
│  ┌──────────────┐        ┌──────────────────────────┐  │
│  │ CORS Middle  │──────▶ │   POST /chat endpoint    │  │
│  │    ware      │        │                          │  │
│  └──────────────┘        │  is_article = True?      │  │
│                          │     ┌─────┴──────┐       │  │
│                          │   YES            NO       │  │
│                          │     ▼             ▼       │  │
│                          │  [Article      [Chat      │  │
│                          │   Flow]        Flow]      │  │
│                          └──────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Request Flow

### Flow 1 — Article → Social Media Post + Image

```
User sends article text  (is_article = True)
        │
        ▼
┌───────────────────────┐
│  LLM (production_     │  ← Groq / Instructor client
│  client.chat())       │     System Prompt: Storytelling Creator
│                       │     Generates structured post with:
│  - Hook               │       Hook, Setup, Progression,
│  - Setup              │       So What, Reflection
│  - Progression        │
│  - So What            │
│  - Reflection         │
└──────────┬────────────┘
           │  summary_text
           ▼
┌───────────────────────┐
│  LLM (production_     │  ← Groq / Instructor client
│  client.chat())       │     System Prompt: FLUX Prompt Engineer
│                       │     Generates image description
│  Image Prompt         │
└──────────┬────────────┘
           │  image_prompt
           ▼
┌───────────────────────┐
│  HuggingFace          │  ← InferenceClient
│  FLUX.1-schnell       │     text_to_image()
│  Image Generation     │
└──────────┬────────────┘
           │  base64 PNG
           ▼
┌───────────────────────┐
│  Response             │
│  { content, image }   │  ← JSON response to client
└───────────────────────┘
```

### Flow 2 — Chat (Conversational)

```
User sends message  (is_article = False)
        │
        ▼
┌───────────────────────┐
│  Append to            │  ← Global chat_history list
│  chat_history         │     (persists across requests)
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│  LLM (production_     │  ← Last 10 messages sent for context
│  client.chat())       │     temperature = 0.7
└──────────┬────────────┘
           │  bot_response
           ▼
┌───────────────────────┐
│  Append bot response  │
│  to chat_history      │
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│  Response             │
│  { content,           │
│    image: null }      │
└───────────────────────┘
```

---

## Component Breakdown

### 1. FastAPI App (`app`)
- **Framework**: FastAPI
- **CORS**: Open (`allow_origins=["*"]`) — allows any client origin
- **Port**: `8000` on localhost
- **Endpoints**: Single endpoint `POST /chat`

### 2. Request Model (`ChatRequest`)
| Field       | Type   | Default | Description                    |
|-------------|--------|---------|--------------------------------|
| `text`      | `str`  | —       | Article content or chat message |
| `is_article`| `bool` | `False` | Controls which flow is triggered |

### 3. Response Model
| Field     | Type            | Description                       |
|-----------|-----------------|-----------------------------------|
| `content` | `str`           | Generated post or chat reply      |
| `image`   | `str` or `None` | Base64-encoded PNG (article only) |

### 4. LLM Client (`production_client`)
- Defined in `llm_client.py` (external module)
- Wraps **Groq** + **Instructor** for structured output
- Two temperature modes:
  - `0.3` → Article summarization (focused, deterministic)
  - `0.7` → Chat responses (creative, varied)

### 5. Image Generation (`get_ai_image`)
- Provider: **HuggingFace Inference API**
- Model: `black-forest-labs/FLUX.1-schnell`
- Output: Base64-encoded PNG string (`data:image/png;base64,...`)
- Auth: `HF_TOKEN` environment variable

### 6. Memory (`chat_history`)
- Global Python list — persists for the lifetime of the server process
- Stores `{"role": "user/assistant", "content": "..."}` dicts
- Context window: last 10 messages sent per request
- **Note**: Resets on server restart (no persistent storage)

### 7. Ngrok Tunnel
- Authenticates via `NGROK_AUTH_TOKEN` env variable
- Exposes `localhost:8000` as a public HTTPS URL
- Fails gracefully — server still runs locally if Ngrok fails

---

## Environment Variables

| Variable          | Used By             | Description                  |
|-------------------|---------------------|------------------------------|
| `HF_TOKEN`        | `get_ai_image()`    | HuggingFace API key          |
| `NGROK_AUTH_TOKEN`| Ngrok setup         | Ngrok authentication token   |
| `GROQ_API_KEY`    | `production_client` | Groq API key                 |

---

## External Dependencies

| Library            | Purpose                              |
|--------------------|--------------------------------------|
| `fastapi`          | Web framework                        |
| `uvicorn`          | ASGI server                          |
| `pyngrok`          | Ngrok tunnel management              |
| `huggingface_hub`  | FLUX image generation                |
| `groq`             | LLM inference (fast Llama/Mixtral)   |
| `instructor`       | Structured LLM output via Pydantic   |
| `python-dotenv`    | `.env` file loading                  |
| `pydantic`         | Request/response data validation     |

---
