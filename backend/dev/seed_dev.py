"""Carga datos de PRUEBA (sintéticos) en MySQL y HBase, con los mismos IDs en ambos motores.

Solo para desarrollar el backend y la app mientras no estén los datos reales.
Los barrios y comunas son reales; los lugares, usuarios y check-ins son inventados.

Uso (desde backend/):  .venv/Scripts/python -m dev.seed_dev
"""

import random
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import happybase
import sqlalchemy as sa

from app.config import settings
from app.persistencia.hbase import geohash
from app.persistencia.hbase.claves import a_celdas, clave, pad, rev_ts
from app.persistencia.hbase.esquema import crear_tablas
from app.persistencia.mysql.cuentas import hash_password

random.seed(42)

N_LUGARES = 300
N_USUARIOS = 60
N_CHECKINS = 4000

BARRIOS_POR_COMUNA = {
    1: ["Retiro", "San Nicolás", "Puerto Madero", "San Telmo", "Monserrat", "Constitución"],
    2: ["Recoleta"],
    3: ["Balvanera", "San Cristóbal"],
    4: ["La Boca", "Barracas", "Parque Patricios", "Nueva Pompeya"],
    5: ["Almagro", "Boedo"],
    6: ["Caballito"],
    7: ["Flores", "Parque Chacabuco"],
    8: ["Villa Soldati", "Villa Riachuelo", "Villa Lugano"],
    9: ["Liniers", "Mataderos", "Parque Avellaneda"],
    10: ["Villa Real", "Monte Castro", "Versalles", "Floresta", "Vélez Sarsfield", "Villa Luro"],
    11: ["Villa General Mitre", "Villa Devoto", "Villa del Parque", "Villa Santa Rita"],
    12: ["Coghlan", "Saavedra", "Villa Urquiza", "Villa Pueyrredón"],
    13: ["Núñez", "Belgrano", "Colegiales"],
    14: ["Palermo"],
    15: ["Chacarita", "Villa Crespo", "La Paternal", "Villa Ortúzar", "Agronomía", "Parque Chas"],
}
# Centro aproximado de cada comuna (para generar coordenadas verosímiles)
CENTRO_COMUNA = {
    1: (-34.607, -58.375), 2: (-34.588, -58.395), 3: (-34.612, -58.405), 4: (-34.640, -58.385),
    5: (-34.616, -58.420), 6: (-34.618, -58.443), 7: (-34.632, -58.460), 8: (-34.670, -58.465),
    9: (-34.650, -58.505), 10: (-34.628, -58.500), 11: (-34.603, -58.495), 12: (-34.565, -58.490),
    13: (-34.555, -58.455), 14: (-34.580, -58.425), 15: (-34.590, -58.460),
}
TIPOS = ["gastronomia", "cultura", "patrimonio"]
CATEGORIAS = [
    ("Bar", "gastronomia"), ("Café", "gastronomia"), ("Restaurante", "gastronomia"),
    ("Pizzería", "gastronomia"), ("Heladería", "gastronomia"),
    ("Centro cultural", "cultura"), ("Biblioteca", "cultura"), ("Librería", "cultura"),
    ("Teatro", "cultura"), ("Museo", "cultura"),
    ("Monumento", "patrimonio"), ("Mural", "patrimonio"),
]
FUENTES = [
    ("Oferta y Establecimientos gastronómicos", "https://data.buenosaires.gob.ar/dataset/oferta-establecimientos-gastronomicos"),
    ("Espacios culturales", "https://data.buenosaires.gob.ar/dataset/espacios-culturales"),
    ("Monumentos", "https://data.buenosaires.gob.ar/dataset/monumentos"),
    ("Murales", "https://data.buenosaires.gob.ar/dataset/murales"),
]
PALABRAS = ["La Esquina", "El Farol", "Los Amigos", "Del Sur", "La Paloma", "El Tano", "Las Violetas",
            "La Poesía", "El Federal", "Notable", "Del Barrio", "La Academia", "El Puerto", "La Perla",
            "Los Galgos", "El Progreso", "La Biela", "Margot", "El Gato Negro", "La Ideal", "Del Ángel"]
