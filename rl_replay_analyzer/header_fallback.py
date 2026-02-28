"""
Parser de respaldo del header del replay en Python puro.

Cuando boxcars_py falla (p. ej. StructProperty no soportado), leemos el header
directamente del binario: saltamos propiedades desconocidas y extraemos
TeamNames y Goals para poder dar un resultado útil.
"""

from __future__ import annotations

import struct
from typing import Any


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
            raise ValueError("Fin de datos del header")
        out = self._buf[self._pos : self._pos + n]
        self._pos += n
        return out

    def read_i32(self) -> int:
        val = struct.unpack_from("<i", self._buf, self._pos)[0]
        self._pos += 4
        return val

    def read_u32(self) -> int:
        val = struct.unpack_from("<I", self._buf, self._pos)[0]
        self._pos += 4
        return val

    def read_f32(self) -> float:
        self._pos += 4
        return struct.unpack_from("<f", self._buf, self._pos - 4)[0]

    def advance(self, n: int) -> None:
        self._pos += n


def _read_string8(s: _Stream) -> str:
    """String8: UInt32 length, luego length bytes UTF-8."""
    length = s.read_u32()
    if length == 0:
        return ""
    if length > s.remaining() or length > 50000:
        raise ValueError("Longitud de string inválida")
    raw = s.read(length)
    if raw and raw[-1:] == b"\x00":
        raw = raw[:-1]
    return raw.decode("utf-8", errors="replace")


def _read_string16(s: _Stream) -> str:
    """String16: Int32 length; si >0 bytes, si <0 UTF-16."""
    length = s.read_i32()
    if length == 0:
        return ""
    if length > 0:
        if length > s.remaining() or length > 50000:
            raise ValueError("Longitud string16 inválida")
        raw = s.read(length)
        if raw and raw[-1:] == b"\x00":
            raw = raw[:-1]
        return raw.decode("windows-1252", errors="replace")
    byte_count = (-length) * 2
    if byte_count > s.remaining() or byte_count > 50000:
        raise ValueError("Longitud string16 inválida")
    raw = s.read(byte_count)
    if len(raw) >= 2 and raw[-2:] == b"\x00\x00":
        raw = raw[:-2]
    return raw.decode("utf-16-le", errors="replace")


def _skip_property_value(s: _Stream, prop_type: str) -> None:
    """Avanza el stream sin guardar el valor (para saltar StructProperty, etc.)."""
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
            raise ValueError("Array demasiado grande")
        for _ in range(count):
            _skip_properties(s)
        return
    if prop_type == "StructProperty":
        # Nombre del tipo de struct (String16): Int32 length + bytes
        length = s.read_i32()
        if length > 0 and length < 50000:
            s.advance(length)
        elif length < 0 and length > -50000:
            s.advance((-length) * 2)
        else:
            try:
                _ = _read_string16(s)
            except ValueError:
                pass
        try:
            _skip_properties(s)
        except ValueError:
            pass
        return
    raise ValueError(f"Tipo de propiedad no soportado al saltar: {prop_type!r}")


def _skip_properties(s: _Stream) -> None:
    """Avanza hasta el siguiente 'None' (fin de bloque de propiedades)."""
    while True:
        try:
            key = _read_string8(s)
        except ValueError:
            break
        if key in ("None", "\x00\x00\x00None", ""):
            break
        try:
            prop_type = _read_string8(s)
        except ValueError:
            break
        s.advance(8)  # unknown
        try:
            _skip_property_value(s, prop_type)
        except ValueError:
            break


def _read_property_value(s: _Stream, prop_type: str) -> Any:
    """Lee el valor de una propiedad (solo tipos que nos interesan)."""
    if prop_type == "IntProperty":
        return s.read_i32()
    if prop_type == "FloatProperty":
        return s.read_f32()
    if prop_type in ("StrProperty", "NameProperty"):
        return _read_string16(s)
    if prop_type == "BoolProperty":
        return s.read(1)[0] != 0
    if prop_type == "QWordProperty":
        s.advance(8)
        return None
    if prop_type == "ByteProperty":
        s.advance(1)
        return None
    if prop_type == "ArrayProperty":
        return _read_array_property(s)
    if prop_type == "StructProperty":
        _ = _read_string16(s)
        return _read_properties(s)
    if prop_type == "EnumProperty":
        s.advance(1)
        return None
    raise ValueError(f"Tipo no esperado: {prop_type!r}")


def _read_properties(s: _Stream, stop_at_goals: bool = True) -> list[tuple[str, Any]]:
    """Lee propiedades hasta 'None'. Si stop_at_goals, para tras leer Goals."""
    out: list[tuple[str, Any]] = []
    while True:
        key = _read_string8(s)
        if key in ("None", "\x00\x00\x00None", ""):
            break
        prop_type = _read_string8(s)
        s.advance(8)
        # StructProperty no lo soportamos; saltar para llegar a TeamNames/Goals
        if prop_type == "StructProperty":
            _skip_property_value(s, prop_type)
            continue
        try:
            value = _read_property_value(s, prop_type)
        except ValueError:
            _skip_property_value(s, prop_type)
            continue
        out.append((key, value))
        if stop_at_goals and key == "Goals":
            break
    return out


def _read_array_property(s: _Stream) -> list[list[tuple[str, Any]]]:
    """ArrayProperty: UInt32 count, luego count bloques de Properties."""
    count = s.read_u32()
    if count > 100000:
        raise ValueError("Array demasiado grande")
    return [_read_properties(s, stop_at_goals=False) for _ in range(count)]


def parse_header(data: bytes) -> dict[str, Any]:
    """
    Parsea el header del replay y devuelve un dict con 'properties'
    en formato lista de (nombre, valor). Salta StructProperty y otros
    tipos problemáticos para poder leer TeamNames y Goals.
    """
    if len(data) < 12:
        raise ValueError("Archivo demasiado corto")
    s = _Stream(data)
    header_size = s.read_i32()
    s.advance(4)  # header_crc
    if header_size < 8 or header_size > 50 * 1024 * 1024 or s._pos + header_size > len(data):
        raise ValueError("Tamaño de header inválido")
    header_data = s.read(header_size)
    s = _Stream(header_data)
    major = s.read_i32()
    minor = s.read_i32()
    # En versiones recientes (866+) hay net_version
    if (major, minor) >= (866, 18):
        s.read_i32()  # net_version
    # Game type string (String16)
    length = s.read_i32()
    if length > 0:
        s.advance(min(length, s.remaining()))
    elif length < 0:
        s.advance(min((-length) * 2, s.remaining()))
    props_list = _read_properties(s, stop_at_goals=True)
    properties = [[name, value] for name, value in props_list]
    return {"properties": properties}
