"""
Parser en Python puro del header de archivos .replay de Rocket League.

No requiere Rust/boxcars. Lee solo la sección header para extraer
TeamNames y Goals (y opcionalmente keyframes/tick_marks del footer si se necesita después).
Referencia: documentación no oficial del formato en rocket-league-replay-format.
"""

from __future__ import annotations

import struct
from typing import Any

from rl_replay_analyzer.exceptions import CorruptReplayError


class _Stream:
    """Lectura little-endian sobre bytes."""

    __slots__ = ("_buf", "_pos")

    def __init__(self, data: bytes):
        self._buf = data
        self._pos = 0

    def remaining(self) -> int:
        return len(self._buf) - self._pos

    def read(self, n: int) -> bytes:
        if self._pos + n > len(self._buf):
            raise CorruptReplayError(
                "El archivo no parece un replay válido de Rocket League. "
                "Comprueba que sea un .replay guardado desde el juego."
            )
        out = self._buf[self._pos : self._pos + n]
        self._pos += n
        return out

    def read_i32(self) -> int:
        val = struct.unpack_from("<i", self._buf, self._pos)[0]
        self._pos += 4
        return val

    def skip_i32(self) -> None:
        self._pos += 4

    def read_u32(self) -> int:
        val = struct.unpack_from("<I", self._buf, self._pos)[0]
        self._pos += 4
        return val

    def skip_u32(self) -> None:
        self._pos += 4

    def read_u64(self) -> int:
        self._pos += 8
        return struct.unpack_from("<Q", self._buf, self._pos - 8)[0]

    def read_f32(self) -> float:
        self._pos += 4
        return struct.unpack_from("<f", self._buf, self._pos - 4)[0]

    def advance(self, n: int) -> None:
        self._pos += n


def _read_string8(s: _Stream) -> str:
    """String8: UInt32 length, luego length bytes UTF-8 (sin último null)."""
    length = s.read_u32()
    if length == 0:
        return ""
    if length > s.remaining() or length > 10000:
        raise CorruptReplayError(
            "El archivo no parece un replay válido de Rocket League (datos corruptos o formato no soportado)."
        )
    raw = s.read(length)
    if raw and raw[-1:] == b"\x00":
        raw = raw[:-1]
    return raw.decode("utf-8", errors="replace")


def _read_string16(s: _Stream) -> str:
    """String16: Int32 length; si >0 son bytes Windows-1252, si <0 son UTF-16 (-length*2 bytes)."""
    length = s.read_i32()
    if length == 0:
        return ""
    if length > 0:
        raw = s.read(length)
        if raw and raw[-1:] == b"\x00":
            raw = raw[:-1]
        return raw.decode("windows-1252", errors="replace")
    else:
        byte_count = (-length) * 2
        raw = s.read(byte_count)
        if len(raw) >= 2 and raw[-2:] == b"\x00\x00":
            raw = raw[:-2]
        return raw.decode("utf-16-le", errors="replace")


def _read_property_value(s: _Stream, prop_type: str) -> Any:
    if prop_type == "IntProperty":
        val = struct.unpack_from("<i", s._buf, s._pos)[0]
        s.advance(4)
        return val
    if prop_type == "FloatProperty":
        return s.read_f32()
    if prop_type in ("StrProperty", "NameProperty"):
        return _read_string16(s)
    if prop_type == "BoolProperty":
        return s.read(1)[0] != 0
    if prop_type == "QWordProperty":
        return s.read_u64()
    if prop_type == "ByteProperty":
        s.advance(1)
        return None
    if prop_type == "ArrayProperty":
        return _read_array_property(s)
    if prop_type == "StructProperty":
        # Nombre del tipo de struct (String16) y luego propiedades anidadas hasta "None"
        _ = _read_string16(s)
        return _read_properties(s)
    if prop_type == "EnumProperty":
        s.advance(1)
        return None
    raise CorruptReplayError(f"Tipo de propiedad no soportado en header: {prop_type!r}")


def _skip_property_value(s: _Stream, prop_type: str) -> None:
    """Avanza el stream sin guardar el valor (para saltar propiedades que no necesitamos)."""
    if prop_type == "IntProperty":
        s.advance(4)
        return
    if prop_type == "FloatProperty":
        s.advance(4)
        return
    if prop_type in ("StrProperty", "NameProperty"):
        _ = _read_string16(s)
        return
    if prop_type == "BoolProperty":
        s.advance(1)
        return
    if prop_type == "QWordProperty":
        s.advance(8)
        return
    if prop_type in ("ByteProperty", "EnumProperty"):
        s.advance(1)
        return
    if prop_type == "ArrayProperty":
        count = s.read_u32()
        if count > 100000:
            raise CorruptReplayError("Array demasiado grande al saltar")
        for _ in range(count):
            _skip_properties(s)
        return
    if prop_type == "StructProperty":
        # Struct type name: puede ser String8 (UInt32 len) o String16 (Int32 len, negativo = UTF-16)
        pos = s._pos
        length = s.read_i32()
        if length > 0 and length < 10000:
            s.advance(length)
        elif length < 0 and length > -10000:
            s.advance((-length) * 2)
        else:
            s._pos = pos
            _ = _read_string16(s)
        _skip_properties(s)
        return
    raise CorruptReplayError(f"Tipo no soportado al saltar: {prop_type!r}")


