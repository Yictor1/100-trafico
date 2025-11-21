import os
import random
import datetime as dt
from pathlib import Path
from typing import List, Tuple, Dict

from dotenv import load_dotenv
load_dotenv()

import sys
# Añadir directorio src al path para importar database
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Importar cliente de Supabase (import absoluto)
from database.supabase_client import get_model_config, get_all_schedules

MIN_GAP_MINUTES = int(os.getenv("MIN_GAP_MINUTES", "10"))
MAX_DAYS_AHEAD = int(os.getenv("MAX_DAYS_AHEAD", "30"))
MAX_SAME_VIDEO = int(os.getenv("MAX_SAME_VIDEO", "6"))  # tope 6 apariciones

def now_tz() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=-5)))

def parse_dt_local(s: str) -> dt.datetime:
    # Espera "YYYY-MM-DD HH:MM:SS" en zona Bogotá
    y, mo, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
    H, M, S = int(s[11:13]), int(s[14:16]), int(s[17:19])
    return dt.datetime(y, mo, d, H, M, S, tzinfo=dt.timezone(dt.timedelta(hours=-5)))

def fmt_dt_local(x: dt.datetime) -> str:
    return x.strftime("%Y-%m-%d %H:%M:%S")

def _get_model_config(modelo: str):
    """
    Obtiene configuración del modelo desde Supabase.
    Reemplaza _get_modelos_row() que usaba Google Sheets.
    
    Returns:
        Tuple (plataformas: List[str], hora_inicio: str, ventana_horas: int)
    """
    config = get_model_config(modelo)
    if not config:
        raise ValueError(f"Modelo '{modelo}' no existe en tabla 'modelos'.")
    
    # Parsear plataformas (están separadas por comas)
    plataformas = [p.strip().lower() for p in config['plataformas'].split(',') if p.strip()]
    hora_inicio = config['hora_inicio']
    ventana_horas = config['ventana_horas']
    
    return plataformas, hora_inicio, ventana_horas

def _get_all_records(modelo: str) -> List[Dict]:
    """
    Obtiene todos los registros de un modelo desde Supabase.
    Reemplaza _get_all_records(ws) que usaba Google Sheets.
    
    Returns:
        Lista de diccionarios con los schedules
    """
    return get_all_schedules(modelo)

def _video_total_count(records, video_filename: str) -> int:
    cnt = 0
    for r in records:
        if (r.get("video") or "").strip() == video_filename:
            cnt += 1
    return cnt

def _distinct_videos_on_date(records, date_str: str) -> int:
    vids = set()
    for r in records:
        st = (r.get("scheduled_time") or "").strip()
        if len(st) >= 10 and st[:10] == date_str:
            v = (r.get("video") or "").strip()
            if v:
                vids.add(v)
    return len(vids)

def _occupied_on_date(records, date_str: str) -> List[dt.datetime]:
    occ = []
    for r in records:
        st = (r.get("scheduled_time") or "").strip()
        if len(st) >= 19 and st[:10] == date_str:
            try:
                occ.append(parse_dt_local(st))
            except Exception:
                pass
    return sorted(occ)

def _within_window(candidate: dt.datetime, start: dt.datetime, end: dt.datetime) -> bool:
    return start <= candidate <= end

def _valid_gap(candidate: dt.datetime, others: List[dt.datetime], gap_min: int) -> bool:
    for h in others:
        if abs((candidate - h).total_seconds()) < gap_min * 60:
            return False
    return True

