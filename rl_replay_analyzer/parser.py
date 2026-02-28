"""
Parser de archivos .replay de Rocket League.

Extrae nombres de equipos (azul/naranja) y lista de goles con tiempo y equipo
desde la metadata del replay (header) y, si hace falta, tick marks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rl_replay_analyzer.exceptions import (
    InvalidReplayError,
    CorruptReplayError,
    MissingDataError,
)
from rl_replay_analyzer.utils import (
    get_prop,
    first_string_from_header_prop,
    keyframes_to_time_mapper,
    seconds_to_mm_ss,
)


def _replay_to_dict(replay: Any) -> dict:
    """Convierte el objeto replay (boxcars) a dict para acceso uniforme."""
    if replay is None:
        raise CorruptReplayError("Replay es None")
    if isinstance(replay, dict):
        return replay
    # Objeto con atributos (p. ej. desde pyo3/boxcars)
    if hasattr(replay, "__dict__"):
        return vars(replay)
    if hasattr(replay, "get"):
        return dict(replay)
    # Atributos conocidos de boxcars Replay
    known = ("properties", "tick_marks", "keyframes", "levels", "game_type")
    out = {}
    for name in known:
        if hasattr(replay, name):
            val = getattr(replay, name)
            if hasattr(val, "__iter__") and not isinstance(val, (str, bytes)):
                try:
                    out[name] = list(val) if val is not None else []
                except Exception:
                    out[name] = val
            else:
                out[name] = val
    if out:
        return out
    try:
        return json.loads(json.dumps(replay, default=lambda x: getattr(x, "__dict__", str(x))))
    except Exception as e:
        raise CorruptReplayError(f"No se pudo normalizar el replay: {e}") from e


def _get_team_names(replay_dict: dict) -> tuple[str, str]:
    """
    Extrae nombres del equipo azul y naranja desde la propiedad TeamNames del header.

    En partidas privadas, TeamNames es un ArrayProperty con dos elementos
    (blue, orange); cada uno puede ser un string o una estructura con Str/Name.
    """
    team_names_prop = get_prop(replay_dict, "TeamNames")
    blue_name: str | None = None
    orange_name: str | None = None

    # Formato boxcars: puede ser lista de listas de [key, value] o dict con "Array"
    array_data: list | None = None
    if isinstance(team_names_prop, list):
        array_data = team_names_prop
    elif isinstance(team_names_prop, dict) and "Array" in team_names_prop:
        array_data = team_names_prop["Array"]

    if array_data and len(array_data) >= 2:
        blue_name = first_string_from_header_prop(array_data[0])
        orange_name = first_string_from_header_prop(array_data[1])

    # Si no hay nombres custom (partida pública), usar Local / Visitante
    if not blue_name:
        blue_name = "Local"
    if not orange_name:
        orange_name = "Visitante"

    return blue_name, orange_name


def _parse_goals_from_property(replay_dict: dict, blue_name: str, orange_name: str) -> list[dict]:
    """
    Extrae goles desde la propiedad Goals del header (cada elemento con Frame y Team).
    """
    goals_prop = get_prop(replay_dict, "Goals")
    if goals_prop is None:
        return []

    # Goals puede ser Array de estructuras con "Frame" y "Team" (índice 0/1)
    array_data: list | None = None
    if isinstance(goals_prop, list):
        array_data = goals_prop
    elif isinstance(goals_prop, dict) and "Array" in goals_prop:
        array_data = goals_prop["Array"]

    if not array_data:
        return []

    keyframes = replay_dict.get("keyframes") or []
    frame_to_time = keyframes_to_time_mapper(keyframes)

    goals: list[dict] = []
    for entry in array_data:
        frame_val = None
        team_idx = None
        # Cada entry puede ser lista de [key, value] o dict
        if isinstance(entry, list):
            for pair in entry:
                if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                    continue
                k, v = pair[0], pair[1]
                if isinstance(k, str):
                    k = k.strip().rstrip("\x00")
                if k in ("Frame", "frame"):
                    frame_val = v if isinstance(v, int) else (v.get("Int") if isinstance(v, dict) else None)
                elif k in ("Team", "TeamIndex", "team", "PlayerTeam", "playerteam"):
                    if isinstance(v, int):
                        team_idx = v
                    elif isinstance(v, dict) and "Int" in v:
                        team_idx = v["Int"]
        elif isinstance(entry, dict):
            frame_val = entry.get("Frame") or entry.get("frame")
            team_idx = entry.get("Team") or entry.get("TeamIndex") or entry.get("team")
            if isinstance(frame_val, dict):
                frame_val = frame_val.get("Int")
            if isinstance(team_idx, dict):
                team_idx = team_idx.get("Int")

        if frame_val is None:
            continue
        frame = int(frame_val) if not isinstance(frame_val, int) else frame_val
        if team_idx == 0:
            team_name = blue_name
        elif team_idx == 1:
            team_name = orange_name
        else:
            team_name = "Unknown"
        time_str = seconds_to_mm_ss(frame_to_time(frame))
        goals.append({"time": time_str, "team": team_name})

    return goals


def _parse_goals_from_tick_marks(
    replay_dict: dict, blue_name: str, orange_name: str
) -> list[dict]:
    """
    Fallback: extrae goles desde tick_marks (description "Goal").
    No tenemos equipo en tick marks, se asigna "Unknown" o se omite equipo.
    """
    tick_marks = replay_dict.get("tick_marks") or []
    if not tick_marks:
        return []

    keyframes = replay_dict.get("keyframes") or []
    frame_to_time = keyframes_to_time_mapper(keyframes)

    goals = []
    for tm in tick_marks:
        if isinstance(tm, dict):
            desc = (tm.get("description") or "").strip().lower()
            frame_val = tm.get("frame")
        elif isinstance(tm, (list, tuple)) and len(tm) >= 2:
            desc = (str(tm[1].get("description", tm[1]) if isinstance(tm[1], dict) else tm[1]) or "").strip().lower()
            frame_val = tm[0] if isinstance(tm[0], int) else (tm[1].get("frame") if isinstance(tm[1], dict) else None)
        else:
            continue
        if "goal" not in desc:
            continue
        if frame_val is None:
            continue
        frame = int(frame_val)
        time_str = seconds_to_mm_ss(frame_to_time(frame))
        goals.append({"time": time_str, "team": "Unknown"})

    return goals


def extract_match_data(replay_dict: dict) -> dict:
    """
    Extrae equipos y goles ordenados cronológicamente desde un replay ya parseado (dict).

    Returns:
        Dict con estructura:
        {
          "teams": { "blue": str, "orange": str },
          "goals": [ { "time": "mm:ss", "team": str }, ... ]
        }
    """
    replay_dict = _replay_to_dict(replay_dict)
    blue_name, orange_name = _get_team_names(replay_dict)

    goals = _parse_goals_from_property(replay_dict, blue_name, orange_name)
    if not goals:
        goals = _parse_goals_from_tick_marks(replay_dict, blue_name, orange_name)

    # Orden cronológico por tiempo (mm:ss como string ordena bien si padding correcto)
    goals.sort(key=lambda g: (g["time"], g["team"]))

    return {
        "teams": {"blue": blue_name, "orange": orange_name},
        "goals": goals,
    }


def parse_replay_file(path: str | Path) -> dict:
    """
    Abre un archivo .replay, lo parsea y devuelve el resultado estructurado.

    Usa boxcars_py si está instalado; si no (p. ej. en Windows sin Rust),
    usa un parser en Python puro que solo lee el header.

    Args:
        path: Ruta al archivo .replay.

    Returns:
        Dict con "teams" y "goals" listos para resultado.json.

    Raises:
        InvalidReplayError: Archivo no encontrado o no válido.
        CorruptReplayError: Replay corrupto o no parseable.
        MissingDataError: Faltan datos necesarios en el replay.
    """
    path = Path(path)
    if not path.exists():
        raise InvalidReplayError(f"Archivo no encontrado: {path}")
    if path.suffix.lower() != ".replay":
        raise InvalidReplayError(f"Extensión esperada .replay: {path}")

    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        raise InvalidReplayError(f"No se pudo leer el archivo: {e}") from e

    try:
        from boxcars_py import parse_replay
    except ImportError:
        # Sin Rust/boxcars: usar parser en Python puro (solo header)
        from rl_replay_analyzer.header_parser import parse_header

        try:
            header_dict = parse_header(data)
        except CorruptReplayError:
            raise
        except Exception as e:
            raise CorruptReplayError(f"Error al parsear el header del replay: {e}") from e
        return extract_match_data(header_dict)

    try:
        replay = parse_replay(data)
    except Exception as e:
        raise CorruptReplayError(f"Error al parsear el replay: {e}") from e

    if replay is None:
        raise CorruptReplayError("El parser devolvió None")

    return extract_match_data(replay)
