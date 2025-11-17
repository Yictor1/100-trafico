# src/discordbot.py
# -*- coding: utf-8 -*-

import os
import re
import json
import asyncio
import datetime as dt
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict

import discord
from discord.ext import commands
from dropbox import Dropbox, exceptions
import dropbox

try:
    from discord.ui import TextInput as UI_TextInput, Modal
    from discord import TextStyle as UI_TextStyle
    LIB_FLAVOR = "discord.py"
except Exception:
    from discord.ui import InputText as UI_TextInput, Modal
    from discord import InputTextStyle as UI_TextStyle
    LIB_FLAVOR = "py-cord"

STYLE_PARAGRAPH = getattr(UI_TextStyle, "paragraph", None) or getattr(UI_TextStyle, "long", None)

from dotenv import load_dotenv
load_dotenv()

# ---- ENV ----
TOKEN = os.getenv("DISCORD_TOKEN")
DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")
PANEL_CATEGORY_NAME = os.getenv("PANEL_CATEGORY_NAME")
GSHEET_NAME = os.getenv("GSHEET_NAME", "Trafico Candy")
VIDEO_TIMEOUT_MIN = int(os.getenv("VIDEO_TIMEOUT_MIN", "10"))
MAX_VIDEO_MB = int(os.getenv("MAX_VIDEO_MB", "500"))
ALLOWED_EXT = {".mp4", ".mov", ".mkv"}
SEND_CHANNEL_SUMMARY = os.getenv("SEND_CHANNEL_SUMMARY", "false").lower() == "true"

# Inicializar Dropbox client
dbx = Dropbox(DROPBOX_TOKEN) if DROPBOX_TOKEN else None

# ---- Sheets ----
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
    return gspread.authorize(creds)

def get_or_create_model_sheet(sh, modelo: str):
    try:
        return sh.worksheet(modelo)
    except gspread.WorksheetNotFound:
        return sh.add_worksheet(title=modelo, rows=200, cols=10)

HEADERS = ["video", "caption", "tags", "plataforma", "estado", "scheduled_time"]

def ensure_headers(ws):
    current = ws.row_values(1)
    if current[:len(HEADERS)] != HEADERS:
        ws.update("A1", [HEADERS])

def append_preliminary_rows(modelo: str, rows: List[List[str]]):
    gc = get_gspread_client()
    sh = gc.open(GSHEET_NAME)
    ws = get_or_create_model_sheet(sh, modelo)
    ensure_headers(ws)

    existing = ws.get_all_records()
    existing_keys = {(r.get("video",""), r.get("plataforma",""), r.get("scheduled_time","")) for r in existing}

    to_append = []
    for r in rows:
        key = (r[0], r[3], r[5])
        if key not in existing_keys:
            to_append.append(r)

    if to_append:
        ws.append_rows(to_append, value_input_option="RAW")

# ---- Utilidades ----
def now_tz() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=-5)))

def norm_snake(s: str) -> str:
    t = s.lower()
    t = (t.replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
           .replace("/", " ").replace("-", " "))
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", "_", t).strip("_")
    return t

@dataclass
class FormData:
    modelo: str
    que_vendes: List[str]
    outfit: List[str]
    request_id: Optional[str] = None
    ts_str: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

# =========================
# Soporte: inferir modelo
# =========================
def infer_model_name(interaction: discord.Interaction) -> str:
    channel_name = getattr(interaction.channel, "name", "") or ""
    category_name = getattr(getattr(interaction.channel, "category", None), "name", "") or ""
    generic = {"general", "panel", "contenido", "trafico", "traffic"}
    name = channel_name.strip()
    if not name or name.lower() in generic:
        name = category_name.strip() or "modelo"
    return norm_snake(name)

