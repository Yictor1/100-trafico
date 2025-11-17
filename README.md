# 🍬 Tráfico Candy Gemini

Bot de Discord que utiliza Google Gemini AI para generar contenido creativo y gestionar tráfico de contenido.

## 🚀 Características

- **Bot de Discord**: Integración completa con Discord usando discord.py
- **IA Generativa**: Utiliza Google Gemini para generar contenido creativo
- **Programación Automática**: Sistema de programación de tareas
- **Google Sheets**: Integración con Google Sheets para gestión de datos
- **Sistema de Etiquetas**: Gestión inteligente de etiquetas y categorías

## 📋 Requisitos Previos

- Python 3.13 o superior
- Cuenta de Discord con bot configurado
- Proyecto de Google Cloud con Gemini API habilitada
- Cuenta de servicio de Google para Google Sheets

## 🛠️ Instalación

1. **Clona el repositorio:**
```bash
git clone https://github.com/Yictor1/Trafico_candy_Gemini.git
cd Trafico_candy_Gemini
```

2. **Crea un entorno virtual:**
```bash
python -m venv .venv
```

3. **Activa el entorno virtual:**
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

4. **Instala las dependencias:**
```bash
cd project
pip install -r requirements.txt
```

## ⚙️ Configuración

### 1. Archivo de Credenciales (`credenciales.json`)

**Ubicación:** Debe estar en la **raíz del proyecto** (mismo nivel que la carpeta `project/`)

```
Trafico_candy_Gemini/
├── credenciales.json          ← AQUÍ
├── .env                       ← AQUÍ
├── project/
│   ├── src/
│   ├── requirements.txt
│   └── run.py
└── modelos/
```

**Contenido:** Archivo JSON de cuenta de servicio de Google Cloud con permisos para:
- Google Sheets API
- Gemini AI API

### 2. Variables de Entorno (`.env`)

**Ubicación:** Debe estar en la **raíz del proyecto** (mismo nivel que la carpeta `project/`)

```env
# Discord Bot Token
DISCORD_TOKEN=tu_token_de_discord_aqui

# Google Gemini API Key
GEMINI_API_KEY=tu_api_key_de_gemini_aqui

# ID del servidor de Discord
GUILD_ID=id_del_servidor_discord

# ID del canal donde el bot puede escribir
CHANNEL_ID=id_del_canal_discord

# Configuración de Google Sheets
SHEET_ID=id_de_la_hoja_de_calculo
```

## 🏗️ Estructura del Proyecto

```
Trafico_candy_Gemini/
├── credenciales.json          # Credenciales de Google Cloud
├── .env                       # Variables de entorno
├── .gitignore                 # Archivos omitidos por Git
├── README.md                  # Este archivo
├── project/                   # Código principal del proyecto
│   ├── src/                   # Código fuente
│   │   ├── discordbot.py      # Bot principal de Discord
│   │   ├── caption.py         # Generación de contenido con Gemini
│   │   ├── scheduler.py       # Programación de tareas
│   │   ├── tags_disponibles.json # Etiquetas disponibles
│   │   └── __init__.py
│   ├── requirements.txt       # Dependencias de Python
│   └── run.py                 # Punto de entrada principal
└── modelos/                   # Modelos de IA (opcional)
    └── taniared/              # Modelos específicos
```

## 🚀 Uso

1. **Configura las credenciales** según las instrucciones anteriores

2. **Ejecuta el bot:**
```bash
cd project
python run.py
```

3. **El bot se conectará a Discord** y estará listo para recibir comandos

## 🔧 Comandos del Bot

- `/generar`: Genera contenido usando Gemini AI
- `/programar`: Programa contenido para publicación futura
- `/etiquetas`: Muestra etiquetas disponibles
- `/ayuda`: Muestra ayuda sobre comandos disponibles

## 📝 Notas Importantes

- **NUNCA subas `credenciales.json` o `.env` a Git** - ya están incluidos en `.gitignore`
- El entorno virtual (`.venv/`) no se sube al repositorio
- Asegúrate de tener permisos adecuados en Google Cloud
- El bot requiere permisos de administrador en Discord para funcionar correctamente

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🆘 Soporte

Si tienes problemas o preguntas:
1. Revisa este README
2. Verifica que las credenciales estén en la ubicación correcta
3. Asegúrate de que todas las dependencias estén instaladas
4. Abre un issue en GitHub

## 🔐 Seguridad

- **NUNCA** compartas tus credenciales
- **NUNCA** subas archivos de configuración sensibles
- Usa variables de entorno para configuraciones locales
- Mantén actualizadas las dependencias
