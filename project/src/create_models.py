"""Utilidades para crear la estructura de modelos a partir de datos crudos.

Antes este script dependía de Google Sheets y Discord. Ahora actúa como una
capa de normalización que recibe diccionarios (por ejemplo, del bot de Telegram
o de Supabase), crea/actualiza la carpeta del modelo y genera los payloads que
en el futuro se enviarán a Supabase mediante MCP.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parents[2]
MODELS_DIR = BASE_DIR / "modelos"
QUEUE_DIR = BASE_DIR / "supabase_queue"


def normalize_folder_name(name: str) -> str:
    """Normaliza el nombre para que sea seguro en cualquier SO."""
    return (
        name.replace("/", "_")
        .replace(":", "_")
        .replace("\\", "_")
        .replace("*", "_")
        .replace("?", "_")
        .replace('"', "_")
        .replace("<", "_")
        .replace(">", "_")
        .replace("|", "_")
    )


def build_config(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transforma datos crudos a la estructura esperada en config.json."""
    profile_id = (
        form_data.get("ID Incogniton")
        or form_data.get("ID Incognito")
        or form_data.get("ID")
        or ""
    )

    target_url: Dict[str, str] = {}
    if form_data.get("URL xxxfollow"):
        target_url["xxxfollow"] = form_data["URL xxxfollow"]
    if form_data.get("URL My.Club"):
        target_url["myclub"] = form_data["URL My.Club"]

    metadata = {
        "Tipo de cuerpo": form_data.get("Tipo de cuerpo", ""),
        "Tamano de pechos": form_data.get("Tamano de pechos", ""),
        "Tamano de culo": form_data.get("Tamano de culo", ""),
        "Color de cabello": form_data.get("Color de cabello", ""),
        "Categoria": form_data.get("Categoria", ""),
        "Piercings": form_data.get("Piercings", ""),
        "Tatuajes": form_data.get("Tatuajes", ""),
    }

    return {
        "profile_id": profile_id,
        "target_url": target_url,
        "metadata": metadata,
    }


def create_model_folder(model_name: str, form_data: Dict[str, Any]) -> Path:
    """Crea/actualiza la carpeta del modelo y persiste config.json."""
    normalized_name = normalize_folder_name(model_name)
    model_path = MODELS_DIR / normalized_name
    model_path.mkdir(parents=True, exist_ok=True)

    config_payload = build_config(form_data)
    config_path = model_path / "config.json"
    config_path.write_text(json.dumps(config_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return model_path


def _ensure_queue_dir() -> None:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)


def queue_supabase_payload(event: str, payload: Dict[str, Any]) -> Path:
    """Guarda un payload en formato JSONL para ser enviado vía MCP."""
    _ensure_queue_dir()
    queue_file = QUEUE_DIR / f"{event}.jsonl"
    with queue_file.open("a", encoding="utf-8") as handler:
        handler.write(json.dumps(payload, ensure_ascii=False))
        handler.write("\n")
    return queue_file


def build_supabase_payload(model_name: str, form_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Genera el cuerpo que luego insertaremos en Supabase."""
    return {
        "model_slug": normalize_folder_name(model_name),
        "display_name": model_name,
        "profile_id": config.get("profile_id"),
        "target_url": config.get("target_url"),
        "metadata": config.get("metadata"),
        "channel_id": form_data.get("channel_id"),
        "telegram_username": form_data.get("telegram_username"),
    }


def process_form_submission(form_data: Dict[str, Any], queue_event: Optional[str] = "models") -> Dict[str, Any]:
    """Entry point principal usado por el bot.

    - Valida datos mínimos
    - Genera/actualiza carpeta del modelo
    - Encola payload para Supabase (si se indica)
    """
    model_name = (
        form_data.get("Nombre modelo")
        or form_data.get("model_name")
        or form_data.get("nombre")
    )
    if not model_name:
        raise ValueError("form_data debe incluir el nombre del modelo.")

    model_path = create_model_folder(model_name, form_data)
    config_payload = json.loads((model_path / "config.json").read_text(encoding="utf-8"))
    supabase_payload = build_supabase_payload(model_name, form_data, config_payload)

    queue_path: Optional[Path] = None
    if queue_event:
        queue_path = queue_supabase_payload(queue_event, supabase_payload)

    return {
        "model_path": str(model_path),
        "config_path": str(model_path / "config.json"),
        "supabase_payload": supabase_payload,
        "queue_file": str(queue_path) if queue_path else None,
    }


def main() -> None:
    """Permite procesar un archivo JSON sencillo desde la terminal."""
    import argparse

    parser = argparse.ArgumentParser(description="Normaliza un modelo a partir de un JSON.")
    parser.add_argument("json_path", help="Ruta al archivo JSON con los datos del modelo.")
    args = parser.parse_args()

    data = json.loads(Path(args.json_path).read_text(encoding="utf-8"))
    result = process_form_submission(data)
    print("✅ Modelo procesado correctamente:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
