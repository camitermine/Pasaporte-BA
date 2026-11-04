"""Genera actividad simulada (usuarios y check-ins) sobre los lugares REALES de MySQL.

Sirve para medir MySQL vs HBase con un volumen representativo. Solo escribe en MySQL;
después hay que reconstruir HBase con ``database/hbase/cargar_desde_mysql.py``.

- Los usuarios simulados se llaman ``sim_00001``, ``sim_00002``, ... y no pueden iniciar
  sesión con una contraseña conocida. Al regenerar se borran primero, junto con sus
  check-ins; los usuarios reales (``admin``, ``visitante``, etc.) no se tocan.
- La distribución imita uso real: pocos lugares muy populares y muchos poco visitados
  (Zipf), pocos usuarios muy activos (lognormal) y preferencia por el barrio propio.
- Con la misma semilla se obtienen exactamente los mismos datos.

Uso desde ``backend/``::

    .venv/Scripts/python -m dev.generar_actividad --checkins 100000
    .venv/Scripts/python -m dev.generar_actividad --borrar      # solo elimina lo simulado
"""

from __future__ import annotations

import argparse
import itertools
import random
import secrets
import time
from collections import defaultdict
from datetime import datetime

import sqlalchemy as sa

from app.config import settings
from app.persistencia.mysql.cuentas import hash_password

PREFIJO = "sim_"
LOTE = 10_000
COMENTARIOS = [
    "Muy lindo lugar", "Volvería", "Excelente atención", "Mucha gente", "Recomendado",
    "Tranquilo", "Imperdible", "Bastante bien", "Precios razonables", "Para ir con amigos",
]
# Más actividad por la tarde y la noche (horas 9 a 23).
PESOS_HORA = [1, 2, 3, 4, 4, 4, 3, 3, 4, 5, 6, 6, 5, 4, 2]


def mes(texto: str) -> datetime:
    return datetime.strptime(texto, "%Y-%m")


def siguiente_mes(d: datetime) -> datetime:
    return datetime(d.year + (d.month == 12), d.month % 12 + 1, 1)


def patron_simulados() -> dict[str, str]:
    return {"p": PREFIJO.replace("_", r"\_") + "%"}  # '_' es comodín en LIKE


def borrar_simulados(con: sa.Connection) -> tuple[int, int]:
    # Los check-ins tienen ON DELETE RESTRICT; favoritos y sesiones se borran en cascada.
    checkins = con.execute(sa.text("""DELETE ch FROM checkin ch
        JOIN usuario u ON u.id_usuario = ch.id_usuario
        WHERE u.nombre_usuario LIKE :p"""), patron_simulados()).rowcount
    usuarios = con.execute(sa.text("DELETE FROM usuario WHERE nombre_usuario LIKE :p"),
                           patron_simulados()).rowcount
    # MySQL lleva el contador al máximo id existente + 1: así los ids se repiten entre corridas.
    for tabla in ("checkin", "usuario"):
        con.execute(sa.text(f"ALTER TABLE {tabla} AUTO_INCREMENT = 1"))
    return usuarios, checkins


def acumulados(pesos: list[float]) -> list[float]:
    return list(itertools.accumulate(pesos))


