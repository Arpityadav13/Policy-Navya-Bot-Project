# 🏛 NyayaBot — Policy-to-Citizen AI Chatbot

> Converts complex government policy documents into simple explanations using RAG + Claude AI

![NyayaBot Banner](https://img.shields.io/badge/NyayaBot-v1.0-gold?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PC9zdmc+)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)](https://python.org)
[![Claude](https://img.shields.io/badge/Claude-Sonnet-orange?style=flat-square)](https://anthropic.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?style=flat-square)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

## 📋 Overview

NyayaBot is a **Retrieval-Augmented Generation (RAG) chatbot** that helps Indian citizens understand complex government welfare schemes in plain language. It answers questions about eligibility, benefits, and application processes in **22 Indian languages**.

### Key Features
- 🧠 **RAG Architecture** — FAISS vector search + Claude AI
- 🌐 **Multilingual** — Hindi, Tamil, Bengali, Telugu, Marathi, Gujarati + 16 more
- 📄 **PDF Upload** — Index any policy document on-the-fly
- 🤖 **Telegram Bot** — Deploy as WhatsApp/Telegram chatbot
- 📊 **Dashboard** — Usage analytics and monitoring
- 🇮🇳 **200+ Schemes** — Pre-loaded Indian government schemes

---

## 🗂 Project Structure

```
policy-bot/
├── frontend/                  # Web Interface
│   ├── index.html             # Main chat interface
│   ├── dashboard.html         # Analytics dashboard
│   ├── style.css              # Styling (dark theme)
│   └── app.js                 # Frontend logic + Claude API
│
├── backend/                   # API Server
│   └── server.py              # FastAPI REST API
│
├── rag/                       # RAG Engine
│   └── engine.py              # Core RAG: embed + retrieve + generate
│
├── bot/                       # Bot Interfaces
│   └── telegram_bot.py        # Telegram integration
│
├── data/
│   ├── policies/              # ← Add policy PDFs here
│   ├── training/
│   │   └── training_data.json # Pre-built knowledge base
│   └── faiss_index/           # Auto-generated vector index
│
├── config/
│   └── settings.json          # App configuration
│
├── scripts/
│   └── ingest.py              # Batch document ingestion
│
├── requirements.txt
├── .env.example               # Environment variables template
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/your-org/nyayabot.git
cd policy-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
nano .env
```

### 3. Add Policy Documents (Optional)

```bash
# Add PDF policy documents to data/policies/
cp your_scheme.pdf data/policies/

# Or run ingestion script
python scripts/ingest.py
```

### 4. Start the Server

```bash
cd backend
python server.py
# Server starts at http://localhost:8000
```

### 5. Open the Frontend

Option A — Open directly in browser:
```
open frontend/index.html
```

Option B — Serve via the FastAPI server:
```
http://localhost:8000
```

---

## 🤖 Telegram Bot Setup

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Copy the token to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   ```
3. Run the bot:
   ```bash
   python bot/telegram_bot.py
   ```

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | Claude Sonnet (Anthropic) |
| RAG Framework | LlamaIndex + custom pipeline |
| Vector Store | FAISS (CPU) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| PDF Processing | PyMuPDF |
| Translation | Google Translate API + IndicTrans2 |
| API Server | FastAPI + uvicorn |
| Bot Interface | python-telegram-bot |
| Frontend | Vanilla HTML/CSS/JS |

---

## 📡 API Reference

### POST /api/chat
```json
{
  "message": "PM Kisan ke liye eligible hoon?",
  "language": "hi",
  "session_id": "user123",
  "history": []
}
```

Response:
```json
{
  "answer": "PM-KISAN के लिए पात्रता...",
  "language": "hi",
  "sources": ["pm_kisan_guidelines.txt"],
  "scheme_names": ["PM-KISAN"],
  "retrieval_time_ms": 45.2,
  "llm_time_ms": 1240.5,
  "total_time_ms": 1285.7,
  "confidence": 0.89
}
```

### POST /api/upload-policy
```
multipart/form-data:
  file: <pdf_file>
  scheme_name: "My Custom Scheme"
```

### GET /api/schemes
Returns list of all indexed schemes.

### GET /api/search?q=query&top_k=5
Semantic search across policy documents.

---

## 🌐 Supported Languages

Hindi (hi), Tamil (ta), Bengali (bn), Telugu (te), Marathi (mr), Gujarati (gu), Kannada (kn), Malayalam (ml), Punjabi (pa), Urdu (ur), Odia (or), Assamese (as), Sindhi (sd), Konkani (kok), Manipuri (mni), Bodo (brx), Dogri (doi), Kashmiri (ks), Maithili (mai), Sanskrit (sa), Santhali (sat), Nepali (ne)

---

## 🏗 Architecture

```
User Query
    │
    ▼
[Language Detection] ──→ Translate to English (if needed)
    │
    ▼
[Embedding Engine] ──→ sentence-transformers
    │
    ▼
[FAISS Vector Search] ──→ Top-K relevant chunks
    │
    ▼
[Context Assembly] ──→ Retrieved policy sections
    │
    ▼
[Claude AI (RAG)] ──→ Generate explanation
    │
    ▼
[Translation] ──→ Back to user's language
    │
    ▼
Response to User
```

---

## 📊 Performance

- Average retrieval time: ~50ms
- Average LLM response: ~1.2s
- Vector store size: ~200MB (200 schemes)
- Supported concurrent users: 100+ (with FastAPI)

---

## 🤝 Contributing

1. Fork the repository
2. Add policy documents to `data/policies/`
3. Add QA pairs to `data/training/training_data.json`
4. Submit a pull request

---

## 📄 License

MIT License — Free for personal and commercial use.

---

## 🙏 Acknowledgements

Built for Indian citizens. Powered by Claude AI (Anthropic).
Policy data sourced from official government websites.