CALLES = ["Corrientes", "Rivadavia", "Santa Fe", "Cabildo", "Defensa", "Perú", "Bolívar", "Scalabrini Ortiz",
          "Directorio", "Córdoba", "Callao", "Juramento", "Triunvirato", "Álvarez Thomas", "Boedo"]
NOMBRES = ["Ana", "Juan", "Sofía", "Mateo", "Valentina", "Lucas", "Camila", "Tomás", "Martina", "Joaquín",
           "Lucía", "Santiago", "Julieta", "Benjamín", "Agustina", "Nicolás", "Florencia", "Facundo"]
APELLIDOS = ["García", "Fernández", "López", "Martínez", "González", "Rodríguez", "Pérez", "Romero",
             "Sosa", "Álvarez", "Torres", "Ruiz", "Ramírez", "Flores", "Acosta", "Benítez"]
COMENTARIOS = ["Muy lindo lugar", "Volvería", "Excelente atención", "Mucha gente", "Un clásico",
               "Ideal para ir con amigos", "Tranqui para leer", "Buenísimo", "Nada especial", None, None, None]


def generar():
    barrios = []  # (id, nombre, comuna)
    for comuna, nombres in BARRIOS_POR_COMUNA.items():
        for n in nombres:
            barrios.append((len(barrios) + 1, n, comuna))
    categorias = [(i + 1, n, TIPOS.index(t) + 1, t) for i, (n, t) in enumerate(CATEGORIAS)]

    lugares = []
    for i in range(1, N_LUGARES + 1):
        id_cat, nom_cat, _, tipo = random.choice(categorias)
        id_bar, _, comuna = random.choice(barrios)
        lat0, lon0 = CENTRO_COMUNA[comuna]
        fuente = {"gastronomia": 1, "cultura": 2}.get(tipo, 3 if nom_cat == "Monumento" else 4)
        lugares.append({
            "id": i, "nombre": f"{nom_cat} {random.choice(PALABRAS)}",
            "direccion": f"{random.choice(CALLES)} {random.randint(100, 5000)}",
            "lat": round(lat0 + random.uniform(-0.01, 0.01), 6),
            "lon": round(lon0 + random.uniform(-0.01, 0.01), 6),
            "id_categoria": id_cat, "id_barrio": id_bar, "id_fuente": fuente, "id_origen": str(1000 + i),
        })

    usuarios = []
    usados = set()
    for i in range(1, N_USUARIOS + 1):
        nombre, apellido = random.choice(NOMBRES), random.choice(APELLIDOS)
        base = f"{nombre}.{apellido}".lower().translate(str.maketrans("áéíóúñ", "aeioun"))
        usuario = base if base not in usados else f"{base}{i}"
        usados.add(usuario)
        usuarios.append({
            "id": i, "nombre_usuario": usuario, "nombre": f"{nombre} {apellido}",
            "email": f"{usuario}@mail.com", "id_barrio": random.choice(barrios)[0],
            "fecha_alta": datetime(2025, 9, 1) + timedelta(days=random.randint(0, 30)),
        })

    # Los check-ins se concentran en algunos lugares "populares" para que el ranking sea interesante.
    pesos = [random.paretovariate(1.5) for _ in lugares]
    hoy = datetime.now().replace(microsecond=0)
    checkins = []
    for i in range(1, N_CHECKINS + 1):
        lugar = random.choices(lugares, weights=pesos)[0]
        fecha = hoy - timedelta(days=random.randint(0, 364), minutes=random.randint(0, 1439))
        checkins.append({
            "id": i, "id_usuario": random.randint(1, N_USUARIOS), "id_lugar": lugar["id"],
            "fecha_hora": fecha, "puntaje": random.choice([None, 3, 4, 4, 5, 5]),
            "comentario": random.choice(COMENTARIOS),
        })
    return barrios, categorias, lugares, usuarios, checkins


