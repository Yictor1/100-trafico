# src/caption.py
# -*- coding: utf-8 -*-

import os
import json
import random
import logging
import time
from typing import List, Dict, Optional
from dataclasses import dataclass

import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

# ---- ENV ----
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MAX_RETRIES = 3

# Configurar Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Usar gemini-2.0-flash-exp si está disponible, o fallback a 1.5
    gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    gemini_model = None

# ---- Logging ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- Cache Global ----
_TAGS_CACHE = None
_CONFIG_CACHE = {}

@dataclass
class CaptionResult:
    """Resultado de la generación de caption y tags"""
    caption: str
    tags: List[str]
    success: bool
    error: Optional[str] = None

def get_tags_data() -> Dict:
    """Carga tags_disponibles.json con caché"""
    global _TAGS_CACHE
    if _TAGS_CACHE is None:
        try:
            # tags_disponibles.json está en src/, un nivel arriba de src/project/
            base_src_dir = os.path.dirname(os.path.dirname(__file__))
            tags_path = os.path.join(base_src_dir, "tags_disponibles.json")
            with open(tags_path, "r", encoding="utf-8") as f:
                _TAGS_CACHE = json.load(f)
            logger.info("✅ tags_disponibles.json cargado en caché")
        except Exception as e:
            logger.error(f"❌ Error cargando tags_disponibles.json: {e}")
            return {}
    return _TAGS_CACHE

def load_model_config(modelo: str) -> Dict:
    """Carga la configuración del modelo con caché"""
    global _CONFIG_CACHE
    if modelo not in _CONFIG_CACHE:
        try:
            # Buscar desde el directorio raíz del proyecto
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Subir 3 niveles desde src/
            config_path = os.path.join(base_dir, "modelos", modelo, "config.json")
            with open(config_path, "r", encoding="utf-8") as f:
                _CONFIG_CACHE[modelo] = json.load(f)
            logger.info(f"✅ Configuración de {modelo} cargada en caché")
        except Exception as e:
            logger.error(f"❌ Error cargando config del modelo {modelo}: {e}")
            return {}
    return _CONFIG_CACHE[modelo]

def map_size_es_to_en(v: str) -> str:
    """Normaliza tamaños en español a inglés para facet_map"""
    s = (v or "").lower()
    if "peque" in s or "small" in s: 
        return "Small"
    if "gran" in s or "big" in s:    
        return "Big"
    return ""

