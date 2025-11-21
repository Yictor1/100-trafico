# 🚦 Trafico Bot

Bot de Telegram automatizado para la gestión, optimización y programación de contenido para adultos. Integra Inteligencia Artificial (Gemini) y base de datos en la nube (Supabase) para un flujo de trabajo eficiente.

## 🚀 Características Principales

*   **🤖 Bot de Telegram Centralizado**: Interfaz principal para subir videos y gestionar metadatos.
*   **🧠 IA Generativa (Gemini)**: Generación automática de captions seductores y tags inteligentes optimizados para SEO.
*   **☁️ Base de Datos Supabase**: Almacenamiento robusto y escalable de configuraciones y programación de posts.
*   **📅 Scheduler Inteligente**: Asignación automática de horarios de publicación según las reglas de cada modelo y plataforma.
*   **🔄 Gestión Multi-Plataforma**: Soporte para múltiples plataformas (ej. XXXFollow, MyClub, RedGifs, Cams) con configuraciones independientes.

## 🛠️ Arquitectura del Proyecto

El proyecto se estructura en los siguientes componentes clave:

*   **`project/src/bot_central.py`**: El núcleo del bot de Telegram. Maneja la interacción con el usuario y la recepción de archivos.
*   **`project/src/caption.py`**: Módulo de IA. Analiza metadatos, conecta con Gemini API para generar textos y guarda resultados en Supabase.
*   **`project/src/scheduler.py`**: Motor de programación. Calcula los mejores horarios de publicación basándose en la configuración del modelo.
*   **`project/src/supabase_client.py`**: Cliente centralizado para todas las operaciones de base de datos.
*   **`create_model_table.js`**: Script de utilidad para inicializar tablas de bases de datos para nuevos modelos.

## 📋 Requisitos Previos

*   Python 3.10+
*   Node.js (para scripts de mantenimiento de Supabase)
*   Cuenta en Supabase
*   API Key de Google Gemini

## ⚙️ Configuración

1.  **Variables de Entorno**: Crea un archivo `.env` en la carpeta `Trafico/` con las siguientes variables:
    ```env
    TELEGRAM_TOKEN=tu_token_de_telegram
    GEMINI_API_KEY=tu_api_key_de_gemini
    SUPABASE_URL=tu_url_de_supabase
    SUPABASE_ANON_KEY=tu_anon_key_de_supabase
    ```

2.  **Instalación de Dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

## ▶️ Uso

### 1. Iniciar el Bot
Para arrancar el bot, ejecuta el script principal desde la raíz del proyecto:

```bash
python Trafico/project/run.py
```

### 2. Flujo de Trabajo
1.  Envía un video al bot de Telegram.
2.  El bot te pedirá detalles: **¿Qué vendes?** (foco del video) y **Outfit**.
3.  El sistema procesará el video:
    *   Generará un caption y tags con IA.
    *   Creará entradas en la base de datos para cada plataforma configurada.
    *   Asignará horarios de publicación automáticamente.

### 3. Agregar un Nuevo Modelo
Cuando trabajes con una modelo nueva por primera vez:

1.  El bot creará automáticamente la carpeta y la configuración básica en Supabase.
2.  Debes crear su tabla de horarios ejecutando manualmente:
    ```bash
    cd Trafico/project/src
    node create_model_table.js nombre_modelo
    ```
    *(Reemplaza `nombre_modelo` con el slug de la modelo, ej: `taniared`)*

## 📂 Estructura de Directorios

*   `modelos/`: Carpetas específicas por modelo con sus configuraciones (`config.json`).
*   `plataformas/`: Scripts específicos de subida para cada plataforma (si aplica).
*   `project/`: Código fuente Python.
*   `create_supabase_schema.js`: Script para inicializar el esquema base de la base de datos.

---
*Desarrollado para optimizar el flujo de trabajo de Traffic Management.*
