"""Pruebas de regresión de las reglas de normalización del dataset."""

from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path


ETL_DIR = Path(__file__).resolve().parent
RAIZ = ETL_DIR.parents[1]
sys.path.insert(0, str(ETL_DIR))

import generar_datos_mysql as etl  # noqa: E402


class NormalizacionTest(unittest.TestCase):
    def test_barrios_oficiales(self):
        self.assertEqual(etl.nombre_barrio("AGRONOMIA"), "Agronomía")
        self.assertEqual(etl.nombre_barrio("BOCA"), "La Boca")
        self.assertEqual(etl.nombre_barrio("CONSTITUCION"), "Constitución")

    def test_repara_mojibake_y_preserva_siglas(self):
        self.assertEqual(etl.limpiar_texto("DOÃ‘A FLOR"), "DOÑA FLOR")
        self.assertEqual(etl.formato_titulo("BIBLIOTECA - UBA"), "Biblioteca - UBA")
        self.assertEqual(etl.formato_titulo(etl.limpiar_texto("PIO IX")), "Pío IX")

    def test_preserva_preguntas_intencionales(self):
        self.assertEqual(etl.limpiar_texto("COMO? EL 12"), "COMO? EL 12")
        self.assertEqual(etl.limpiar_texto("PIZZA QUE?"), "PIZZA QUE?")

    def test_normalizacion_de_calles(self):
        ruta = RAIZ / "database" / "datasets" / "tablas_3fn" / "lugares.csv"
        with ruta.open(encoding="utf-8-sig", newline="") as archivo:
            lugares = list(csv.DictReader(archivo))
        calles_origen = {
            etl.limpiar_texto(fila[columna])
            for fila in lugares
            for columna in etl.COLUMNAS_DE_CALLE
        } - {None}
        calles = etl.normalizar_calles(lugares)
        self.assertEqual(len(calles_origen), 1_249)
        self.assertEqual(len(set(calles.values())), 1_009)
        self.assertEqual(calles[etl.limpiar_texto("SALGUERO, JERONIMO")], "Jerónimo Salguero")
        self.assertEqual(calles[etl.limpiar_texto("9 DE JULIO AV.")], "Av. 9 de Julio")

    def test_salida_sin_mojibake_y_solo_dos_preguntas(self):
        salida = (RAIZ / "database" / "mysql" / "datos_iniciales.sql").read_text(encoding="utf-8")
        for marcador in ("Ã", "Â", "â", "�"):
            self.assertNotIn(marcador, salida)
        self.assertEqual(salida.count("?"), 2)
        self.assertIn("Como? El 12", salida)
        self.assertIn("Pizza Que?", salida)


if __name__ == "__main__":
    unittest.main()
