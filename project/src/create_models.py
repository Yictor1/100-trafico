import os
import json
import asyncio
import discord
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from discord.ext import commands

# Constants
SHEETS_NAME = "Trafico Candy"
SHEET_TAB = "Json modelos"
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "modelos")
DISCORD_CATEGORY = "Modelos"

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# Add your credentials setup here

def get_sheets_service():
    from google.oauth2.service_account import Credentials
    import os

    # Calcular la raíz del proyecto (2 niveles arriba desde project/src)
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    credentials_path = os.getenv(
        "GOOGLE_SHEETS_CREDENTIALS_PATH",
        os.path.join(ROOT_DIR, "credenciales.json")
    )

    credentials = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return build("sheets", "v4", credentials=credentials)


def get_discord_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)
    return bot

def read_new_rows(service, spreadsheet_id, sheet_name):
    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=sheet_name).execute()
        values = result.get('values', [])
        
        if not values:
            print("No data found.")
            return []

        headers = values[0]
        rows = values[1:]
        
        # Check if 'procesado' column exists, if not, add it
        if 'procesado' not in headers:
            headers.append('procesado')
            rows = [row + [""] for row in rows]
            sheet.values().update(
                spreadsheetId=spreadsheet_id,
                range=sheet_name,
                valueInputOption="RAW",
                body={"values": [headers] + rows}
            ).execute()

        # Find unprocessed rows (where 'procesado' is not 'SI')
        unprocessed_rows = [row for row in rows if len(row) < len(headers) or row[headers.index('procesado')] != 'SI']
        return headers, unprocessed_rows

    except HttpError as err:
        print(f"An error occurred: {err}")
        return []

def mark_row_as_processed(service, spreadsheet_id, sheet_name, row_number, headers):
    try:
        sheet = service.spreadsheets()
        # Encontrar la posición de la columna 'procesado' dinámicamente
        if 'procesado' in headers:
            procesado_index = headers.index('procesado')
            procesado_col = chr(ord('A') + procesado_index)
        else:
            print("❌ Columna 'procesado' no encontrada en headers")
            return
        
        # row_number es el índice real en el sheet (ya viene +2 desde el enumerate)
        range_ = f"{sheet_name}!{procesado_col}{row_number}"
        print(f"Marking as processed: {range_}")  # Debug message
        sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueInputOption="RAW",
            body={"values": [["SI"]]}
        ).execute()
    except HttpError as err:
        print(f"An error occurred: {err}")

def normalize_folder_name(name):
    # Replace invalid characters for Windows folder names
    return name.replace("/", "_").replace(":", "_").replace("\\", "_").replace("*", "_").replace("?", "_").replace("\"", "_").replace("<", "_").replace(">", "_").replace("|", "_")

# --- NUEVO: helper para formatear el config.json ---
def build_config(form_data: dict) -> dict:
    """Transforma los datos crudos del Sheet al formato de config.json requerido."""
    profile_id = (
        form_data.get("ID Incogniton")
        or form_data.get("ID Incognito")
        or form_data.get("ID")
        or ""
    )

    target_url = {}
    if form_data.get("URL xxxfollow"):
        target_url["xxxfollow"] = form_data["URL xxxfollow"]
    if form_data.get("URL My.Club"):
        target_url["myclub"] = form_data["URL My.Club"]

    metadata = {
        "Tipo de cuerpo":   form_data.get("Tipo de cuerpo", ""),
        "Tamano de pechos": form_data.get("Tamano de pechos", ""),
        "Tamano de culo":   form_data.get("Tamano de culo", ""),
        "Color de cabello": form_data.get("Color de cabello", ""),
        "Categoria":        form_data.get("Categoria", ""),
        "Piercings":        form_data.get("Piercings", ""),
        "Tatuajes":         form_data.get("Tatuajes", "")
    }

    return {
        "profile_id": profile_id,
        "target_url": target_url,
        "metadata": metadata
    }


def create_model_folder(model_name, form_data):
    normalized_name = normalize_folder_name(model_name)
    model_path = os.path.join(MODELS_DIR, normalized_name)
    print(f"Creating folder at: {model_path}")  # Debug message
    os.makedirs(model_path, exist_ok=True)
    config_path = os.path.join(model_path, "config.json")
    print(f"Writing config.json at: {config_path}")  # Debug message

    # >>> cambio principal: formatear antes de guardar
    config_payload = build_config(form_data)

    with open(config_path, "w", encoding="utf-8") as config_file:
        json.dump(config_payload, config_file, indent=2, ensure_ascii=False)

