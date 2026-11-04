"""Compara lecturas equivalentes de actividad en MySQL y HBase.

Este script es una herramienta de evaluación del TP, no una opción de la app:
el usuario nunca elige el motor. Requiere que ambas bases estén levantadas y
que HBase haya sido proyectada desde MySQL con ``database/hbase/cargar_desde_mysql.py``.
Para tener volumen, generar antes actividad con ``dev.generar_actividad``.

Cómo mide:
- Cada motor se instancia una sola vez; el tiempo medido es solo el de la consulta.
- Se descartan unas ejecuciones de calentamiento (cachés y conexiones frías).
- MySQL y HBase se alternan en cada repetición, para que ninguno quede favorecido
  por lo que esté pasando en la máquina en ese momento.
- Por defecto elige casos representativos de los datos: el usuario/lugar/barrio con más
  actividad, uno mediano y uno con poca. Con --usuario, --lugar o --barrio se fuerza un caso.
- Además de comparar tiempos, verifica que ambos motores devuelvan el mismo resultado.
  En el ranking, los lugares empatados en el mismo puesto pueden venir en distinto orden
  (MySQL ordena la puntuación según su collation y Python no), así que dentro de un
  puesto se comparan sin importar el orden.

Uso desde ``backend/``::

    .venv/Scripts/python -m dev.comparar_motores --mes 2026-10 --repeticiones 30 --csv dev/resultados/benchmark.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from pydantic import BaseModel

from app.persistencia.base import Persistencia
from app.persistencia.fabrica import crear_persistencia
from app.persistencia.mysql.repos import _engine

MOTORES = ("mysql", "hbase")


@dataclass
class Caso:
    consulta: str
    caso: str            # mas_activo, mediano, poco_activo o manual
    id: int
    checkins: int        # check-ins que la consulta tiene que considerar
    ejecutar: Callable[[Persistencia], Any]


def serializar(valor: Any) -> Any:
    if isinstance(valor, BaseModel):
        valor = valor.model_dump(mode="json")
    elif isinstance(valor, list):
        valor = [serializar(item) for item in valor]
    elif isinstance(valor, dict):
        valor = {clave: serializar(item) for clave, item in valor.items()}

    # Los cursores son detalles internos y no tienen el mismo formato físico.
    if isinstance(valor, dict) and "siguiente_cursor" in valor:
        valor = {**valor, "siguiente_cursor": None}
    return valor


def normalizar(valor: Any) -> Any:
    """Ordena por id los empates del ranking (mismo puesto) antes de comparar."""
    if isinstance(valor, list) and valor and isinstance(valor[0], dict) and "puesto" in valor[0]:
        return sorted(valor, key=lambda x: (x["puesto"], x["lugar"]["id"]))
    return valor


def percentil(valores: list[float], p: float) -> float:
    orden = sorted(valores)
    return orden[min(len(orden) - 1, round(p * (len(orden) - 1)))]


# ---------------------------------------------------------------- elección de casos

def _escalar(sql: str, **params: Any) -> list[tuple]:
    with _engine.connect() as con:
        return [tuple(f) for f in con.execute(sa.text(sql), params)]


def _representativos(filas: list[tuple]) -> list[tuple[str, int, int]]:
    """De (id, cantidad) ordenado por cantidad desc: el máximo, la mediana y el mínimo."""
    if not filas:
        return []
    elegidos = {"mas_activo": filas[0], "mediano": filas[len(filas) // 2], "poco_activo": filas[-1]}
    vistos, casos = set(), []
    for nombre, (id_, cantidad) in elegidos.items():
        if id_ not in vistos:
            vistos.add(id_)
            casos.append((nombre, id_, cantidad))
    return casos


def elegir_casos(args: argparse.Namespace) -> list[Caso]:
    inicio = datetime(args.anio, args.numero_mes, 1)
    fin = datetime(args.anio + (args.numero_mes == 12), args.numero_mes % 12 + 1, 1)

    if args.usuario:
        usuarios = [("manual", args.usuario, _escalar(
            "SELECT COUNT(*) FROM checkin WHERE id_usuario = :u", u=args.usuario)[0][0])]
    else:
        usuarios = _representativos(_escalar("""SELECT id_usuario, COUNT(*) c FROM checkin
            GROUP BY id_usuario ORDER BY c DESC, id_usuario"""))
    if args.lugar:
        lugares = [("manual", args.lugar, _escalar(
            "SELECT COUNT(*) FROM checkin WHERE id_lugar = :l", l=args.lugar)[0][0])]
    else:
        lugares = _representativos(_escalar("""SELECT id_lugar, COUNT(*) c FROM checkin
            GROUP BY id_lugar ORDER BY c DESC, id_lugar"""))
    consulta_barrio = """SELECT l.id_barrio, COUNT(*) c FROM checkin ch
        JOIN lugar l ON l.id_lugar = ch.id_lugar
        WHERE ch.fecha_hora >= :i AND ch.fecha_hora < :f {extra}
        GROUP BY l.id_barrio ORDER BY c DESC, l.id_barrio"""
    if args.barrio:
        filas = _escalar(consulta_barrio.format(extra="AND l.id_barrio = :b"), i=inicio, f=fin, b=args.barrio)
        barrios = [("manual", args.barrio, filas[0][1] if filas else 0)]
    else:
        barrios = _representativos(_escalar(consulta_barrio.format(extra=""), i=inicio, f=fin))

    if not usuarios:
        raise SystemExit("No hay check-ins: generá actividad con  python -m dev.generar_actividad")

    casos: list[Caso] = []
    for nombre, id_, n in usuarios:
        casos.append(Caso("historial por usuario", nombre, id_, n,
                          lambda p, i=id_: p.checkins.de_usuario(i, args.limite, None)))
    for nombre, id_, n in lugares:
        casos.append(Caso("actividad por lugar", nombre, id_, n,
                          lambda p, i=id_: p.checkins.de_lugar(i, args.limite, None)))
    for nombre, id_, n in barrios:
        casos.append(Caso("ranking mensual", nombre, id_, n,
                          lambda p, i=id_: p.consultas.ranking_barrio(i, args.anio, args.numero_mes, 10)))
    for nombre, id_, n in usuarios:
        casos.append(Caso("pasaporte del usuario", nombre, id_, n,
                          lambda p, i=id_: p.consultas.pasaporte(i)))
    return casos


# ---------------------------------------------------------------- medición

def medir(caso: Caso, motores: dict[str, Persistencia], repeticiones: int,
          calentamiento: int) -> tuple[dict[str, list[float]], dict[str, Any]]:
    tiempos: dict[str, list[float]] = {m: [] for m in motores}
    valores: dict[str, Any] = {}
    for n in range(calentamiento + repeticiones):
        orden = MOTORES if n % 2 == 0 else MOTORES[::-1]
        for motor in orden:
            inicio = time.perf_counter()
            valor = caso.ejecutar(motores[motor])
            transcurrido = (time.perf_counter() - inicio) * 1000
            if n >= calentamiento:
                tiempos[motor].append(transcurrido)
            valores[motor] = valor
    return tiempos, {m: normalizar(serializar(v)) for m, v in valores.items()}


def total_checkins() -> int:
    return _escalar("SELECT COUNT(*) FROM checkin")[0][0]


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--usuario", type=int, help="forzar un usuario en vez de elegirlos automáticamente")
    parser.add_argument("--lugar", type=int, help="forzar un lugar")
    parser.add_argument("--barrio", type=int, help="forzar un barrio")
    parser.add_argument("--mes", default="2026-10", help="mes del ranking, formato YYYY-MM")
    parser.add_argument("--limite", type=int, default=50, help="tamaño de página de los historiales")
    parser.add_argument("--repeticiones", type=int, default=30)
    parser.add_argument("--calentamiento", type=int, default=3)
    parser.add_argument("--csv", type=Path, help="agrega los resultados a este CSV")
    args = parser.parse_args()
    if args.repeticiones < 1 or args.limite < 1 or args.calentamiento < 0:
        parser.error("repeticiones y limite deben ser positivos; calentamiento, no negativo")
    try:
        args.anio, args.numero_mes = (int(parte) for parte in args.mes.split("-"))
        if not 1 <= args.numero_mes <= 12:
            raise ValueError
    except ValueError:
        parser.error("mes debe tener formato YYYY-MM")
    return args


def main() -> int:
    args = argumentos()
    volumen = total_checkins()
    casos = elegir_casos(args)
    motores = {m: crear_persistencia(m) for m in MOTORES}
    print(f"Volumen: {volumen:,} check-ins | {args.repeticiones} repeticiones "
          f"(+{args.calentamiento} de calentamiento) | mes {args.mes}\n")
    print(f"    {'consulta':<22} {'caso':<12} {'id':>6} {'check-ins':>9}   "
          f"{'MySQL med / p95 (ms)':>21}   {'HBase med / p95 (ms)':>21}")

    filas_csv, equivalentes = [], 0
    for caso in casos:
        tiempos, valores = medir(caso, motores, args.repeticiones, args.calentamiento)
        iguales = valores["mysql"] == valores["hbase"]
        equivalentes += iguales
        resumen = {m: (statistics.median(t), percentil(t, 0.95), min(t)) for m, t in tiempos.items()}
        print(f"{'OK ' if iguales else 'DIF'} {caso.consulta:<22} {caso.caso:<12} {caso.id:>6} {caso.checkins:>9,}   "
              f"{resumen['mysql'][0]:>9.2f} / {resumen['mysql'][1]:>9.2f}   "
              f"{resumen['hbase'][0]:>9.2f} / {resumen['hbase'][1]:>9.2f}")
        if not iguales:
            print("    MySQL:", json.dumps(valores["mysql"], ensure_ascii=False)[:500])
            print("    HBase:", json.dumps(valores["hbase"], ensure_ascii=False)[:500])
        for motor, (mediana, p95, minimo) in resumen.items():
            filas_csv.append({
                "fecha": datetime.now().isoformat(timespec="seconds"), "volumen_checkins": volumen,
                "consulta": caso.consulta, "caso": caso.caso, "id": caso.id,
                "checkins_involucrados": caso.checkins, "motor": motor,
                "mediana_ms": round(mediana, 3), "p95_ms": round(p95, 3), "min_ms": round(minimo, 3),
                "repeticiones": args.repeticiones, "equivalentes": iguales,
            })

    print(f"\n{equivalentes}/{len(casos)} resultados equivalentes")
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        nuevo = not args.csv.exists()
        with args.csv.open("a", newline="", encoding="utf-8") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=list(filas_csv[0]))
            if nuevo:
                escritor.writeheader()
            escritor.writerows(filas_csv)
        print(f"Resultados agregados a {args.csv}")
    return 0 if equivalentes == len(casos) else 1


if __name__ == "__main__":
    raise SystemExit(main())