class ConfirmacionView(discord.ui.View):
    def __init__(self, form: FormData, interaction: discord.Interaction, timeout_min: int = VIDEO_TIMEOUT_MIN):
        super().__init__(timeout=timeout_min * 60)
        self.form = form
        self.interaction = interaction
        self.confirmed = False

    async def on_timeout(self):
        if not self.confirmed:
            try:
                await self.interaction.edit_original_response(content="⏱️ Tiempo agotado para confirmar. Vuelve a pulsar **Enviar contenido**.", view=None)
            except Exception:
                pass

    @discord.ui.button(label="Confirmar que subí el video", style=discord.ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("Este botón no es tuyo.", ephemeral=True)

        self.confirmed = True
        await interaction.response.defer(ephemeral=True)
        
        # Enviar mensaje de progreso
        await interaction.followup.send("🔄 Descargando y procesando video...", ephemeral=True)

        try:
            await process_submission(self.form, self.interaction)
            await interaction.followup.send("✅ Video procesado. ¡Gracias!", ephemeral=True)
            
            # Reenviar botón "Enviar contenido" al canal
            try:
                await self.interaction.channel.send("**Panel de envío de contenido**", view=EnviarContenidoView())
            except Exception as e:
                print(f"[discordbot] Error reenviando panel: {e}")
        except Exception as e:
            await interaction.followup.send(f"❌ Error procesando: {e}", ephemeral=True)

        for item in self.children:
            item.disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except Exception:
            pass

# =========================
# Pipeline de procesamiento
# =========================
import sys, pathlib
BASE_DIR = pathlib.Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scheduler import plan
from caption import generate_and_update

async def create_file_request(form: FormData, interaction: discord.Interaction) -> str:
    """Crea File Request en Dropbox y devuelve el URL."""
    if not dbx:
        raise ValueError("DROPBOX_TOKEN no configurado.")
    ts_str = now_tz().strftime("%Y-%m-%d_%H-%M-%S")
    form.ts_str = ts_str
    title = f"Envío {form.modelo} - {ts_str}"
    destination = f"/Uploads/{form.modelo}/{ts_str}"

    try:
        result = dbx.file_requests_create(
            title=title,
            destination=destination,
            open=True,
            description="Sube tu video aquí (sin login requerido)."
        )
        form.request_id = result.id
        return result.url
    except exceptions.DropboxException as e:
        raise ValueError(f"Error creando request en Dropbox: {e}")

async def download_from_dropbox(form: FormData, local_path: str) -> str:
    if not dbx:
        raise ValueError("DROPBOX_TOKEN no configurado.")
    destination = f"/Uploads/{form.modelo}/{form.ts_str}"

    try:
        entries = dbx.files_list_folder(destination).entries
        videos = [e for e in entries if isinstance(e, dropbox.files.FileMetadata) and e.name.lower().endswith(tuple(ALLOWED_EXT))]

        if not videos:
            raise ValueError("No se encontró video subido en la carpeta.")

        latest = max(videos, key=lambda x: x.server_modified)
        dropbox_path = latest.path_lower

        metadata = dbx.files_get_metadata(dropbox_path)
        size_mb = metadata.size / (1024 * 1024)
        if size_mb > MAX_VIDEO_MB:
            raise ValueError(f"Video demasiado grande: {size_mb:.1f} MB (> {MAX_VIDEO_MB} MB)")

        ext = os.path.splitext(latest.name)[1].lower()
        
        # Descarga asíncrona para evitar bloquear el hilo principal
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, dbx.files_download_to_file, local_path, dropbox_path)
        
        return ext
    except exceptions.DropboxException as e:
        raise ValueError(f"Error descargando de Dropbox: {e}")

async def process_submission(form: FormData, interaction: discord.Interaction):
    try:
        modelo_dir = os.path.join("modelos", form.modelo)
        os.makedirs(modelo_dir, exist_ok=True)

        ts = now_tz().strftime("%Y-%m-%d_%H-%M-%S")
        video_name = f"{ts}.mp4"
        form_name = f"{ts}.json"

        video_path = os.path.join(modelo_dir, video_name)

        ext = await download_from_dropbox(form, video_path)
        video_name = f"{ts}{ext}"
        os.rename(os.path.join(modelo_dir, f"{ts}.mp4"), os.path.join(modelo_dir, video_name))

        meta = {
            "modelo": form.modelo,
            "que_vendes": form.que_vendes,
            "outfit": form.outfit,
            "video_filename": video_name
        }

        form_path = os.path.join(modelo_dir, form_name)
        with open(form_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        try:
            slots = plan(form.modelo, video_name)
        except ValueError as e:
            print(f"[discordbot] Advertencia: No se pudieron generar slots para {form.modelo}: {e}")
            slots = []

        if not slots:
            print(f"[discordbot] Advertencia: Slots vacíos para {form.modelo}")
        else:
            prelim_rows = []
            for plataforma, scheduled_time in slots:
                prelim_rows.append([
                    video_name,
                    "",
                    "",
                    plataforma,
                    "pendiente",
                    scheduled_time
                ])
            append_preliminary_rows(form.modelo, prelim_rows)

        generate_and_update(form.modelo, form_path)

        if SEND_CHANNEL_SUMMARY:
            try:
                size_mb = os.path.getsize(os.path.join(modelo_dir, video_name)) / (1024 * 1024)
                resumen = (
                    f"**Nuevo envío de {interaction.user.mention}**\n"
                    f"- Modelo: `{form.modelo}`\n"
                    f"- Qué vendes: `{', '.join(form.que_vendes)}`\n"
                    f"- Outfit: `{', '.join(form.outfit)}`\n"
                    f"- Archivo: `{video_name}` ({size_mb:.1f} MB)"
                )
                await interaction.channel.send(resumen)
            except Exception:
                pass

        # 👈 CORRECCIÓN: Tratar request_id como cadena y manejar la excepción
        if form.request_id and dbx:
            try:
                dbx.file_requests_delete([form.request_id])  # Pasar como lista
            except exceptions.DropboxException as e:
                # Ignorar error si el File Request está abierto (normal)
                if "file_request_open" in str(e):
                    print(f"[discordbot] Info: File Request {form.request_id} está abierto, no se puede eliminar (normal)")
                else:
                    print(f"[discordbot] Advertencia: No se pudo eliminar File Request {form.request_id}: {e}")

    except Exception as e:
        if form.request_id and dbx:
            try:
                dbx.file_requests_delete([form.request_id])  # Pasar como lista
            except exceptions.DropboxException as e:
                # Ignorar error si el File Request está abierto (normal)
                if "file_request_open" not in str(e):
                    print(f"[discordbot] Advertencia: No se pudo eliminar File Request {form.request_id}: {e}")
            except:
                pass
        try:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Error procesando: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Error procesando: {e}", ephemeral=True)
        except Exception:
            print(f"[discordbot] Error procesando: {e}")

# ---- UI ----
class EnviarContenidoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enviar contenido", style=discord.ButtonStyle.primary, custom_id="enviar_contenido_btn")
    async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button):
        form_view = FormularioSimplificado(invoker=interaction.user)
        await interaction.response.send_message("Completa el formulario:", view=form_view, ephemeral=True)
        try:
            msg = await interaction.original_response()
            form_view.message = msg
        except Exception:
            pass

