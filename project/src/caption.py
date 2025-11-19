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
    gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    gemini_model = None

# ---- Logging ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CaptionResult:
    """Resultado de la generación de caption y tags"""
    caption: str
    tags: List[str]
    success: bool
    error: Optional[str] = None

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
        tags_path = os.path.join(os.path.dirname(__file__), "tags_disponibles.json")
        with open(tags_path, "r", encoding="utf-8") as f:
            tags_data = json.load(f)
        
        selected_tags = []
        
        # Helpers al inicio
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
        
        # Normalizar que_vendes y outfit (aceptar strings o listas)
        q = form_data.get("que_vendes", [])
        o = form_data.get("outfit", [])
        que_vendes = q if isinstance(q, list) else [q] if q else []
        outfit_list = o if isinstance(o, list) else [o] if o else []
        
        # 1. Tags basados en que_vendes (body_focus)
        for item in que_vendes:
            item_lower = item.lower()
            
            # Mapear que_vendes a body_focus
            if item_lower in ["culo", "ass"]:
                # Buscar en body_focus ass
                for body_focus in tags_data.get("body_focus", []):
                    if body_focus.get("id") == "ass":
                        # Aplicar facet_from_config si existe
                        facet_key = body_focus.get("facet_from_config")
                        if facet_key:
                            # Mapear a config.json usando función de normalización
                            config_value = map_size_es_to_en(model_config.get("metadata", {}).get("Tamano de culo", ""))
                            facet_map = body_focus.get("facet_map", {})
                            
                            if config_value and config_value in facet_map:
                                selected_tags.append(facet_map[config_value])  # Mantener #
                        
                        # Filtra los tags de tamaño en el pool del foco
                        pool_tags = [t for t in body_focus.get("pool", []) if t not in {"#BigAss","#SmallAss"}]
                        selected_tags.extend(pool_tags[:2])  # no más de 2 del foco
                        break
            
            elif item_lower in ["tetas", "boobs"]:
                for body_focus in tags_data.get("body_focus", []):
                    if body_focus.get("id") == "boobs":
                        facet_key = body_focus.get("facet_from_config")
                        if facet_key:
                            config_value = map_size_es_to_en(model_config.get("metadata", {}).get("Tamano de pechos", ""))
                            facet_map = body_focus.get("facet_map", {})
                            
                            if config_value and config_value in facet_map:
                                selected_tags.append(facet_map[config_value])  # Mantener #
                        
                        # Filtra los tags de tamaño en el pool del foco
                        pool_tags = [t for t in body_focus.get("pool", []) if t not in {"#BigTits","#SmallTits"}]
                        selected_tags.extend(pool_tags[:2])  # no más de 2 del foco
                        break
            
            elif item_lower in ["pies", "feet"]:
                for body_focus in tags_data.get("body_focus", []):
                    if body_focus.get("id") == "feet":
                        selected_tags += _pick_from_pool(body_focus.get("pool", []), selected_tags, 2)
                        break
            
            elif item_lower in ["cara", "face"]:
                for body_focus in tags_data.get("body_focus", []):
                    if body_focus.get("id") == "face":
                        selected_tags += _pick_from_pool(body_focus.get("pool", []), selected_tags, 2)
                        break
            
            elif item_lower in ["vagina", "pussy"]:
                for body_focus in tags_data.get("body_focus", []):
                    if body_focus.get("id") == "pussy":
                        selected_tags += _pick_from_pool(body_focus.get("pool", []), selected_tags, 2)
                        break
            
            elif item_lower in ["cuerpo completo", "fullbody"]:
                for body_focus in tags_data.get("body_focus", []):
                    if body_focus.get("id") == "fullbody":
                        selected_tags += _pick_from_pool(body_focus.get("pool", []), selected_tags, 2)
                        break
        
        # 2. Tags basados en outfit (genérico desde JSON)
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
            
            # Outfit: máximo 2 y aplica adds
            pool = [t for t in o.get("pool", []) if t not in selected_tags]
            selected_tags += pool[:2]  # antes era [:3]
            
            # adds_from_body_focus (ej. thong→pussy+ass, topless→boobs, heels→feet)
            for add in o.get("adds_from_body_focus", []):
                fid = add.get("focus")
                cnt = int(add.get("count", 1))
                bf = next((b for b in tags_data.get("body_focus", []) if b.get("id")==fid), None)
                if not bf: 
                    continue
                bf_pool = [t for t in bf.get("pool", []) if t not in selected_tags]
                # Si el focus añadido es 'ass', evita tamaños:
                if fid == "ass":
                    bf_pool = [t for t in bf_pool if t not in {"#BigAss", "#SmallAss"}]
                selected_tags += _pick_from_pool(bf_pool, selected_tags, cnt)
        
        # 3. Tags basados en model_traits del config.json (0–1 por trait)
        metadata = model_config.get("metadata", {})
        
        # Body type
        bt_pool = _match_trait(tags_data.get("model_traits", {}).get("body_type", []), metadata.get("Tipo de cuerpo",""))
        selected_tags += _pick_from_pool(bt_pool, selected_tags, 1)
        
        # Boobs size (NO añadir: ya lo resolvió facet_map)
        # Ass size   (NO añadir: ya lo resolvió facet_map)
        
        # Hair color
        hc_pool = _match_trait(tags_data.get("model_traits", {}).get("hair_color", []), metadata.get("Color de cabello",""))
        selected_tags += _pick_from_pool(hc_pool, selected_tags, 1)
        
        # Category
        cat_pool = _match_trait(tags_data.get("model_traits", {}).get("category", []), metadata.get("Categoria",""))
        selected_tags += _pick_from_pool(cat_pool, selected_tags, 1)
        
        # Tattoos (normaliza SI/NO → Sí/No con _norm comparando)
        tat_pool = _match_trait(tags_data.get("model_traits", {}).get("tattoos", []), metadata.get("Tatuajes",""))
        selected_tags += _pick_from_pool(tat_pool, selected_tags, 1)
        
        # Piercings
        pier_pool = _match_trait(tags_data.get("model_traits", {}).get("piercings", []), metadata.get("Piercings",""))
        selected_tags += _pick_from_pool(pier_pool, selected_tags, 1)
        
        # Corte final respetando política y dedupe
        unique_tags = list(dict.fromkeys(selected_tags))
        max_tags = tags_data.get("policy", {}).get("max_tags", 6)
        
        logger.info(f"Tags inteligentes generados: {len(unique_tags)} tags")
        return unique_tags[:max_tags]
        
    except Exception as e:
        logger.error(f"Error generando tags inteligentes: {e}")
        return []

