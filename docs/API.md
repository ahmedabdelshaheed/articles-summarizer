# API Documentation

Base URL: `https://your-ngrok-url.ngrok-free.app`

---

## Endpoints

### POST `/chat`

The single endpoint for all interactions — handles both chat messages and article processing.

---

#### Request

**Headers**

```
Content-Type: application/json
```

**Body**

```json
{
  "text": "string",
  "is_article": false
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | ✅ | — | The user's message or the article text to process |
| `is_article` | boolean | ❌ | `false` | Set to `true` to trigger article rewriting mode |

---

#### Response

```json
{
  "content": "string",
  "image": "string | null"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `content` | string | The AI-generated response (chat reply or article rewrite) |
| `image` | string \| null | Base64-encoded PNG image (`data:image/png;base64,...`) — only returned in article mode, otherwise `null` |

---

## Examples

### 1. Chat Message

**Request**
```json
POST /chat

{
  "text": "What is machine learning?",
  "is_article": false
}
```

**Response**
```json
{
  "content": "Machine learning is a branch of AI where systems learn from data...",
  "image": null
}
```

---

### 2. Article Processing

**Request**
```json
POST /chat

{
  "text": "OpenAI has released GPT-5 with major improvements in reasoning...",
  "is_article": true
}
```

**Response**
```json
{
  "content": "🚀 The AI world just changed forever.\n\nGrab your coffee — here's what just dropped...",
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}
```

---

## Error Responses

| Status Code | Description |
|-------------|-------------|
| `422` | Validation error — missing or wrong field types |
| `500` | Server error — AI model or image generation failed |

**500 Error body example:**
```json
{
  "detail": "Connection error to inference API"
}
```

---

## CORS

The API accepts requests from any origin (`*`). All HTTP methods and headers are allowed.

---

## Notes

- **Chat memory** is global and shared across all sessions. It resets when the server restarts.
- In chat mode, only the **last 10 messages** are sent to the model to manage context length.
- The image returned is always a **PNG encoded as base64** — no external URL is used.
- Temperature for article mode is `0.3` (focused), for chat mode is `0.7` (creative).
