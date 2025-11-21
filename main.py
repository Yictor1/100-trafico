import subprocess
import time
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python3"
BOT_MAIN = BASE_DIR / "src" / "project" / "bot_central.py"
POSTER_MAIN = BASE_DIR / "src" / "project" / "poster.py"

# Determinar qué python usar
if VENV_PYTHON.exists() and not sys.executable.startswith(str(BASE_DIR / ".venv")):
    print(f"⚠️  Recomiendo activar el entorno virtual:\n    source {BASE_DIR}/.venv/bin/activate\n")
    python_exe = str(VENV_PYTHON)
else:
    python_exe = sys.executable

print(f"🚀 Iniciando servicios con: {python_exe}")

processes = []

try:
    # Iniciar Bot Central
    print("🤖 Iniciando Bot Central...")
    p_bot = subprocess.Popen([python_exe, str(BOT_MAIN)])
    processes.append(p_bot)

    # Iniciar Poster Scheduler
    print("📅 Iniciando Poster Scheduler...")
    p_poster = subprocess.Popen([python_exe, str(POSTER_MAIN)])
    processes.append(p_poster)

    print("✅ Servicios iniciados. Presiona Ctrl+C para detener.")
    
    # Mantener vivo el proceso principal
    while True:
        time.sleep(1)
        # Verificar si algún proceso murió
        if p_bot.poll() is not None:
            print("❌ Bot Central se detuvo inesperadamente.")
            break
        if p_poster.poll() is not None:
            print("❌ Poster Scheduler se detuvo inesperadamente.")
            break

except KeyboardInterrupt:
    print("\n🛑 Deteniendo servicios...")
finally:
    for p in processes:
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
    print("👋 Adiós.")

