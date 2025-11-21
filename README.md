# 🚦 Trafico Bot

**Automated Telegram bot for adult content management**

## ✨ Features
- 🤖 Central Telegram bot for video uploads and metadata handling
- 🧠 Gemini AI for automatic caption and SEO‑optimized tag generation
- ☁️ Supabase cloud database for robust storage and scheduling
- 📅 Smart scheduler that auto‑assigns posting times per model and platform
- 🔄 Multi‑platform support (XXXFollow, MyClub, RedGifs, Cams, …)

## 🏗️ Architecture
- `src/project/bot_central.py` – Core Telegram bot logic
- `src/project/caption.py` – Gemini integration and caption/tag generation
- `src/project/scheduler.py` – Publication time calculation
- `src/project/supabase_client.py` – Database abstraction layer
- `create_model_table.js` – Utility script to initialise model tables in Supabase

## 📋 Prerequisites
- Python 3.10+
- Node.js (for Supabase maintenance scripts)
- Supabase account & project
- Google Gemini API key

## ⚙️ Setup
1. Create a `.env` file in the project root:
   ```env
   TELEGRAM_TOKEN=your_telegram_token
   GEMINI_API_KEY=your_gemini_key
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## ▶️ Usage
```bash
python src/project/run.py
```
The bot will prompt for video details (what you sell, outfit, etc.), generate captions/tags via Gemini, store entries in Supabase, and schedule posts automatically.

## 📂 Directory layout
- `modelos/` – Model‑specific folders with `config.json`
- `plataformas/` – Platform‑specific upload scripts
- `src/project/` – Python source code
- `node_modules/` – Node dependencies for Supabase scripts

---
*Optimized for efficient traffic management and content publishing.*
