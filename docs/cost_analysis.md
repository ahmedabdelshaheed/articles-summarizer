---

# 📊 Cost Analysis Report: Summarizer Chatbot (2026)

## 1. Usage Profile (Per Session)
Based on a scenario involving: **(1 Article of 800 words + 2 Follow-up Questions + 400-token Summary)**.

| Stage | Input Tokens | Output Tokens | Cumulative Total |
| :--- | :--- | :--- | :--- |
| **Initial Summary Request** | 1,070 | 400 | 1,470 |
| **First Question** | 445 | 65 | 510 |
| **Second Question** | 530 | 65 | 595 |
| **Average Per Request** | **682 Tokens** | **177 Tokens** | **859** |

---

## 2. Daily Operational Statistics
Calculated based on a realistic volume of **100 Requests per day**:

* **Total Daily Input Tokens:** 68,200
* **Total Daily Output Tokens:** 17,700
* **Monthly Request Volume:** 3,000

---

## 3. Comparative Model Costs
Based on your verified `MODEL_CONFIGS`:

| Model | Provider | Daily Cost (100 Req) | Monthly Cost (30 Days) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **GPT-OSS-120b** | Groq | **$0.00** | **$0.00** | 🆓 Free/Tier 1 |
| **Gemini-3-Flash** | Google | **$0.087** | **$2.61** | 💎 Economic |
| **GPT-4o** | OpenAI | **$0.347** | **$10.42** | 🚀 Premium |

---
