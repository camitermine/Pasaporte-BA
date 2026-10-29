"""Reconstruye las proyecciones de HBase a partir de la fuente canonica MySQL.

Ejecutar desde ``backend/`` luego de cargar el modelo y los datos iniciales:
    python ../database/hbase/cargar_desde_mysql.py
"""

from collections import Counter
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))

import happybase
import sqlalchemy as sa

from app.config import settings
from app.persistencia.hbase import geohash
from app.persistencia.hbase.claves import a_celdas, clave, pad, rev_ts
from app.persistencia.hbase.esquema import crear_tablas


def filas(con, consulta: str) -> list[dict]:
    return [dict(f._mapping) for f in con.execute(sa.text(consulta))]


def cargar() -> None:
    engine = sa.create_engine(settings.mysql_url)
    with engine.connect() as sql:
        barrios = filas(sql, "SELECT id_barrio, nombre, id_comuna FROM barrio")
        categorias = filas(sql, """SELECT c.id_categoria, c.nombre, t.nombre AS tipo
            FROM categoria c JOIN tipo_lugar t ON t.id_tipo=c.id_tipo""")
        lugares = filas(sql, """SELECT l.*, b.nombre AS barrio, b.id_comuna,
                   c.nombre AS categoria, t.nombre AS tipo, f.nombre AS fuente
            FROM lugar l JOIN barrio b ON b.id_barrio=l.id_barrio
            JOIN categoria c ON c.id_categoria=l.id_categoria
            JOIN tipo_lugar t ON t.id_tipo=c.id_tipo
            LEFT JOIN fuente f ON f.id_fuente=l.id_fuente WHERE l.activo=TRUE""")
        usuarios = filas(sql, """SELECT u.*, b.nombre AS barrio, b.id_comuna
            FROM usuario u LEFT JOIN barrio b ON b.id_barrio=u.id_barrio WHERE u.activo=TRUE""")
        checkins = filas(sql, """SELECT ch.*, u.nombre_usuario, l.nombre AS nombre_lugar,
                   l.id_barrio, b.nombre AS barrio
            FROM checkin ch JOIN usuario u ON u.id_usuario=ch.id_usuario
            JOIN lugar l ON l.id_lugar=ch.id_lugar
            JOIN barrio b ON b.id_barrio=l.id_barrio""")

    hbase = happybase.Connection(settings.hbase_host, settings.hbase_port)
    crear_tablas(hbase, recrear=True)
    tabla = hbase.table

    with tabla("catalogo").batch(batch_size=500) as batch:
        for b in barrios:
            batch.put(clave("barrio", b["id_barrio"]), a_celdas({"nombre": b["nombre"], "comuna": b["id_comuna"]}))
        for c in categorias:
            batch.put(clave("categoria", c["id_categoria"]), a_celdas({"nombre": c["nombre"], "tipo": c["tipo"]}))

    with tabla("lugares").batch(batch_size=500) as principal, \
            tabla("lugares_por_barrio").batch(batch_size=500) as por_barrio, \
            tabla("lugares_por_categoria").batch(batch_size=500) as por_categoria, \
            tabla("lugares_por_geohash").batch(batch_size=500) as por_geohash:
        for l in lugares:
            gh = geohash.codificar(float(l["latitud"]), float(l["longitud"]), 6) \
                if l["latitud"] is not None and l["longitud"] is not None else None
            principal.put(clave(l["id_lugar"]), a_celdas({
                "nombre": l["nombre"], "direccion": l["direccion"], "lat": l["latitud"],
                "lon": l["longitud"], "geohash": gh, "id_categoria": l["id_categoria"],
                "categoria": l["categoria"], "tipo": l["tipo"], "id_barrio": l["id_barrio"],
                "barrio": l["barrio"], "comuna": l["id_comuna"], "fuente": l["fuente"],
            }))
            por_barrio.put(clave(l["id_barrio"], l["id_lugar"]),
                           a_celdas({"nombre": l["nombre"].lower(), "id_categoria": l["id_categoria"]}))
            por_categoria.put(clave(l["id_categoria"], l["id_lugar"]),
                              a_celdas({"nombre": l["nombre"].lower(), "id_barrio": l["id_barrio"]}))
            if gh:
                por_geohash.put(f"{gh}#{pad(l['id_lugar'])}".encode(),
                                a_celdas({"lat": l["latitud"], "lon": l["longitud"]}))

    with tabla("usuarios").batch() as principal, tabla("usuarios_por_nombre").batch() as por_nombre:
        for u in usuarios:
            principal.put(clave(u["id_usuario"]), a_celdas({
                "nombre_usuario": u["nombre_usuario"], "nombre": u["nombre"], "email": u["email"],
                "id_barrio": u["id_barrio"], "barrio": u["barrio"], "comuna": u["id_comuna"],
                "fecha_alta": u["fecha_alta"],
            }))
            por_nombre.put(u["nombre_usuario"].encode(), a_celdas({"id": u["id_usuario"]}))

    por_mes, totales = Counter(), Counter()
    with tabla("checkins").batch(batch_size=1000) as principal, \
            tabla("checkins_por_lugar").batch(batch_size=1000) as por_lugar, \
            tabla("checkins_por_usuario").batch(batch_size=1000) as por_usuario:
        for ch in checkins:
            dato = a_celdas({
                "id_usuario": ch["id_usuario"], "nombre_usuario": ch["nombre_usuario"],
                "id_lugar": ch["id_lugar"], "nombre_lugar": ch["nombre_lugar"],
                "id_barrio": ch["id_barrio"], "barrio": ch["barrio"],
                "fecha_hora": ch["fecha_hora"], "puntaje": ch["puntaje"],
                "comentario": ch["comentario"], "verificado": bool(ch["verificado"]),
            })
            ts = rev_ts(ch["fecha_hora"])
            principal.put(clave(ch["id_checkin"]), dato)
            por_lugar.put(clave(ch["id_lugar"], ts, ch["id_checkin"]), dato)
            por_usuario.put(clave(ch["id_usuario"], ts, ch["id_checkin"]), dato)
            por_mes[(ch["id_lugar"], f"{ch['fecha_hora']:%Y%m}")] += 1
            totales[ch["id_lugar"]] += 1

    stats = tabla("stats_lugar")
    for (id_lugar, mes), cantidad in por_mes.items():
        stats.counter_set(clave(id_lugar), f"m:{mes}".encode(), cantidad)
    for id_lugar, cantidad in totales.items():
        stats.counter_set(clave(id_lugar), b"t:total", cantidad)
    secuencias = tabla("secuencias")
    secuencias.counter_set(b"lugar", b"c:valor", max((x["id_lugar"] for x in lugares), default=0))
    secuencias.counter_set(b"usuario", b"c:valor", max((x["id_usuario"] for x in usuarios), default=0))
    secuencias.counter_set(b"checkin", b"c:valor", max((x["id_checkin"] for x in checkins), default=0))
    hbase.close()
    print(f"HBase cargado: {len(lugares)} lugares, {len(usuarios)} usuarios, {len(checkins)} check-ins")


if __name__ == "__main__":
    cargar()
