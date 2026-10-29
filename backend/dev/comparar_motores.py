"""Compara lecturas equivalentes de actividad en MySQL y HBase.

Este script es una herramienta de evaluación del TP, no una opción de la app:
el usuario nunca elige el motor. Requiere que ambas bases estén levantadas y
que HBase haya sido proyectada desde MySQL con ``database/hbase/cargar_desde_mysql.py``.

Uso desde ``backend/``::

    .venv/Scripts/python -m dev.comparar_motores --usuario 1 --lugar 1 \
        --barrio 1 --mes 2026-10 --repeticiones 10
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.persistencia.fabrica import crear_persistencia


@dataclass
class Resultado:
    valor: Any
    tiempos_ms: list[float]


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


def medir(fabrica: Callable[[], Any], repeticiones: int) -> Resultado:
    tiempos: list[float] = []
    valor = None
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        valor = fabrica()
        tiempos.append((time.perf_counter() - inicio) * 1000)
    return Resultado(serializar(valor), tiempos)


def comparar(nombre: str, consulta: Callable[[Any], Any], repeticiones: int) -> bool:
    resultados: dict[str, Resultado] = {}
    for motor in ("mysql", "hbase"):
        resultados[motor] = medir(
            lambda motor=motor: consulta(crear_persistencia(motor)), repeticiones
        )

    mysql, hbase = resultados["mysql"], resultados["hbase"]
    iguales = mysql.valor == hbase.valor
    print(
        f"{'OK ' if iguales else 'DIF'} {nombre:<30} "
        f"MySQL mediana={statistics.median(mysql.tiempos_ms):8.2f} ms | "
        f"HBase mediana={statistics.median(hbase.tiempos_ms):8.2f} ms"
    )
    if not iguales:
        print("    MySQL:", json.dumps(mysql.valor, ensure_ascii=False)[:500])
        print("    HBase:", json.dumps(hbase.valor, ensure_ascii=False)[:500])
    return iguales


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usuario", type=int, default=1)
    parser.add_argument("--lugar", type=int, default=1)
    parser.add_argument("--barrio", type=int, default=1)
    parser.add_argument("--mes", default="2026-10", help="Mes con formato YYYY-MM")
    parser.add_argument("--limite", type=int, default=50)
    parser.add_argument("--repeticiones", type=int, default=10)
    args = parser.parse_args()
    if args.repeticiones < 1 or args.limite < 1:
        parser.error("repeticiones y limite deben ser positivos")
    try:
        args.anio, args.numero_mes = (int(parte) for parte in args.mes.split("-"))
        if not 1 <= args.numero_mes <= 12:
            raise ValueError
    except ValueError:
        parser.error("mes debe tener formato YYYY-MM")
    return args


def main() -> int:
    args = argumentos()
    pruebas = [
        comparar(
            "historial por usuario",
            lambda p: p.checkins.de_usuario(args.usuario, args.limite, None),
            args.repeticiones,
        ),
        comparar(
            "actividad por lugar",
            lambda p: p.checkins.de_lugar(args.lugar, args.limite, None),
            args.repeticiones,
        ),
        comparar(
            "ranking mensual",
            lambda p: p.consultas.ranking_barrio(
                args.barrio, args.anio, args.numero_mes, 10
            ),
            args.repeticiones,
        ),
        comparar(
            "pasaporte del usuario",
            lambda p: p.consultas.pasaporte(args.usuario),
            args.repeticiones,
        ),
    ]
    print(f"\n{sum(pruebas)}/{len(pruebas)} resultados equivalentes")
    return 0 if all(pruebas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
