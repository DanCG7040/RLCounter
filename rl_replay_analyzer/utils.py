"""
Utilidades para el analizador de replays.

- Conversión de tiempo interno (frames / segundos) a formato mm:ss.
- Helpers para navegar propiedades del header (dict/list anidados).
"""

from typing import Callable

# FPS típico del replay de Rocket League para tiempo de juego
REPLAY_FPS = 30


def frame_to_seconds(frame: int, fps: int = REPLAY_FPS) -> float:
    """
    Convierte un número de frame del replay a segundos de partido.

    Args:
        frame: Número de frame en el replay.
        fps: Frames por segundo (por defecto 30 en RL).

    Returns:
        Tiempo en segundos.
    """
    return frame / fps


def seconds_to_mm_ss(seconds: float) -> str:
    """
    Convierte segundos a formato mm:ss (siempre 2 dígitos en minutos).

    Args:
        seconds: Tiempo en segundos (puede ser decimal).

    Returns:
        Cadena en formato "mm:ss" (ej: "04:23", "00:05").
    """
    total_seconds = int(round(seconds))
    minutes = total_seconds // 60
    secs = total_seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def frame_to_mm_ss(frame: int, fps: int = REPLAY_FPS) -> str:
    """
    Convierte un frame del replay directamente a formato mm:ss.

    Args:
        frame: Número de frame.
        fps: Frames por segundo.

    Returns:
        Tiempo en formato "mm:ss".
    """
    return seconds_to_mm_ss(frame_to_seconds(frame, fps))


def get_prop(replay_data: dict, key: str):
    """
    Obtiene una propiedad del replay por nombre desde la lista de propiedades.

    En boxcars, replay['properties'] es una lista de [nombre, valor].
    El valor puede ser un dict con claves como 'Str', 'Int', 'Array', etc.
    (según serialización de HeaderProp).

    Args:
        replay_data: Diccionario del replay (o con clave 'properties').
        key: Nombre de la propiedad (ej: 'TeamNames', 'Goals').

    Returns:
        Valor de la propiedad o None si no existe.
    """
    properties = replay_data.get("properties") if isinstance(replay_data, dict) else None
    if not properties:
        return None
    for item in properties:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        prop_name, prop_value = item[0], item[1]
        if prop_name == key:
            return prop_value
    return None


def first_string_from_header_prop(prop_value) -> str | None:
    """
    Extrae el primer string de un HeaderProp (Array o Struct).

    Útil para nombres de equipo cuando el valor es una estructura anidada
    (ej. Array de un elemento con Str).

    Args:
        prop_value: Valor tal como viene del replay (dict/list).

    Returns:
        Primera cadena encontrada o None.
    """
    if prop_value is None:
        return None
    if isinstance(prop_value, str):
        return prop_value.strip() or None
    if isinstance(prop_value, tuple) and len(prop_value) >= 2:
        # Par (nombre, valor) del parser puro; el valor puede ser el string
        return first_string_from_header_prop(prop_value[1])
    if isinstance(prop_value, dict):
        # HeaderProp serializado: puede ser {"Str": "nombre"} o {"Name": "nombre"}
        for k in ("Str", "Name", "string"):
            if k in prop_value and isinstance(prop_value[k], str):
                s = prop_value[k].strip()
                return s if s else None
        # Struct con "fields": lista de [nombre, valor]
        for field_list in prop_value.get("fields", prop_value.get("Struct", [])):
            if isinstance(field_list, (list, tuple)) and len(field_list) >= 2:
                out = first_string_from_header_prop(field_list[1])
                if out:
                    return out
        return None
    if isinstance(prop_value, list):
        for elem in prop_value:
            out = first_string_from_header_prop(elem)
            if out:
                return out
    return None


def keyframes_to_time_mapper(keyframes: list) -> Callable[[int], float]:
    """
    Construye una función que mapea frame -> tiempo en segundos usando keyframes.

    Si no hay keyframes, usa FPS fijo (frame/30).

    Args:
        keyframes: Lista de dicts con 'frame' y 'time' (float).

    Returns:
        Función (frame: int) -> float (segundos).
    """
    if not keyframes or not isinstance(keyframes, list):
        return lambda f: frame_to_seconds(f)

    # Ordenar por frame
    sorted_kf = sorted(
        (k for k in keyframes if isinstance(k, dict) and "frame" in k and "time" in k),
        key=lambda x: x["frame"],
    )
    if not sorted_kf:
        return lambda f: frame_to_seconds(f)

    def frame_to_time(frame: int) -> float:
        # Antes del primer keyframe
        if frame <= sorted_kf[0]["frame"]:
            return sorted_kf[0]["time"] + (frame - sorted_kf[0]["frame"]) / REPLAY_FPS
        # Después del último
        if frame >= sorted_kf[-1]["frame"]:
            return sorted_kf[-1]["time"] + (frame - sorted_kf[-1]["frame"]) / REPLAY_FPS
        # Interpolar entre dos keyframes
        for i in range(len(sorted_kf) - 1):
            a, b = sorted_kf[i], sorted_kf[i + 1]
            if a["frame"] <= frame <= b["frame"]:
                t = (frame - a["frame"]) / (b["frame"] - a["frame"])
                return a["time"] + t * (b["time"] - a["time"])
        return frame_to_seconds(frame)

    return frame_to_time
