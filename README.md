# 🚦 Bot Trafico

**Bot de Telegram automatizado para la gestión de contenido para adultos**

## ✨ Características
- 🤖 Bot central de Telegram para subir videos y manejar metadatos
- 🧠 IA Gemini para generación automática de captions y tags optimizados para SEO
- ☁️ Base de datos Supabase en la nube para almacenamiento robusto y programación
- 📅 Scheduler inteligente que asigna automáticamente horarios de publicación por modelo y plataforma
- 🔄 Soporte multi‑plataforma (XXXFollow, MyClub, RedGifs, Cams, …)

## 🏗️ Arquitectura
- `src/project/bot_central.py` – Lógica principal del bot de Telegram
- `src/project/caption.py` – Integración con Gemini y generación de captions/tags
- `src/project/scheduler.py` – Cálculo de horarios de publicación
- `src/project/supabase_client.py` – Capa de abstracción de la base de datos
- `create_model_table.js` – Script para inicializar tablas de modelos en Supabase

## 📋 Requisitos previos
- Python 3.10+
- Node.js (para scripts de mantenimiento de Supabase)
- Cuenta y proyecto en Supabase
- API key de Google Gemini

## ⚙️ Configuración
1. Crear un archivo `.env` en la raíz del proyecto:
   ```env
   TELEGRAM_TOKEN=tu_token_de_telegram
   GEMINI_API_KEY=tu_api_key_de_gemini
   SUPABASE_URL=tu_url_de_supabase
   SUPABASE_ANON_KEY=tu_anon_key_de_supabase
   ```
2. Instalar dependencias de Python:
   ```bash
   pip install -r requirements.txt
   ```

## ▶️ Uso
```bash
python src/project/run.py
```
El bot solicitará detalles del video (qué vendes, outfit, etc.), generará captions/tags vía Gemini, guardará la información en Supabase y programará la publicación automáticamente.

## 📂 Estructura de directorios
- `modelos/` – Carpetas específicas por modelo con su `config.json`
- `plataformas/` – Scripts específicos de subida por plataforma
- `src/project/` – Código fuente en Python
- `node_modules/` – Dependencias de Node para los scripts de Supabase

---
*Optimizado para una gestión eficiente del tráfico y publicación de contenido.*