def _build_slots_for_day(n: int, start: dt.datetime, hours: int, occupied: List[dt.datetime]) -> List[dt.datetime]:
    gap = MIN_GAP_MINUTES
    end = start + dt.timedelta(hours=hours)

    proposals: List[dt.datetime] = []
    now_local = now_tz()
    # 1) primer slot cerca de inicio
    if n >= 1:
        jitter = dt.timedelta(minutes=random.randint(0, 5))
        c = (start + jitter).replace(second=0, microsecond=0)
        if _within_window(c, start, end) and _valid_gap(c, occupied + proposals, gap) and c >= now_local:
            proposals.append(c)

    # 2) segundo slot cerca de fin
    if n >= 2:
        jitter = dt.timedelta(minutes=random.randint(0, 5))
        c = (end - jitter).replace(second=0, microsecond=0)
        if _within_window(c, start, end) and _valid_gap(c, occupied + proposals, gap) and c >= now_local:
            proposals.append(c)

    # 3) midpoint entre 1 y 2
    if n >= 3 and len(proposals) >= 2:
        a, b = sorted(proposals)[0], sorted(proposals)[-1]
        c = (a + (b - a) / 2).replace(second=0, microsecond=0)
        if _within_window(c, start, end) and _valid_gap(c, occupied + proposals, gap) and c >= now_local:
            proposals.append(c)

    # 4) midpoints válidos entre ocupados + propuestos (≥ 2×gap)
    def midpoints_fill():
        nonlocal proposals
        timeline = sorted(occupied + proposals)
        made = 0
        for i in range(len(timeline) - 1):
            a, b = timeline[i], timeline[i + 1]
            if (b - a) >= dt.timedelta(minutes=2 * gap):
                c = (a + (b - a) / 2).replace(second=0, microsecond=0)
                if _within_window(c, start, end) and _valid_gap(c, occupied + proposals, gap) and c >= now_local:
                    proposals.append(c)
                    made += 1
                    if len(proposals) >= n:
                        break
        return made

    while len(proposals) < n and midpoints_fill() > 0:
        pass

    # 5) relleno hacia adelante en pasos de gap
    t = start
    while len(proposals) < n:
        t = t.replace(second=0, microsecond=0)
        if _within_window(t, start, end) and _valid_gap(t, occupied + proposals, gap) and t >= now_local:
            proposals.append(t)
        t += dt.timedelta(minutes=gap)
        if t > end:
            break

    return sorted(proposals)[:n]

def plan(modelo: str, video_filename: str) -> List[Tuple[str, str]]:
    """
    Devuelve lista [(plataforma, "YYYY-MM-DD HH:MM:SS")] siguiendo las reglas.
    Ahora usa Supabase en lugar de Google Sheets.
    """
    # Obtener configuración del modelo desde Supabase
    plataformas, hora_inicio_str, ventana_horas = _get_model_config(modelo)
    if not plataformas:
        raise ValueError("sin_plataformas")

    # Obtener registros existentes desde Supabase
    records = _get_all_records(modelo)

    # Tope del mismo video
    if _video_total_count(records, video_filename) >= MAX_SAME_VIDEO:
        raise ValueError("tope_video")

    # Hora inicio base
    H, M = [int(x) for x in hora_inicio_str.split(":")]
    tz = dt.timezone(dt.timedelta(hours=-5))
    today = now_tz().date()

    # Búsqueda hasta MAX_DAYS_AHEAD
    for day_offset in range(MAX_DAYS_AHEAD + 1):
        date_obj = today + dt.timedelta(days=day_offset)
        date_str = date_obj.strftime("%Y-%m-%d")

        # Capacidad por día (3 videos distintos)
        if _distinct_videos_on_date(records, date_str) >= 3:
            continue

        start = dt.datetime(date_obj.year, date_obj.month, date_obj.day, H, M, 0, tzinfo=tz)
        end = start + dt.timedelta(hours=ventana_horas)

        # Regla “hoy si aún no pasó hora_inicio; si ya pasó, hoy igual pero respetando ahora≥inicio (si no alcanza, pasa a mañana)”
        if day_offset == 0:
            now_local = now_tz()
            if now_local > end:
                # la ventana de hoy ya pasó
                continue
            # si ya pasó inicio, simplemente ocupamos considerando now en validación (hecho en _build_slots_for_day)

        occupied = _occupied_on_date(records, date_str)
        times = _build_slots_for_day(len(plataformas), start, ventana_horas, occupied)

        if len(times) == len(plataformas):
            # Éxito: mapea en orden
            return [(plataformas[i], fmt_dt_local(times[i])) for i in range(len(plataformas))]

    raise ValueError("sin_espacio")