def _skip_properties(s: _Stream) -> None:
    """Avanza el stream hasta el siguiente 'None' (fin de bloque de propiedades)."""
    while True:
        key = _read_string8(s)
        if key in ("None", "\x00\x00\x00None", ""):
            break
        prop_type = _read_string8(s)
        s.advance(8)
        _skip_property_value(s, prop_type)


# Propiedades que saltamos (structs anidados complejos) para evitar errores de formato
_SKIP_KEYS = frozenset(("PlayerStats", "HighLights"))


def _read_properties(s: _Stream) -> list[tuple[str, Any]]:
    """Lee una secuencia de propiedades hasta key 'None'."""
    out: list[tuple[str, Any]] = []
    while True:
        key = _read_string8(s)
        if key in ("None", "\x00\x00\x00None", ""):
            break
        prop_type = _read_string8(s)
        s.advance(8)  # unknown_001
        if key in _SKIP_KEYS:
            _skip_property_value(s, prop_type)
            continue
        try:
            value = _read_property_value(s, prop_type)
        except CorruptReplayError:
            raise
        except Exception as e:
            raise CorruptReplayError(f"Error leyendo propiedad {key!r} ({prop_type}): {e}") from e
        out.append((key, value))
        # Solo necesitamos TeamNames y Goals; tras Goals hay HighLights/PlayerStats con structs complejos
        if key == "Goals":
            break
    return out


def _read_array_property(s: _Stream) -> list[list[tuple[str, Any]]]:
    """ArrayProperty: UInt32 count, luego count bloques de Properties."""
    count = s.read_u32()
    if count > 100000:
        raise CorruptReplayError(
            "El archivo no parece un replay válido de Rocket League (datos corruptos)."
        )
    arr = []
    for _ in range(count):
        arr.append(_read_properties(s))
    return arr


def parse_header(data: bytes) -> dict[str, Any]:
    """
    Parsea solo el header del replay y devuelve un dict con 'properties'
    en formato lista de (nombre, valor), donde los valores pueden ser
    tipos primitivos o listas de propiedades para ArrayProperty.

    Args:
        data: Contenido completo del archivo .replay.

    Returns:
        Dict con al menos 'properties' (lista de (key, value)) y
        'keyframes' vacío (el parser puro no lee el body; el tiempo se calcula por FPS).
    """
    if len(data) < 12:
        raise CorruptReplayError("Archivo demasiado corto para ser un replay")
    s = _Stream(data)
    header_size = s.read_i32()
    s.advance(4)  # header_crc
    max_header = 50 * 1024 * 1024  # 50 MB
    if header_size < 8 or header_size > max_header or s._pos + header_size > len(data):
        raise CorruptReplayError(
            "El archivo no parece un replay válido de Rocket League. "
            "Comprueba que sea un .replay guardado desde el juego (partida privada o pública)."
        )
    header_data = s.read(header_size)
    s = _Stream(header_data)
    major = s.read_i32()
    minor = s.read_i32()
    if (major, minor) >= (866, 18):
        s.read_i32()  # net_version
    # Game type: string (Int32 length + bytes, como String16)
    length = s.read_i32()
    if length > 0:
        s.advance(min(length, s.remaining()))
    elif length < 0:
        s.advance(min((-length) * 2, s.remaining()))
    # Lista de propiedades
    props_list = _read_properties(s)
    # Convertir a dict por nombre para compatibilidad con get_prop
    props_dict: dict[str, Any] = {}
    for name, value in props_list:
        props_dict[name] = value
    # Formato esperado por el resto del código: "properties" como lista de [nombre, valor]
    properties = [[name, value] for name, value in props_list]
    return {"properties": properties, "keyframes": [], "tick_marks": []}


def extract_team_names_from_header_dict(header_dict: dict) -> tuple[str, str]:
    """Extrae (blue, orange) desde el resultado de parse_header."""
    from rl_replay_analyzer.utils import get_prop, first_string_from_header_prop

    team_names_prop = get_prop(header_dict, "TeamNames")
    if team_names_prop is None:
        raise CorruptReplayError("No se encontró la propiedad 'TeamNames' en el header")
    blue, orange = "Blue", "Orange"
    # En parser puro, ArrayProperty es lista de listas de (key, value)
    if isinstance(team_names_prop, list) and len(team_names_prop) >= 2:
        # Cada elemento es una lista de propiedades; buscamos el primer string
        blue = first_string_from_header_prop(team_names_prop[0]) or blue
        orange = first_string_from_header_prop(team_names_prop[1]) or orange
    return blue, orange


def extract_goals_from_header_dict(
    header_dict: dict, blue_name: str, orange_name: str
) -> list[dict]:
    """Extrae lista de goles desde el header parseado (parser puro)."""
    from rl_replay_analyzer.utils import get_prop, seconds_to_mm_ss

    goals_prop = get_prop(header_dict, "Goals")
    if goals_prop is None or not isinstance(goals_prop, list):
        return []
    goals = []
    for entry in goals_prop:
        if not isinstance(entry, list):
            continue
        frame_val = None
        team_idx = None
        for pair in entry:
            if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                continue
            k, v = pair[0], pair[1]
            if k in ("Frame", "frame"):
                frame_val = v
            elif k in ("Team", "TeamIndex", "team"):
                team_idx = v
        if frame_val is None:
            continue
        try:
            frame = int(frame_val)
        except (TypeError, ValueError):
            continue
        team_name = blue_name if team_idx == 0 else (orange_name if team_idx == 1 else "Unknown")
        time_str = seconds_to_mm_ss(frame / 30.0)  # 30 FPS
        goals.append({"time": time_str, "team": team_name})
    return goals