def create_model_sheet(service, spreadsheet_id, model_name):
    try:
        sheet = service.spreadsheets()
        requests = [{
            "addSheet": {
                "properties": {
                    "title": model_name
                }
            }
        }]
        body = {"requests": requests}
        sheet.batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

        # Add headers to the new sheet
        headers = ["video", "caption", "tags", "plataforma", "estado", "scheduled_time"]
        range_ = f"{model_name}!A1:F1"
        sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueInputOption="RAW",
            body={"values": [headers]}
        ).execute()
    except HttpError as err:
        print(f"An error occurred: {err}")

async def create_discord_channel(model_name, sheets_service, spreadsheet_id, sheet_name, row_number):
    from dotenv import load_dotenv
    load_dotenv()
    
    TOKEN = os.getenv("DISCORD_TOKEN")
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    
    # Crear el bot usando la misma configuración que discordbot.py
    bot = discord.Client(intents=intents)
    
    channel_id = None
    button_sent = False
    
    @bot.event
    async def on_ready():
        nonlocal channel_id, button_sent
        try:
            guild = bot.guilds[0] if bot.guilds else None
            if guild:
                category = discord.utils.get(guild.categories, name=DISCORD_CATEGORY)
                if category:
                    # Crear el canal
                    channel = await guild.create_text_channel(model_name, category=category)
                    channel_id = str(channel.id)
                    print(f"✅ Canal '{model_name}' creado en Discord con ID: {channel_id}")
                    
                    # Guardar channel_id en Google Sheets
                    try:
                        # Buscar la columna channel_id o crearla si no existe
                        headers_result = sheets_service.spreadsheets().values().get(
                            spreadsheetId=spreadsheet_id, 
                            range=sheet_name
                        ).execute()
                        headers = headers_result.get('values', [[]])[0]
                        
                        if 'channel_id' not in headers:
                            headers.append('channel_id')
                            sheets_service.spreadsheets().values().update(
                                spreadsheetId=spreadsheet_id,
                                range=f"{sheet_name}!A1",
                                valueInputOption="RAW",
                                body={"values": [headers]}
                            ).execute()
                        
                        # Encontrar la columna channel_id
                        channel_id_col = chr(ord('A') + headers.index('channel_id'))
                        range_ = f"{sheet_name}!{channel_id_col}{row_number}"
                        
                        sheets_service.spreadsheets().values().update(
                            spreadsheetId=spreadsheet_id,
                            range=range_,
                            valueInputOption="RAW",
                            body={"values": [[channel_id]]}
                        ).execute()
                        print(f"✅ Channel ID guardado en Google Sheets: {channel_id}")
                        
                    except Exception as e:
                        print(f"❌ Error guardando channel_id en Google Sheets: {e}")
                    
                    # Enviar mensaje con botón usando el mismo custom_id que discordbot.py
                    try:
                        # Crear botón con el mismo custom_id que maneja discordbot.py
                        from discord import ButtonStyle
                        from discord.ui import Button, View
                        
                        # Usar exactamente el mismo custom_id que está en discordbot.py
                        button = Button(label="Enviar contenido", style=ButtonStyle.primary, custom_id="enviar_contenido_btn")
                        view = View()
                        view.add_item(button)
                        
                        await channel.send("¡Bienvenido al canal del modelo! Usa el botón para enviar contenido.", view=view)
                        button_sent = True
                        print(f"✅ Botón 'Enviar contenido' enviado correctamente con custom_id: enviar_contenido_btn")
                        
                    except Exception as e:
                        print(f"❌ Error enviando botón: {e}")
                        button_sent = False
                    
                    # Actualizar columna boton_enviado
                    try:
                        # Buscar la columna boton_enviado o crearla si no existe
                        if 'boton_enviado' not in headers:
                            headers.append('boton_enviado')
                            sheets_service.spreadsheets().values().update(
                                spreadsheetId=spreadsheet_id,
                                range=f"{sheet_name}!A1",
                                valueInputOption="RAW",
                                body={"values": [headers]}
                            ).execute()
                        
                        # Encontrar la columna boton_enviado
                        boton_col = chr(ord('A') + headers.index('boton_enviado'))
                        range_ = f"{sheet_name}!{boton_col}{row_number}"
                        
                        value = "TRUE" if button_sent else "FALSE"
                        sheets_service.spreadsheets().values().update(
                            spreadsheetId=spreadsheet_id,
                            range=range_,
                            valueInputOption="RAW",
                            body={"values": [[value]]}
                        ).execute()
                        print(f"✅ Columna boton_enviado actualizada: {value}")
                        
                    except Exception as e:
                        print(f"❌ Error actualizando boton_enviado: {e}")
                    
                else:
                    print(f"❌ Categoría '{DISCORD_CATEGORY}' no encontrada")
        except Exception as e:
            print(f"❌ Error creando canal Discord: {e}")
        finally:
            # Cerrar el bot de forma más limpia
            try:
                await bot.close()
            except:
                pass
    
    try:
        await bot.start(TOKEN)
    except Exception as e:
        print(f"❌ Error conectando a Discord: {e}")
        try:
            await bot.close()
        except:
            pass
    
    return channel_id, button_sent