def get_smart_tags_from_new_structure(form_data: Dict, model_config: Dict) -> List[str]:
    """Obtiene tags inteligentemente usando la nueva estructura de tags_disponibles.json"""
    try:
        tags_data = get_tags_data()
        if not tags_data:
            return []
        
        selected_tags = []
        
        # Helpers
        def _norm(s: str) -> str:
            return (s or "").strip().lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")

        def _pick_from_pool(pool, selected, k):
            cand = [t for t in pool if t not in selected]
            random.shuffle(cand)
            return cand[:max(0,k)]

        def _match_trait(trait_list, value_es):
            v = _norm(value_es)
            for entry in trait_list:
                if _norm(entry.get("value","")) == v:
                    return entry.get("pool", [])
            return []
        
        # Normalizar que_vendes y outfit
        q = form_data.get("que_vendes", [])
        o = form_data.get("outfit", [])
        que_vendes = q if isinstance(q, list) else [q] if q else []
        outfit_list = o if isinstance(o, list) else [o] if o else []
        
        # Mapeo directo de términos a IDs de body_focus
        FOCUS_MAPPING = {
            "culo": "ass", "ass": "ass",
            "tetas": "boobs", "boobs": "boobs",
            "pies": "feet", "feet": "feet",
            "cara": "face", "face": "face",
            "vagina": "pussy", "pussy": "pussy",
            "cuerpo completo": "fullbody", "fullbody": "fullbody"
        }

        # 1. Tags basados en que_vendes (body_focus)
        for item in que_vendes:
            item_lower = item.lower()
            focus_id = FOCUS_MAPPING.get(item_lower)
            
            if focus_id:
                # Buscar el body_focus correspondiente en el JSON
                body_focus = next((bf for bf in tags_data.get("body_focus", []) if bf.get("id") == focus_id), None)
                
                if body_focus:
                    # Lógica especial para tamaños (ass/boobs)
                    if focus_id in ["ass", "boobs"]:
                        facet_key = body_focus.get("facet_from_config")
                        if facet_key:
                            # Mapear config value (ej: "Grande") a facet value (ej: "Big")
                            config_field = "Tamano de culo" if focus_id == "ass" else "Tamano de pechos"
                            config_value = map_size_es_to_en(model_config.get("metadata", {}).get(config_field, ""))
                            facet_map = body_focus.get("facet_map", {})
                            
                            if config_value and config_value in facet_map:
                                selected_tags.append(facet_map[config_value])
                        
                        # Filtrar tags de tamaño del pool general para no duplicar o contradecir
                        exclude_tags = {"#BigAss", "#SmallAss", "#BigTits", "#SmallTits"}
                        pool_tags = [t for t in body_focus.get("pool", []) if t not in exclude_tags]
                        selected_tags.extend(_pick_from_pool(pool_tags, selected_tags, 2))
                    else:
                        # Para otros focos (feet, face, etc.)
                        selected_tags.extend(_pick_from_pool(body_focus.get("pool", []), selected_tags, 2))
        
        # 2. Tags basados en outfit
        outfit_map = { x["id"]: x for x in tags_data.get("outfit", []) }
        alias_outfit = {
            "lenceria": "lingerie", "tanga": "thong", "topless": "topless",
            "tacones": "heels", "tenis": "sneakers", "falda": "skirt", "desnuda": "nude"
        }
        
        for item in outfit_list:
            oid = alias_outfit.get(item.lower(), item.lower())
            o = outfit_map.get(oid)
            if not o: 
                continue
            
            # Outfit: máximo 2 tags
            pool = [t for t in o.get("pool", []) if t not in selected_tags]
            selected_tags.extend(_pick_from_pool(pool, selected_tags, 2))
            
            # adds_from_body_focus (ej. thong→pussy+ass)
            for add in o.get("adds_from_body_focus", []):
                fid = add.get("focus")
                cnt = int(add.get("count", 1))
                bf = next((b for b in tags_data.get("body_focus", []) if b.get("id")==fid), None)
                if not bf: 
                    continue
                
                bf_pool = [t for t in bf.get("pool", []) if t not in selected_tags]
                if fid == "ass":
                    bf_pool = [t for t in bf_pool if t not in {"#BigAss", "#SmallAss"}]
                
                selected_tags.extend(_pick_from_pool(bf_pool, selected_tags, cnt))
        
        # 3. Tags basados en model_traits del config.json
        metadata = model_config.get("metadata", {})
        traits_config = tags_data.get("model_traits", {})
        
        # Mapeo de trait key en config -> trait key en tags_disponibles
        TRAIT_MAPPING = {
            "Tipo de cuerpo": "body_type",
            "Color de cabello": "hair_color",
            "Categoria": "category",
            "Tatuajes": "tattoos",
            "Piercings": "piercings"
        }
        
        for config_key, trait_key in TRAIT_MAPPING.items():
            trait_pool = _match_trait(traits_config.get(trait_key, []), metadata.get(config_key, ""))
            selected_tags.extend(_pick_from_pool(trait_pool, selected_tags, 1))
        
        # Corte final respetando política y dedupe
        unique_tags = list(dict.fromkeys(selected_tags))
        max_tags = tags_data.get("policy", {}).get("max_tags", 6)
        
        logger.info(f"🏷️ Tags generados ({len(unique_tags)}): {unique_tags[:max_tags]}")
        return unique_tags[:max_tags]
        
    except Exception as e:
        logger.error(f"❌ Error generando tags inteligentes: {e}")
        return []