def cargar_mysql(barrios, categorias, lugares, usuarios, checkins):
    engine = sa.create_engine(settings.mysql_url)
    schema = (Path(__file__).parent / "schema_mysql_dev.sql").read_text(encoding="utf-8")
    with engine.begin() as c:
        for sentencia in (s.strip() for s in schema.split(";")):
            if sentencia and not all(l.startswith("--") for l in sentencia.splitlines()):
                c.execute(sa.text(sentencia))
        ins = lambda sql, filas: c.execute(sa.text(sql), filas) if filas else None
        ins("INSERT INTO comuna VALUES (:id)", [{"id": i} for i in CENTRO_COMUNA])
        ins("INSERT INTO barrio VALUES (:id, :nombre, :comuna)",
            [{"id": b[0], "nombre": b[1], "comuna": b[2]} for b in barrios])
        ins("INSERT INTO tipo_lugar VALUES (:id, :nombre)", [{"id": i + 1, "nombre": t} for i, t in enumerate(TIPOS)])
        ins("INSERT INTO categoria VALUES (:id, :nombre, :tipo)",
            [{"id": c_[0], "nombre": c_[1], "tipo": c_[2]} for c_ in categorias])
        ins("INSERT INTO fuente (id_fuente, nombre, url) VALUES (:id, :nombre, :url)",
            [{"id": i + 1, "nombre": n, "url": u} for i, (n, u) in enumerate(FUENTES)])
        ins("""INSERT INTO lugar
               (id_lugar, nombre, direccion, latitud, longitud, id_categoria, id_barrio, id_fuente, id_origen)
               VALUES (:id, :nombre, :direccion, :lat, :lon, :id_categoria,
                       :id_barrio, :id_fuente, :id_origen)""", lugares)
        password_demo = hash_password("demo1234")
        usuarios_sql = [
            {**u, "password_hash": password_demo, "rol": "admin" if u["id"] == 1 else "usuario"}
            for u in usuarios
        ]
        ins("""INSERT INTO usuario
               (id_usuario, nombre_usuario, nombre, email, password_hash, rol, id_barrio, fecha_alta)
               VALUES (:id, :nombre_usuario, :nombre, :email, :password_hash, :rol, :id_barrio, :fecha_alta)""",
            usuarios_sql)
        ins("""INSERT INTO checkin
               (id_checkin, id_usuario, id_lugar, fecha_hora, puntaje, comentario)
               VALUES (:id, :id_usuario, :id_lugar, :fecha_hora, :puntaje, :comentario)""", checkins)
    print(f"MySQL: {len(lugares)} lugares, {len(usuarios)} usuarios, {len(checkins)} check-ins")
    print(f"Login demo: {usuarios[0]['nombre_usuario']} / demo1234 (admin); los demas / demo1234")


