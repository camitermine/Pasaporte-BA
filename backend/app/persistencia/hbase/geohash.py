"""Geohash: convierte (lat, lon) en un string donde los puntos cercanos comparten prefijo.

Sirve para buscar "lugares cercanos" en HBase con scans por prefijo de row key.
"""

import math

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def codificar(lat: float, lon: float, precision: int = 6) -> str:
    lat_rango, lon_rango = [-90.0, 90.0], [-180.0, 180.0]
    resultado, bits, bit, par = [], 0, 0, True
    while len(resultado) < precision:
        rango, valor = (lon_rango, lon) if par else (lat_rango, lat)
        medio = (rango[0] + rango[1]) / 2
        if valor >= medio:
            bits = (bits << 1) | 1
            rango[0] = medio
        else:
            bits <<= 1
            rango[1] = medio
        par = not par
        bit += 1
        if bit == 5:
            resultado.append(_BASE32[bits])
            bits, bit = 0, 0
    return "".join(resultado)


def tamanio_celda(precision: int) -> tuple[float, float]:
    """(alto en grados de latitud, ancho en grados de longitud) de una celda."""
    total = 5 * precision
    bits_lon = math.ceil(total / 2)
    bits_lat = total // 2
    return 180 / 2**bits_lat, 360 / 2**bits_lon


def precision_para_radio(radio_m: float) -> int:
    """La celda tiene que ser al menos tan grande como el radio, así alcanza con la celda y sus 8 vecinas."""
    for p in (6, 5, 4):
        dlat, _ = tamanio_celda(p)
        if dlat * 111_320 >= radio_m:
            return p
    return 3


def celdas_alrededor(lat: float, lon: float, precision: int) -> list[str]:
    """La celda que contiene al punto más sus 8 vecinas."""
    dlat, dlon = tamanio_celda(precision)
    celdas = {codificar(lat + i * dlat, lon + j * dlon, precision)
              for i in (-1, 0, 1) for j in (-1, 0, 1)}
    return sorted(celdas)


def distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia haversine en metros."""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
