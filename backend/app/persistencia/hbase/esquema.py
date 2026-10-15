"""Tablas de HBase que usa el backend (ver documentacion/DISENO.md, sección 6).

Tabla -> column families. El diseño de row keys está documentado en repos.py.
"""

TABLAS: dict[str, dict[str, dict]] = {
    "catalogo": {"d": {}},
    "lugares": {"d": {}},
    "lugares_por_barrio": {"d": {}},
    "lugares_por_categoria": {"d": {}},
    "lugares_por_geohash": {"d": {}},
    "usuarios": {"d": {}},
    "usuarios_por_nombre": {"d": {}},
    "checkins": {"d": {}},
    "checkins_por_lugar": {"d": {}},
    "checkins_por_usuario": {"d": {}},
    "stats_lugar": {"m": {}, "t": {}},
    "secuencias": {"c": {}},
}


def crear_tablas(conexion, recrear: bool = False) -> None:
    existentes = {t.decode() for t in conexion.tables()}
    for nombre, familias in TABLAS.items():
        if nombre in existentes:
            if not recrear:
                continue
            conexion.delete_table(nombre, disable=True)
        conexion.create_table(nombre, familias)