def generar(con: sa.Connection, args: argparse.Namespace) -> None:
    rnd = random.Random(args.semilla)

    lugares = [tuple(f) for f in con.execute(sa.text(
        "SELECT id_lugar, id_barrio FROM lugar WHERE activo = TRUE AND id_barrio IS NOT NULL ORDER BY id_lugar"))]
    barrios = [f[0] for f in con.execute(sa.text("SELECT id_barrio FROM barrio ORDER BY id_barrio"))]
    if not lugares:
        raise SystemExit("No hay lugares con barrio: cargá primero datos_iniciales.sql")

    # Popularidad Zipf: se baraja el orden para que no dependa del id.
    rnd.shuffle(lugares)
    peso_lugar = {id_l: 1 / (rango + 1) ** args.zipf for rango, (id_l, _) in enumerate(lugares)}
    global_ids = [id_l for id_l, _ in lugares]
    global_acum = acumulados([peso_lugar[i] for i in global_ids])
    por_barrio: dict[int, list[int]] = defaultdict(list)
    for id_l, id_b in lugares:
        por_barrio[id_b].append(id_l)
    barrio_acum = {b: acumulados([peso_lugar[i] for i in ids]) for b, ids in por_barrio.items()}

    # Usuarios: barrio propio al azar y actividad con cola larga (Pareto).
    clave_comun = hash_password(secrets.token_urlsafe(24))  # nadie conoce esta contraseña
    usuarios = []
    for n in range(1, args.usuarios + 1):
        usuarios.append({
            "nombre_usuario": f"{PREFIJO}{n:05d}", "nombre": f"Usuario simulado {n}",
            "email": f"{PREFIJO}{n:05d}@simulado.local", "password_hash": clave_comun,
            "id_barrio": rnd.choice(barrios), "fecha_alta": mes(args.desde),
        })
    con.execute(sa.text("""INSERT INTO usuario
        (nombre_usuario, nombre, email, password_hash, rol, id_barrio, fecha_alta)
        VALUES (:nombre_usuario, :nombre, :email, :password_hash, 'usuario', :id_barrio, :fecha_alta)"""),
        usuarios)
    filas = con.execute(sa.text(
        "SELECT id_usuario, id_barrio FROM usuario WHERE nombre_usuario LIKE :p ORDER BY id_usuario"),
        patron_simulados()).all()
    ids_usuario = [f[0] for f in filas]
    barrio_usuario = {f[0]: f[1] for f in filas}
    # Lognormal: algunos usuarios hacen decenas de veces más check-ins que la mediana, pero
    # ninguno acapara la actividad (con Pareto, uno solo llegaba a un tercio del total).
    usuario_acum = acumulados([rnd.lognormvariate(0, 1) for _ in ids_usuario])

    inicio = mes(args.desde)
    fin = siguiente_mes(mes(args.hasta))
    rango_dias = (fin - inicio).days
    horas_acum = acumulados(PESOS_HORA)

    # Cursor de pymysql: su executemany arma un único INSERT de varias filas por lote, pero solo
    # si VALUES contiene exclusivamente placeholders (un literal lo hace insertar fila por fila).
    sql = ("INSERT INTO checkin (id_usuario, id_lugar, fecha_hora, puntaje, comentario, verificado) "
           "VALUES (%s, %s, %s, %s, %s, %s)")
    cursor = con.connection.cursor()
    t0, lote = time.perf_counter(), []
    for n in range(1, args.checkins + 1):
        u = rnd.choices(ids_usuario, cum_weights=usuario_acum)[0]
        propio = barrio_usuario[u]
        if propio in por_barrio and rnd.random() < args.localidad:
            l = rnd.choices(por_barrio[propio], cum_weights=barrio_acum[propio])[0]
        else:
            l = rnd.choices(global_ids, cum_weights=global_acum)[0]
        dia = inicio.toordinal() + rnd.randrange(rango_dias)
        hora = 9 + rnd.choices(range(len(PESOS_HORA)), cum_weights=horas_acum)[0]
        fecha = datetime.fromordinal(dia).replace(hour=hora, minute=rnd.randrange(60), second=rnd.randrange(60))
        puntaje = rnd.choices([None, 1, 2, 3, 4, 5], weights=[30, 3, 5, 15, 27, 20])[0]
        comentario = rnd.choice(COMENTARIOS) if rnd.random() < 0.15 else None
        lote.append((u, l, fecha, puntaje, comentario, False))
        if len(lote) == LOTE or n == args.checkins:
            cursor.executemany(sql, lote)
            con.connection.commit()
            lote = []
            print(f"\r  {n:>10,} / {args.checkins:,} check-ins ({time.perf_counter() - t0:5.1f} s)", end="", flush=True)
    print()


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkins", type=int, default=100_000)
    parser.add_argument("--usuarios", type=int, default=None,
                        help="por defecto, 1 usuario cada 50 check-ins (mínimo 100)")
    parser.add_argument("--desde", default="2026-05", help="primer mes, YYYY-MM")
    parser.add_argument("--hasta", default="2026-10", help="último mes incluido, YYYY-MM")
    parser.add_argument("--zipf", type=float, default=1.0, help="exponente de popularidad de lugares")
    parser.add_argument("--localidad", type=float, default=0.5,
                        help="probabilidad de visitar un lugar del barrio propio")
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--borrar", action="store_true", help="solo elimina los datos simulados")
    args = parser.parse_args()
    if args.usuarios is None:
        args.usuarios = max(100, args.checkins // 50)
    if args.checkins < 1 or args.usuarios < 1 or args.usuarios > 99_999:
        parser.error("checkins debe ser positivo y usuarios entre 1 y 99.999")
    try:
        if mes(args.desde) > mes(args.hasta):
            parser.error("--desde debe ser anterior o igual a --hasta")
    except ValueError:
        parser.error("los meses deben tener formato YYYY-MM")
    return args


def main() -> None:
    args = argumentos()
    engine = sa.create_engine(settings.mysql_url)
    with engine.connect() as con:
        usuarios, checkins = borrar_simulados(con)
        con.commit()
        print(f"Eliminados: {usuarios:,} usuarios simulados y {checkins:,} check-ins")
        if args.borrar:
            return
        print(f"Generando {args.usuarios:,} usuarios y {args.checkins:,} check-ins "
              f"({args.desde} a {args.hasta}, semilla {args.semilla})")
        generar(con, args)
    print("Listo. Reconstruí HBase con: .venv/Scripts/python ../database/hbase/cargar_desde_mysql.py")


if __name__ == "__main__":
    main()
