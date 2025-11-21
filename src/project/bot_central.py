import sys, os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[2]
VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python3"
if VENV_PYTHON.exists() and not sys.executable.startswith(str(BASE_DIR / ".venv")):
    print(f"⚠️  Ejecuta siempre en el entorno virtual:\n    source {BASE_DIR}/.venv/bin/activate\n")
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), __file__] + sys.argv[1:])

import os, json, pathlib
from datetime import datetime
import secrets
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv
try:
    from .scheduler import plan
    from .caption import generate_and_update
except ImportError:
    from scheduler import plan
    from caption import generate_and_update

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
NOMBRE_POR_USER_ID = {} # opcional: puedes mapear ids a nombres

# Configuración de modelos (carpeta en BASE_DIR)
MODELOS_DIR = BASE_DIR / "modelos"
MODELOS_DIR.mkdir(parents=True, exist_ok=True)

# Opciones disponibles para botones interactivos
QUE_VENDES_OPCIONES = [
    ("tetas", "🍑 Tetas"),
    ("culo", "🍑 Culo"),
    ("pies", "👣 Pies"),
    ("cara", "😍 Cara"),
    ("vagina", "🌸 Vagina"),
    ("cuerpo completo", "👤 Cuerpo completo"),
]

OUTFIT_OPCIONES = [
    ("lenceria", "👙 Lencería"),
    ("tanga", "🩲 Tanga"),
    ("topless", "👔 Topless"),
    ("tacones", "👠 Tacones"),
    ("tenis", "👟 Tenis"),
    ("falda", "👗 Falda"),
    ("desnuda", "✨ Desnuda"),
]

def build_que_vendes_keyboard(seleccionados: list) -> InlineKeyboardMarkup:
    """Construye teclado para seleccionar qué vendes (múltiple selección)"""
    botones = []
    for valor, etiqueta in QUE_VENDES_OPCIONES:
        check = "✅" if valor in seleccionados else "⬜"
        botones.append([InlineKeyboardButton(
            f"{check} {etiqueta}",
            callback_data=f"qv_toggle_{valor}"
        )])
    botones.append([InlineKeyboardButton("➡️ Continuar a Outfit", callback_data="qv_done")])
    return InlineKeyboardMarkup(botones)

def build_outfit_keyboard(seleccionados: list) -> InlineKeyboardMarkup:
    """Construye teclado para seleccionar outfit (múltiple selección)"""
    botones = []
    for valor, etiqueta in OUTFIT_OPCIONES:
        check = "✅" if valor in seleccionados else "⬜"
        botones.append([InlineKeyboardButton(
            f"{check} {etiqueta}",
            callback_data=f"outfit_toggle_{valor}"
        )])
    botones.append([InlineKeyboardButton("✅ Procesar Video", callback_data="process_video")])
    return InlineKeyboardMarkup(botones)

