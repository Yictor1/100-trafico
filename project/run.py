#!/usr/bin/env python3
"""Launcher del bot centralizado de Telegram."""
import sys, os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python3"
BOT_MAIN = BASE_DIR / "project" / "src" / "bot_central.py"

if VENV_PYTHON.exists() and not sys.executable.startswith(str(BASE_DIR / ".venv")):
    print(f"⚠️  Recomiendo activar el entorno virtual:\n    source {BASE_DIR}/.venv/bin/activate\n")
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(BOT_MAIN)] + sys.argv[1:])

# Ejecutar directamente el bot central
os.execv(sys.executable, [sys.executable, str(BOT_MAIN)] + sys.argv[1:])

