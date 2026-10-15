"""Construcción de row keys y (de)serialización de celdas para HBase."""

import struct
from datetime import datetime
from typing import Any

MAX_LONG = 2**63 - 1
SEP = "#"


def pad(n: int) -> str:
    """IDs con ceros a la izquierda: el orden lexicográfico coincide con el numérico."""
    return f"{n:010d}"


def rev_ts(dt: datetime) -> str:
    """Timestamp invertido: los scans devuelven primero lo más reciente."""
    ms = int(dt.timestamp() * 1000)
    return f"{MAX_LONG - ms:019d}"


def clave(*partes: str | int) -> bytes:
    return SEP.join(pad(p) if isinstance(p, int) else p for p in partes).encode()


def prefijo(*partes: str | int) -> bytes:
    return clave(*partes) + SEP.encode()


def fin_de_prefijo(p: bytes) -> bytes:
    """Primer row key que ya no empieza con el prefijo (para usar como row_stop)."""
    return p[:-1] + bytes([p[-1] + 1])


def a_celdas(datos: dict[str, Any], familia: str = "d") -> dict[bytes, bytes]:
    return {f"{familia}:{k}".encode(): _a_bytes(v) for k, v in datos.items() if v is not None}


def de_celdas(fila: dict[bytes, bytes]) -> dict[str, str]:
    return {k.split(b":", 1)[1].decode(): v.decode("utf-8") for k, v in fila.items()}


def leer_contador(valor: bytes | None) -> int:
    """Los contadores de HBase son long de 8 bytes big-endian."""
    return struct.unpack(">q", valor)[0] if valor else 0


def _a_bytes(v: Any) -> bytes:
    if isinstance(v, datetime):
        v = v.isoformat(sep=" ")
    return str(v).encode("utf-8")