async def start(update: Update, context):
    user = update.effective_user
    nombre = NOMBRE_POR_USER_ID.get(user.id, user.first_name or "modelo").lower().replace(" ", "_")
    await update.message.reply_text(
        f"¡Hola {user.first_name}! ✨\n"
        "Este es tu chat privado y 100% seguro con el bot central.\n"
        "Envíame el vídeo cuando quieras (hasta 4 GB) y luego dime qué vendes + outfit.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📹 Enviar vídeo nuevo", callback_data="nuevo")]])
    )

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    modelo = NOMBRE_POR_USER_ID.get(user.id, user.first_name.lower().replace(" ", "_"))
    file = update.message.video or update.message.document
    await update.message.reply_text("Descargando vídeo grande…")
    
    # Ruta absoluta dentro de Trafico/modelos/
    modelo_dir = MODELOS_DIR / modelo
    modelo_dir.mkdir(parents=True, exist_ok=True)
    
    # Generar nombre único: timestamp + random (ej: 20251118_190015_a3f2b1.mp4)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = secrets.token_hex(3)  # 6 caracteres hexadecimales
    video_nombre = f"{timestamp}_{random_suffix}.mp4"
    ruta = str(modelo_dir / video_nombre)
    
    telegram_file = await file.get_file()
    await telegram_file.download_to_drive(ruta)
    context.user_data["video_ruta"] = ruta
    context.user_data["modelo"] = modelo
    context.user_data["que_vendes"] = []  # Inicializar selección
    context.user_data["outfit"] = []  # Inicializar selección
    context.user_data["step"] = "que_vendes"  # Paso actual
    
    await update.message.reply_text(
        "¡Vídeo recibido! ✅\n\n"
        "Ahora selecciona **qué vendes** (puedes elegir varios):",
        reply_markup=build_que_vendes_keyboard([]),
        parse_mode="Markdown"
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja todos los callbacks de los botones interactivos"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_data = context.user_data
    
    # Botón "Enviar vídeo nuevo"
    if data == "nuevo":
        await query.edit_message_text("¡Genial! Mándame el vídeo ahora 😈")
        user_data["esperando"] = True
        return
    
    # Verificar que hay video pendiente
    if not user_data.get("video_ruta"):
        await query.edit_message_text("❌ Error: No hay video pendiente.")
        return
    
    # Toggle de qué vendes
    if data.startswith("qv_toggle_"):
        valor = data.replace("qv_toggle_", "")
        seleccionados = user_data.get("que_vendes", [])
        if valor in seleccionados:
            seleccionados.remove(valor)
        else:
            seleccionados.append(valor)
        user_data["que_vendes"] = seleccionados
        
        await query.edit_message_text(
            f"**Qué vendes** (seleccionados: {len(seleccionados)})\n\n"
            "Toca los botones para seleccionar/deseleccionar:",
            reply_markup=build_que_vendes_keyboard(seleccionados),
            parse_mode="Markdown"
        )
    
    # Continuar a outfit
    elif data == "qv_done":
        if not user_data.get("que_vendes"):
            await query.answer("⚠️ Selecciona al menos una opción", show_alert=True)
            return
        
        user_data["step"] = "outfit"
        await query.edit_message_text(
            f"✅ **Qué vendes seleccionado:** {', '.join(user_data['que_vendes'])}\n\n"
            "Ahora selecciona **outfit** (puedes elegir varios):",
            reply_markup=build_outfit_keyboard([]),
            parse_mode="Markdown"
        )
    
    # Toggle de outfit
    elif data.startswith("outfit_toggle_"):
        valor = data.replace("outfit_toggle_", "")
        seleccionados = user_data.get("outfit", [])
        if valor in seleccionados:
            seleccionados.remove(valor)
        else:
            seleccionados.append(valor)
        user_data["outfit"] = seleccionados
        
        await query.edit_message_text(
            f"**Outfit** (seleccionados: {len(seleccionados)})\n\n"
            "Toca los botones para seleccionar/deseleccionar:",
            reply_markup=build_outfit_keyboard(seleccionados),
            parse_mode="Markdown"
        )
    
    # Procesar video
    elif data == "process_video":
        if not user_data.get("outfit"):
            await query.answer("⚠️ Selecciona al menos un outfit", show_alert=True)
            return
        
        await query.edit_message_text("⏳ Procesando video...")
        
        # Procesar igual que antes
        modelo = user_data["modelo"]
        video_ruta = user_data["video_ruta"]
        video_nombre = pathlib.Path(video_ruta).name
        meta_path = video_ruta.replace(".mp4", ".json")
        
        que_vendes = user_data.get("que_vendes", [])
        outfit = user_data.get("outfit", [])
        
        # Guardar metadata
        json.dump({
            "que_vendes": que_vendes,
            "outfit": outfit,
            "video_filename": video_nombre
        }, open(meta_path, "w"), ensure_ascii=False, indent=2)
        
        # Generar caption y tags
        generate_and_update(modelo, meta_path)
        
        # Programar slots
        try:
            slots = plan(modelo, video_nombre)
            
            # Actualizar scheduled_time en Supabase
            # Añadir src al path si no está (ya debería estar por bot_central.py pero por seguridad)
            if str(BASE_DIR / "src") not in sys.path:
                sys.path.append(str(BASE_DIR / "src"))
            from database.supabase_client import update_schedule_time
            for plataforma, scheduled_time in slots:
                update_schedule_time(modelo, video_nombre, plataforma, scheduled_time)
            
            slots_msg = f"{len(slots)} slots programados"
        except Exception as e:
            slots_msg = f"Slots: {str(e)}"
            slots = []
        
        await query.edit_message_text(
            f"✅ **¡Todo procesado!**\n\n"
            f"📝 Qué vendes: {', '.join(que_vendes)}\n"
            f"👗 Outfit: {', '.join(outfit)}\n"
            f"📅 {slots_msg} ✨\n\n"
            "¿Otro vídeo?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Sí, otro", callback_data="nuevo")]]),
            parse_mode="Markdown"
        )
        user_data.clear()

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callback_handler))  # Maneja todos los botones
app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, video_handler))
# Ya no necesitamos texto_handler, todo es con botones
print("BOT CENTRAL corriendo – recibe de todas las modelos al mismo tiempo")
app.run_polling()