def cargar_hbase(barrios, categorias, lugares, usuarios, checkins):
    con = happybase.Connection(settings.hbase_host, settings.hbase_port)
    crear_tablas(con, recrear=True)
    t = con.table

    with t("catalogo").batch() as b:
        for id_, nombre, comuna in barrios:
            b.put(clave("barrio", id_), a_celdas({"nombre": nombre, "comuna": comuna}))
        for id_, nombre, _, tipo in categorias:
            b.put(clave("categoria", id_), a_celdas({"nombre": nombre, "tipo": tipo}))

    bar = {b[0]: b for b in barrios}
    cat = {c[0]: c for c in categorias}
    fuente = {i + 1: n for i, (n, _) in enumerate(FUENTES)}
    lug = {l["id"]: l for l in lugares}
    usu = {u["id"]: u for u in usuarios}

    with t("lugares").batch(batch_size=500) as bl, t("lugares_por_barrio").batch(batch_size=500) as bb, \
            t("lugares_por_categoria").batch(batch_size=500) as bc, t("lugares_por_geohash").batch(batch_size=500) as bg:
        for l in lugares:
            _, nom_bar, comuna = bar[l["id_barrio"]]
            _, nom_cat, _, tipo = cat[l["id_categoria"]]
            gh = geohash.codificar(l["lat"], l["lon"], 6)
            bl.put(clave(l["id"]), a_celdas({
                "nombre": l["nombre"], "direccion": l["direccion"], "lat": l["lat"], "lon": l["lon"],
                "geohash": gh, "id_categoria": l["id_categoria"], "categoria": nom_cat, "tipo": tipo,
                "id_barrio": l["id_barrio"], "barrio": nom_bar, "comuna": comuna,
                "fuente": fuente[l["id_fuente"]],
            }))
            bb.put(clave(l["id_barrio"], l["id"]),
                   a_celdas({"nombre": l["nombre"].lower(), "id_categoria": l["id_categoria"]}))
            bc.put(clave(l["id_categoria"], l["id"]),
                   a_celdas({"nombre": l["nombre"].lower(), "id_barrio": l["id_barrio"]}))
            bg.put(f"{gh}#{pad(l['id'])}".encode(), a_celdas({"lat": l["lat"], "lon": l["lon"]}))

    with t("usuarios").batch() as bu, t("usuarios_por_nombre").batch() as bn:
        for u in usuarios:
            _, nom_bar, comuna = bar[u["id_barrio"]]
            bu.put(clave(u["id"]), a_celdas({
                "nombre_usuario": u["nombre_usuario"], "nombre": u["nombre"], "email": u["email"],
                "id_barrio": u["id_barrio"], "barrio": nom_bar, "comuna": comuna, "fecha_alta": u["fecha_alta"],
            }))
            bn.put(u["nombre_usuario"].encode(), a_celdas({"id": u["id"]}))

    por_mes, totales = Counter(), Counter()
    with t("checkins").batch(batch_size=1000) as b1, t("checkins_por_lugar").batch(batch_size=1000) as b2, \
            t("checkins_por_usuario").batch(batch_size=1000) as b3:
        for ch in checkins:
            l = lug[ch["id_lugar"]]
            fila = a_celdas({
                "id_usuario": ch["id_usuario"], "nombre_usuario": usu[ch["id_usuario"]]["nombre_usuario"],
                "id_lugar": ch["id_lugar"], "nombre_lugar": l["nombre"],
                "id_barrio": l["id_barrio"], "barrio": bar[l["id_barrio"]][1],
                "fecha_hora": ch["fecha_hora"], "puntaje": ch["puntaje"], "comentario": ch["comentario"],
            })
            ts = rev_ts(ch["fecha_hora"])
            b1.put(clave(ch["id"]), fila)
            b2.put(clave(ch["id_lugar"], ts, ch["id"]), fila)
            b3.put(clave(ch["id_usuario"], ts, ch["id"]), fila)
            por_mes[(ch["id_lugar"], f"{ch['fecha_hora']:%Y%m}")] += 1
            totales[ch["id_lugar"]] += 1

    # Contadores precalculados (en la app se mantienen con INCREMENT en cada alta/baja).
    stats = t("stats_lugar")
    for (id_lugar, mes), n in por_mes.items():
        stats.counter_set(clave(id_lugar), f"m:{mes}".encode(), n)
    for id_lugar, n in totales.items():
        stats.counter_set(clave(id_lugar), b"t:total", n)

    sec = t("secuencias")
    sec.counter_set(b"lugar", b"c:valor", len(lugares))
    sec.counter_set(b"usuario", b"c:valor", len(usuarios))
    sec.counter_set(b"checkin", b"c:valor", len(checkins))
    con.close()
    print(f"HBase: {len(lugares)} lugares, {len(usuarios)} usuarios, {len(checkins)} check-ins")


if __name__ == "__main__":
    datos = generar()
    cargar_mysql(*datos)
    cargar_hbase(*datos)
