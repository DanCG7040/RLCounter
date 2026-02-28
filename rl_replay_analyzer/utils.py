"""
Utilidades para el analizador de replays de Rocket League.

- Conversión de segundos a formato mm:ss (tiempo del marcador).
- Helpers para leer propiedades del header (equipos, etc.).
"""

from __future__ import annotations


def seconds_to_mm_ss(seconds: float) -> str:
    """
    Convierte segundos a formato mm:ss (tiempo del marcador).

    Args:
        seconds: Tiempo en segundos (p. ej. tiempo restante del crono).

    Returns:
        Cadena en formato "mm:ss" (ej: "02:52", "00:05").
    """
    total_seconds = int(max(0.0, seconds))  # truncar para coincidir con el marcador
    minutes = total_seconds // 60
    secs = total_seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def get_prop(replay_data: dict, key: str):
    """
    Obtiene una propiedad del replay por nombre desde la lista de propiedades del header.

    En boxcars, las propiedades del header suelen ser una lista de [nombre, valor].
    El valor puede ser dict con 'Str', 'Int', 'Array', etc.

    Args:
        replay_data: Diccionario del replay (con clave 'properties' o similar).
        key: Nombre de la propiedad (ej: 'TeamNames', 'ReplayTime').

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
    Extrae el primer string de un valor de propiedad del header (Array o Struct).

    Útil para nombres de equipo cuando el valor es una estructura anidada.

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
        return first_string_from_header_prop(prop_value[1])
    if isinstance(prop_value, dict):
        for k in ("Str", "Name", "string"):
            if k in prop_value and isinstance(prop_value[k], str):
                s = prop_value[k].strip()
                return s if s else None
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
