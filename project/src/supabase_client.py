"""
Cliente centralizado de Supabase para el proyecto Trafico.

Maneja:
- Conexión a Supabase
- Creación dinámica de tablas para nuevos modelos
- Operaciones CRUD en tablas de modelos y schedules
"""

import os
from typing import List, Dict, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Configuración
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://osdpemjvcsmfbacmjlcv.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_ANON_KEY no está configurado en .env")

# Cliente global
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_model_config(modelo: str) -> Optional[Dict]:
    """
    Obtiene la configuración de un modelo desde la tabla 'modelos'.
    
    Returns:
        Dict con {modelo, plataformas, hora_inicio, ventana_horas} o None si no existe
    """
    try:
        response = supabase.table("modelos").select("*").eq("modelo", modelo).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error obteniendo config de {modelo}: {e}")
        return None


def create_model_config(modelo: str, plataformas: str, hora_inicio: str = "12:00", ventana_horas: int = 5) -> bool:
    """
    Crea la configuración de un nuevo modelo en la tabla 'modelos'.
    
    Args:
        modelo: Nombre del modelo (slug)
        plataformas: Plataformas separadas por comas (ej: "xxxfollow,myclub")
        hora_inicio: Hora de inicio de ventana (ej: "12:00")
        ventana_horas: Duración de ventana en horas
    
    Returns:
        True si se creó exitosamente
    """
    try:
        data = {
            "modelo": modelo,
            "plataformas": plataformas,
            "hora_inicio": hora_inicio,
            "ventana_horas": ventana_horas
        }
        supabase.table("modelos").insert(data).execute()
        print(f"✅ Configuración de {modelo} creada en tabla 'modelos'")
        return True
    except Exception as e:
        print(f"Error creando config de {modelo}: {e}")
        return False


def table_exists(table_name: str) -> bool:
    """
    Verifica si una tabla existe en Supabase.
    
    Intenta hacer un select simple y si falla, asume que no existe.
    """
    try:
        supabase.table(table_name).select("*").limit(1).execute()
        return True
    except Exception:
        return False


def create_model_table(modelo: str) -> bool:
    """
    Crea una tabla para un modelo nuevo ejecutando el script Node.js con MCP.
    
    Args:
        modelo: Nombre del modelo (slug)
    
    Returns:
        True si se creó exitosamente
    """
    import subprocess
    from pathlib import Path
    
    try:
        # Verificar si ya existe
        if table_exists(modelo):
            print(f"ℹ️  Tabla '{modelo}' ya existe")
            return True
        
        print(f"🆕 Creando tabla para modelo nuevo: {modelo}")
        
        # Ruta al script de creación
        script_path = Path(__file__).parent / "create_model_table.js"
        
        if not script_path.exists():
            print(f"❌ Script no encontrado: {script_path}")
            return False
        
        # Ejecutar script Node.js
        result = subprocess.run(
            ["node", str(script_path), modelo],
            cwd=str(script_path.parent),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"✅ Tabla '{modelo}' creada exitosamente")
            return True
        else:
            print(f"❌ Error creando tabla '{modelo}':")
            print(result.stderr)
            return False
        
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout creando tabla '{modelo}'")
        return False
    except Exception as e:
        print(f"❌ Error creando tabla {modelo}: {e}")
        return False


def ensure_model_exists(modelo: str, plataformas: str = "xxxfollow,myclub", 
                       hora_inicio: str = "12:00", ventana_horas: int = 5) -> bool:
    """
    Asegura que un modelo existe tanto en la tabla 'modelos' como su tabla propia.
    
    Si no existe:
    1. Crea entrada en tabla 'modelos'
    2. Intenta crear tabla del modelo
    
    Args:
        modelo: Nombre del modelo
        plataformas: Plataformas por defecto
        hora_inicio: Hora de inicio por defecto
        ventana_horas: Ventana por defecto
    
    Returns:
        True si el modelo existe o se creó exitosamente
    """
    # Verificar si existe en tabla modelos
    config = get_model_config(modelo)
    
    if not config:
        print(f"🆕 Modelo nuevo detectado: {modelo}")
        create_model_config(modelo, plataformas, hora_inicio, ventana_horas)
    
    # Verificar si existe tabla del modelo
    if not table_exists(modelo):
        print(f"⚠️  Tabla '{modelo}' no existe en Supabase")
        print(f"   Creando tabla automáticamente...")
        if not create_model_table(modelo):
            print(f"❌ No se pudo crear tabla '{modelo}'")
            return False
    
    return True


def insert_schedule(modelo: str, video: str, caption: str, tags: str, 
                   plataforma: str, estado: str = "pendiente", 
                   scheduled_time: str = "") -> bool:
    """
    Inserta un schedule en la tabla del modelo.
    
    Args:
        modelo: Nombre del modelo
        video: Nombre del archivo de video
        caption: Caption generado
        tags: Tags separados por comas
        plataforma: Plataforma específica
        estado: Estado del post (pendiente, publicado)
        scheduled_time: Fecha/hora programada (formato: YYYY-MM-DD HH:MM:SS)
    
    Returns:
        True si se insertó exitosamente
    """
    try:
        data = {
            "video": video,
            "caption": caption,
            "tags": tags,
            "plataforma": plataforma,
            "estado": estado,
            "scheduled_time": scheduled_time
        }
        supabase.table(modelo).insert(data).execute()
        print(f"✅ Schedule insertado en tabla '{modelo}'")
        return True
    except Exception as e:
        print(f"❌ Error insertando schedule en {modelo}: {e}")
        return False


def get_all_schedules(modelo: str) -> List[Dict]:
    """
    Obtiene todos los schedules de un modelo.
    
    Returns:
        Lista de diccionarios con los schedules
    """
    try:
        response = supabase.table(modelo).select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error obteniendo schedules de {modelo}: {e}")
        return []


def get_pending_schedules(modelo: str, plataforma: Optional[str] = None) -> List[Dict]:
    """
    Obtiene schedules pendientes de un modelo.
    
    Args:
        modelo: Nombre del modelo
        plataforma: Filtrar por plataforma específica (opcional)
    
    Returns:
        Lista de schedules pendientes
    """
    try:
        query = supabase.table(modelo).select("*").eq("estado", "pendiente")
        
        if plataforma:
            query = query.eq("plataforma", plataforma)
        
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error obteniendo schedules pendientes de {modelo}: {e}")
        return []


def update_schedule_time(modelo: str, video: str, plataforma: str, scheduled_time: str) -> bool:
    """
    Actualiza el scheduled_time de un schedule específico.
    
    Args:
        modelo: Nombre del modelo
        video: Nombre del video
        plataforma: Plataforma
        scheduled_time: Nueva fecha/hora programada
    
    Returns:
        True si se actualizó exitosamente
    """
    try:
        supabase.table(modelo).update({"scheduled_time": scheduled_time}).eq("video", video).eq("plataforma", plataforma).execute()
        return True
    except Exception as e:
        print(f"Error actualizando schedule: {e}")
        return False
