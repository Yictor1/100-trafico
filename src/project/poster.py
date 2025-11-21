import os
import time
import subprocess
import json
from datetime import datetime
import pytz
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Cargar variables de entorno
# Cargar variables de entorno
# Cargar variables de entorno
BASE_DIR = Path(__file__).resolve().parents[2]
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)

# Configuración Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError(f"Faltan credenciales de Supabase en .env ({env_path})")

supabase: Client = create_client(url, key)

def get_all_models():
    """Obtiene la lista de todos los modelos registrados."""
    try:
        response = supabase.table('modelos').select("modelo").execute()
        return [item['modelo'] for item in response.data] if response.data else []
    except Exception as e:
        print(f"Error obteniendo modelos: {e}")
        return []

def get_pending_posts(modelo):
    """Busca posts pendientes para un modelo específico."""
    # Usar timezone de Colombia (UTC-5)
    colombia_tz = pytz.timezone('America/Bogota')
    now_colombia = datetime.now(colombia_tz)
    # Convertir a string sin timezone para comparar con Supabase (que guarda sin tz)
    now_str = now_colombia.strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"   🕐 Hora actual (Colombia): {now_str}")
    try:
        # Primero ver TODOS los posts para debug
        all_posts = supabase.table(modelo).select("*").execute()
        print(f"   📊 Total posts en tabla: {len(all_posts.data) if all_posts.data else 0}")
        if all_posts.data:
            for p in all_posts.data[:3]:  # Mostrar primeros 3
                print(f"      - {p.get('video', 'N/A')}: estado={p.get('estado')}, scheduled={p.get('scheduled_time')}")
        
        # Columnas: video, caption, tags, plataforma, estado, scheduled_time
        response = supabase.table(modelo)\
            .select("*")\
            .eq('estado', 'pendiente')\
            .lte('scheduled_time', now_str)\
            .execute()
        return response.data
    except Exception as e:
        print(f"Error consultando tabla {modelo}: {e}")
        return []

def process_post(modelo, post):
    """Procesa un post individual ejecutando el worker de Playwright."""
    print(f"🔄 Procesando post para {modelo}: {post.get('video', 'Sin video')}")
    
    # 1. Actualizar estado a 'procesando'
    match_query = supabase.table(modelo).update({'estado': 'procesando'})
    if 'id' in post:
        match_query = match_query.eq('id', post['id'])
    else:
        match_query = match_query.eq('video', post['video']).eq('plataforma', post['plataforma'])
    
    match_query.execute()
    
    # 2. Preparar entorno para el worker
    env = os.environ.copy()
    
    # Construir ruta absoluta del video: Trafico/modelos/{modelo}/{video}
    video_path = BASE_DIR / "modelos" / modelo / post['video']
    
    env['VIDEO_PATH'] = str(video_path)
    env['VIDEO_TITLE'] = post.get('caption', '') # Usamos caption como título
    env['VIDEO_TAGS'] = post.get('tags', '')
    env['MODEL_NAME'] = modelo # Nombre del modelo para aislar sesión
    
    # Validar que el archivo existe
    if not video_path.exists():
        print(f"❌ Archivo no encontrado: {video_path}")
        # Actualizar error
        err_query = supabase.table(modelo).update({'estado': 'fallido'}) # No hay columna error_log standard, solo estado
        if 'id' in post:
            err_query = err_query.eq('id', post['id'])
        else:
            err_query = err_query.eq('video', post['video']).eq('plataforma', post['plataforma'])
        err_query.execute()
        return

    # 3. Ejecutar kams.js (Solo si la plataforma es 'kams' o similar)
    # El usuario mencionó @[plataformas], asumimos que el script kams.js es para esa plataforma.
    # Deberíamos verificar post['plataforma'].
    
    plataforma = post.get('plataforma', '').lower()
    
    # Mapeo de scripts por plataforma
    script_map = {
        'kams': 'workers/kams.js',
        'kams.com': 'workers/kams.js',
        # Agregar otros aquí
    }
    
    script_rel_path = script_map.get(plataforma)
    
    if not script_rel_path:
        print(f"⚠️  Plataforma no soportada por este scheduler: {plataforma}")
        return # No marcamos como fallido, tal vez otro proceso lo maneja

    try:
        script_path = BASE_DIR / script_rel_path
        
        if not script_path.exists():
            print(f"❌ Script no encontrado: {script_path}")
            raise FileNotFoundError(f"Script no encontrado: {script_path}")
        
        cmd = ["npx", "playwright", "test", str(script_path)]
        
        print(f"🚀 Ejecutando: {' '.join(cmd)}")
        print(f"📂 Directorio de trabajo: {BASE_DIR}")
        print(f"🎬 Video: {env['VIDEO_PATH']}")
        print(f"📝 Título: {env['VIDEO_TITLE']}")
        print(f"🏷️  Tags: {env['VIDEO_TAGS']}")
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=str(BASE_DIR))
        
        final_status = 'publicado' if result.returncode == 0 else 'fallido'
        
        if result.returncode == 0:
            print(f"✅ Publicado exitosamente: {post.get('video')}")
            if result.stdout:
                print("STDOUT:", result.stdout[-500:])  # Últimas 500 chars
        else:
            print(f"❌ Falló la publicación: {post.get('video')}")
            print(f"Return code: {result.returncode}")
            if result.stderr:
                print("STDERR:", result.stderr[-1000:])  # Últimas 1000 chars
            if result.stdout:
                print("STDOUT:", result.stdout[-1000:])
            
        # Actualizar estado final
        upd_query = supabase.table(modelo).update({'estado': final_status})
        if 'id' in post:
            upd_query = upd_query.eq('id', post['id'])
        else:
            upd_query = upd_query.eq('video', post['video']).eq('plataforma', post['plataforma'])
        upd_query.execute()
            
    except Exception as e:
        print(f"❌ Error ejecutando worker: {e}")
        # Update fail
        fail_query = supabase.table(modelo).update({'estado': 'fallido'})
        if 'id' in post:
            fail_query = fail_query.eq('id', post['id'])
        else:
            fail_query = fail_query.eq('video', post['video']).eq('plataforma', post['plataforma'])
        fail_query.execute()

def main():
    print("🚀 Iniciando Scheduler Multi-Modelo...")
    while True:
        modelos = get_all_models()
        print(f"🔍 Modelos encontrados: {modelos}")
        if not modelos:
            print("⚠️  No se encontraron modelos en la tabla 'modelos'.")
        
        for modelo in modelos:
            print(f"🔍 Verificando {modelo}...")
            posts = get_pending_posts(modelo)
            print(f"   Posts pendientes para {modelo}: {len(posts) if posts else 0}")
            if posts:
                print(f"\n📬 {modelo}: {len(posts)} posts pendientes.")
                for post in posts:
                    process_post(modelo, post)
        
        print(f"💤 Esperando 60 segundos...")
        time.sleep(60) # Verificar cada minuto

if __name__ == "__main__":
    main()