def load_form_data(form_path: str) -> Dict:
    """Carga los datos del formulario"""
    try:
        # Si no es ruta absoluta, buscar desde el directorio raíz del proyecto
        if not os.path.isabs(form_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            form_path = os.path.join(base_dir, form_path)
        
        with open(form_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ Error cargando form data: {e}")
        return {}

def call_gemini_api(prompt: str) -> Optional[str]:
    """Llama a la API de Gemini para generar caption"""
    if not gemini_model:
        logger.error("❌ GEMINI_API_KEY no configurado")
        return None
    
    for attempt in range(MAX_RETRIES):
        try:
            response = gemini_model.generate_content(prompt)
            content = response.text
            
            if content:
                content = content.strip()
                logger.info("✅ Respuesta exitosa de Gemini API")
                return content
                    
        except Exception as e:
            logger.error(f"⚠️ Error llamando a Gemini (intento {attempt + 1}): {e}")
            if "429" in str(e):
                wait_time = 2 ** attempt
                logger.info(f"⏳ Esperando {wait_time}s por cuota...")
                time.sleep(wait_time)
        
        if attempt < MAX_RETRIES - 1:
            time.sleep(1)
    
    return None

def generate_caption_and_tags(modelo: str, form_path: str) -> CaptionResult:
    """Función principal que genera caption y tags usando la nueva lógica"""
    try:
        # Cargar datos (ahora usa caché para config)
        model_config = load_model_config(modelo)
        form_data = load_form_data(form_path)
        
        if not form_data:
            return CaptionResult("", [], False, "No se pudo cargar form data")
        
        # Usar la nueva lógica de tags inteligentes
        smart_tags = get_smart_tags_from_new_structure(form_data, model_config)
        
        # Generar caption con Gemini
        accion = form_data.get("que_vendes", [])
        outfit = form_data.get("outfit", [])
        metadata = model_config.get("metadata", {})
        
        # Normalizar para comparación
        que_vendes = accion if isinstance(accion, list) else [accion] if accion else []
        outfit_norm = outfit if isinstance(outfit, list) else [outfit] if outfit else []
        
        # Prompt Optimizado
        prompt = f"""
You are an expert social media manager for adult content creators.
Write ONE short, seductive caption in English for a short video clip.

CONTEXT:
- Focus: {', '.join(que_vendes)}
- Outfit: {', '.join(outfit_norm)}
- Model: {metadata.get("Categoria","")} with {metadata.get("Tipo de cuerpo","")} body

RULES:
1. Max 100 characters.
2. NO hashtags, NO emojis.
3. Tone: Sexy, direct, inviting.
4. MUST include a Call to Action (e.g., "Link in bio", "See more inside", "I'm live").

EXAMPLES:
- "Waiting for you in my private room. Join me."
- "Do you like my outfit? See more on my profile."
- "I'm so horny right now. Come play with me."
"""
        
        # Llamar a Gemini para generar caption
        ai_caption = call_gemini_api(prompt)
        
        if ai_caption:
            caption = ai_caption
            logger.info(f"📝 Caption Gemini: {caption}")
        else:
            # Fallback mejorado: caption genérico contextual
            logger.warning("⚠️ Gemini falló, usando caption genérico")
            
            # Diccionario de fallbacks por foco principal
            fallbacks = {
                "culo": "Showing off my curves. Do you like what you see?",
                "tetas": "Playing with my boobs just for you. Join me.",
                "pies": "Worship my feet. I know you want to.",
                "cara": "Look into my eyes and tell me what you want.",
                "vagina": "I'm so wet for you. Come inside.",
                "cuerpo completo": "My full body is waiting for you.",
                "desnuda": "Completely naked and ready. Don't miss out."
            }
            
            # Buscar el primer match
            caption = "Exclusive content just for you. Link in bio."
            for key, text in fallbacks.items():
                if any(key in x.lower() for x in que_vendes + outfit_norm):
                    caption = text
                    break
        
        return CaptionResult(caption, smart_tags, True)
        
    except Exception as e:
        logger.error(f"❌ Error generando caption y tags: {e}")
        return CaptionResult("", [], False, str(e))

def persist_caption_result(form_path: str, caption: str, tags: List[str]) -> bool:
    """Actualiza el archivo del formulario con caption y tags."""
    try:
        data = load_form_data(form_path)
        data["caption"] = caption
        data["tags"] = tags
        with open(form_path, "w", encoding="utf-8") as handler:
            json.dump(data, handler, ensure_ascii=False, indent=2)
        return True
    except Exception as err:
        logger.error(f"❌ Error guardando caption/tags en {form_path}: {err}")
        return False

def generate_and_update(modelo: str, form_path: str):
    """Función pública principal que usa el nuevo sistema inteligente de tags"""
    try:
        logger.info(f"🚀 Iniciando generación INTELIGENTE de caption y tags para modelo: {modelo}")
        
        # Generar contenido con el sistema mejorado
        result = generate_caption_and_tags(modelo, form_path)
        
        if not result.success:
            logger.error(f"❌ Error generando contenido: {result.error}")
            return
        
        # Obtener nombre del video
        form_data = load_form_data(form_path)
        video_filename = form_data.get("video_filename", "")
        
        if not video_filename:
            logger.error("❌ No se encontró video_filename en form data")
            return
        
        # Guardar en JSON local (backup)
        success = persist_caption_result(form_path, result.caption, result.tags)
        if success:
            logger.info("✅ Backup local guardado")
        
        # Insertar en Supabase
        try:
            from database.supabase_client import get_model_config, insert_schedule, ensure_model_exists
            
            # Asegurar que el modelo existe en Supabase
            ensure_model_exists(modelo)
            
            # Obtener plataformas del modelo
            config = get_model_config(modelo)
            if not config:
                logger.warning(f"⚠️ No se encontró configuración para {modelo} en Supabase")
                return
            
            # Parsear plataformas
            plataformas = [p.strip() for p in config['plataformas'].split(',')]
            
            # Convertir tags de lista a string separado por comas
            tags_str = ','.join(result.tags)
            
            # Insertar un schedule por cada plataforma
            for plataforma in plataformas:
                inserted = insert_schedule(
                    modelo=modelo,
                    video=video_filename,
                    caption=result.caption,
                    tags=tags_str,
                    plataforma=plataforma,
                    estado='pendiente',
                    scheduled_time=''  # Se llenará después por scheduler
                )
                if inserted:
                    logger.info(f"✅ Schedule insertado en Supabase: {modelo} -> {plataforma}")
                else:
                    logger.error(f"❌ Error insertando schedule: {modelo} -> {plataforma}")
                    
        except ImportError:
            logger.warning("⚠️ supabase_client no disponible, saltando inserción en Supabase")
        except Exception as e:
            logger.error(f"❌ Error insertando en Supabase: {e}")
            
    except Exception as e:
        logger.error(f"❌ Error en generate_and_update: {e}")

if __name__ == "__main__":
    # Para testing
    import sys
    if len(sys.argv) >= 3:
        modelo = sys.argv[1]
        form_path = sys.argv[2]
        generate_and_update(modelo, form_path)
    else:
        print("Uso: python caption.py <modelo> <form_path>")