def main():
    print("🚀 Iniciando monitor de Google Sheets...")
    print("📊 Leyendo hoja cada 15 segundos...")
    print("⏹️  Presiona Ctrl+C para detener")
    
    # Initialize services
    sheets_service = get_sheets_service()

    # Replace with your actual spreadsheet ID
    SPREADSHEET_ID = "1XhTVpOU-a9wtZf9yFHGkquUm3J446_lPjejZoGeeI8U"

    try:
        while True:
            print(f"\n🔄 [{time.strftime('%H:%M:%S')}] Verificando nuevas filas...")
            
            # Read new rows
            headers, new_rows = read_new_rows(sheets_service, SPREADSHEET_ID, SHEET_TAB)
            
            if new_rows:
                print(f"📝 Encontradas {len(new_rows)} filas nuevas para procesar")
                print(f"Headers: {headers}")
                
                # Get all rows to find real row numbers
                result = sheets_service.spreadsheets().values().get(
                    spreadsheetId=SPREADSHEET_ID,
                    range=SHEET_TAB
                ).execute()
                all_rows = result.get('values', [])

                for row_index, row in enumerate(new_rows):
                    try:
                        form_data = dict(zip(headers, row))
                        model_name = form_data['Nombre modelo']  # Get model name from the correct column
                        
                        # Find the actual row number in the sheet
                        row_data = ','.join(str(x) for x in row)
                        real_row_number = next(i for i, r in enumerate(all_rows, 1) if ','.join(str(x) for x in r) == row_data)
                        
                        print(f"🔨 Procesando modelo: {model_name}")
                        print(f"📋 Datos del formulario: {form_data}")

                        # Create model folder and config.json
                        create_model_folder(model_name, form_data)
                        print(f"✅ Carpeta del modelo creada: {model_name}")

                        # Create new sheet for the model
                        create_model_sheet(sheets_service, SPREADSHEET_ID, model_name)
                        print(f"📊 Nueva hoja creada para: {model_name}")

                        # Create Discord channel
                        channel_id, button_sent = asyncio.run(create_discord_channel(model_name, sheets_service, SPREADSHEET_ID, SHEET_TAB, real_row_number))
                        if channel_id:
                            print(f"💬 Canal Discord creado: {model_name} con ID: {channel_id}")
                            print(f"🔘 Botón enviado: {'SÍ' if button_sent else 'NO'}")
                        else:
                            print(f"❌ Error creando canal Discord: {model_name}")

                        # Mark row as processed with the real row number
                        mark_row_as_processed(sheets_service, SPREADSHEET_ID, SHEET_TAB, real_row_number, headers)
                        print(f"✅ Fila marcada como procesada: {model_name}")
                        
                    except Exception as e:
                        print(f"❌ Error procesando fila {row_index + 1}: {e}")
                        continue
            else:
                print("✅ No hay nuevas filas para procesar")
            
            print(f"⏳ Esperando 15 segundos...")
            time.sleep(15)
            
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo monitor...")
        print("👋 ¡Hasta luego!")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        print("🔄 Reintentando en 15 segundos...")
        time.sleep(15)
        main()  # Recursive call to restart

if __name__ == "__main__":
    main()