def load_model_config(modelo: str) -> Dict:
    """Carga la configuración del modelo"""
    try:
        # Buscar desde el directorio raíz del proyecto
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Subir 3 niveles desde src/
        config_path = os.path.join(base_dir, "modelos", modelo, "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando config del modelo {modelo}: {e}")
        return {}

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
        logger.error(f"Error cargando form data: {e}")
        return {}

def call_gemini_api(prompt: str) -> Optional[str]:
    """Llama a la API de Gemini para generar caption"""
    if not gemini_model:
        logger.error("GEMINI_API_KEY no configurado")
        return None
    
    for attempt in range(MAX_RETRIES):
        try:
            response = gemini_model.generate_content(prompt)
            content = response.text
            
            if content:
                content = content.strip()
                logger.info("Respuesta exitosa de Gemini API")
                return content
                    
        except Exception as e:
            logger.error(f"Error llamando a Gemini (intento {attempt + 1}): {e}")
        
        if attempt < MAX_RETRIES - 1:
            time.sleep(2 ** attempt)  # Backoff exponencial
    
    return None

def generate_caption_and_tags(modelo: str, form_path: str) -> CaptionResult:
    """Función principal que genera caption y tags usando la nueva lógica"""
    try:
        # Cargar datos
        model_config = load_model_config(modelo)
        form_data = load_form_data(form_path)
        
        if not form_data:
            return CaptionResult("", [], False, "No se pudo cargar form data")
        
        # Usar la nueva lógica de tags inteligentes
        smart_tags = get_smart_tags_from_new_structure(form_data, model_config)
        
        if not smart_tags:
            return CaptionResult("", [], False, "No se pudieron generar tags inteligentes")
        
        # Generar caption con Gemini
        accion = form_data.get("que_vendes", [])
        outfit = form_data.get("outfit", [])
        metadata = model_config.get("metadata", {})
        
        # Normalizar para comparación
        que_vendes = accion if isinstance(accion, list) else [accion] if accion else []
        outfit_norm = outfit if isinstance(outfit, list) else [outfit] if outfit else []
        
        # Prompt para Gemini
        prompt = f"""
You are an expert in adult content marketing.
Write ONE very short, seductive caption in English for a porn short video.

Rules:
- Maximum 100 characters
- No emojis, no hashtags
- Style: sexy, direct, TikTok-porn like
- MUST include a strong call to action (examples: "I'm live now", "Come to private show", "Join me inside", "Don't miss this")

Context:
- Focus (que vendes): {que_vendes}
- Outfit: {outfit_norm}
- Model traits: Body {metadata.get("Tipo de cuerpo","")}, Boobs {metadata.get("Tamano de pechos","")},
  Ass {metadata.get("Tamano de culo","")}, Hair {metadata.get("Color de cabello","")}, 
  Category {metadata.get("Categoria","")}, Tattoos {metadata.get("Tatuajes","")}, Piercings {metadata.get("Piercings","")}
"""
        
        # Llamar a Gemini para generar caption
        ai_caption = call_gemini_api(prompt)
        
        if ai_caption:
            caption = ai_caption
            logger.info(f"Caption generado por Gemini: {caption}")
        else:
            # Fallback: caption genérico si Gemini falla
            logger.warning("Gemini falló, usando caption genérico")
            if "cuerpo completo" in que_vendes:
                caption = "Showing my full body just for you. Do you like what you see?"
            elif "culo" in que_vendes and "tacones" in outfit_norm:
                caption = "Showing off my curves in heels. Do you like it?"
            elif "tetas" in que_vendes:
                caption = "Playing with my boobs just for you."
            elif "pies" in que_vendes:
                caption = "Feet lovers paradise. Worship them."
            elif "desnuda" in outfit_norm:
                caption = "Completely naked and ready for you."
            elif "lenceria" in outfit_norm:
                caption = "Wearing sexy lingerie just for you."
            else:
                caption = "Exclusive content just for you."
        
        logger.info(f"Caption final: {caption}")
        logger.info(f"Tags inteligentes ({len(smart_tags)}): {smart_tags}")
        
        return CaptionResult(caption, smart_tags, True)
        
    except Exception as e:
        logger.error(f"Error generando caption y tags: {e}")
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
        logger.error(f"Error guardando caption/tags en {form_path}: {err}")
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
        
        # Logging detallado de resultados
        logger.info(f"✅ RESULTADOS GENERADOS:")
        logger.info(f"   📝 Caption: {result.caption}")
        logger.info(f"   🏷️  Tags ({len(result.tags)}): {', '.join(result.tags)}")
        
        # Guardar en JSON local (backup)
        success = persist_caption_result(form_path, result.caption, result.tags)
        if success:
            logger.info("✅ Caption y tags guardados en el formulario.")
        else:
            logger.warning("⚠️ No se pudieron persistir caption/tags (revisa logs).")
        
        # Insertar en Supabase
        try:
            from supabase_client import get_model_config, insert_schedule, ensure_model_exists
            
            # Asegurar que el modelo existe en Supabase
            ensure_model_exists(modelo)
            
            # Obtener plataformas del modelo
            config = get_model_config(modelo)
            if not config:
                logger.warning(f"⚠️ No se encontró configuración para {modelo} en Supabase")
                return
            
            # Parsear plataformas (están separadas por comas)
            plataformas = [p.strip() for p in config['plataformas'].split(',')]
            logger.info(f"📊 Plataformas para {modelo}: {plataformas}")
            
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