class FormularioSimplificado(discord.ui.View):
    def __init__(self, invoker: discord.Member):
        super().__init__(timeout=600)
        self.invoker = invoker
        self._que_vendes: List[str] = []
        self._outfit: List[str] = []
        self.message: Optional[discord.Message] = None

        class QueVendesSelect(discord.ui.Select):
            def __init__(self):
                super().__init__(placeholder="¿Qué vendes en el video?", min_values=1, max_values=5,
                                 options=[discord.SelectOption(label=x) for x in ["Tetas","Culo","Vagina","Cara","Pies"]],
                                 custom_id="que_vendes", row=0)
            async def callback(self, i: discord.Interaction):
                self.view._que_vendes = list(self.values); await i.response.defer(ephemeral=True)

        class OutfitSelect(discord.ui.Select):
            def __init__(self):
                super().__init__(placeholder="¿Cuál es tu OutFit?", min_values=1, max_values=7,
                                 options=[discord.SelectOption(label=x) for x in ["Desnuda","Lencería","Topples","Tanga","Tacones","Tenis","Falda"]],
                                 custom_id="outfit", row=1)
            async def callback(self, i: discord.Interaction):
                self.view._outfit = list(self.values); await i.response.defer(ephemeral=True)

        self.add_item(QueVendesSelect()); self.add_item(OutfitSelect())

    async def on_timeout(self):
        try:
            if getattr(self, "message", None):
                await self.message.edit(content="⏱️ El formulario expiró. Vuelve a pulsar **Enviar contenido**.", view=None)
        except Exception:
            pass

    @discord.ui.button(label="Enviar", style=discord.ButtonStyle.success, row=2)
    async def submit_form(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.invoker.id:
            return await interaction.response.send_message("Este formulario no es tuyo.", ephemeral=True)
        if not (self._que_vendes and self._outfit):
            return await interaction.response.send_message("Completa todas las secciones del formulario.", ephemeral=True)

        modelo = infer_model_name(interaction)
        form = FormData(
            modelo=modelo,
            que_vendes=[norm_snake(x) for x in self._que_vendes],
            outfit=[norm_snake(x) for x in self._outfit]
        )

        try:
            upload_url = await create_file_request(form, interaction)
            guide = (
                f"📹 **Sube tu video aquí:** {upload_url}\n"
                f"💡 **Instrucciones rápidas:**\n"
                "- Abre el enlace en tu navegador (no necesitas cuenta).\n"
                "- Selecciona el archivo (.mp4/.mov/.mkv, ≤ {MAX_VIDEO_MB} MB).\n"
                "- Sube y espera confirmación.\n"
                "- Luego, pulsa **Confirmar que subí el video** abajo.\n"
                f"Tienes {VIDEO_TIMEOUT_MIN} minutos para confirmar."
            )
            view = ConfirmacionView(form, interaction)
            await interaction.response.send_message(guide, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error preparando subida: {e}", ephemeral=True)

# ---- Bot ----
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    try:
        bot.add_view(EnviarContenidoView())
    except Exception:
        pass

@bot.event
async def on_ready():
    if not DROPBOX_TOKEN:
        print("[discordbot] ⚠️ DROPBOX_TOKEN no configurado. La subida no funcionará.")
    print(f"Bot conectado como {bot.user}")
    try:
        if PANEL_CATEGORY_NAME:
            for guild in bot.guilds:
                category = discord.utils.get(guild.categories, name=PANEL_CATEGORY_NAME)
                if category:
                    for channel in category.text_channels:
                        perms = channel.permissions_for(guild.me)
                        if perms.send_messages and perms.view_channel:
                            await channel.send("**Panel de envío de contenido**", view=EnviarContenidoView())
                    break
    except Exception as e:
        print(f"[discordbot] Error enviando panel: {e}")

def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN no configurado en .env")
    if not DROPBOX_TOKEN:
        raise RuntimeError("DROPBOX_TOKEN no configurado en .env")
    bot.run(TOKEN)