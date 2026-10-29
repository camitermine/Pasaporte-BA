"""Convierte los CSV integrados en una carga limpia y normalizada para MySQL.

Uso desde la raiz del repositorio:
    python database/etl/generar_datos_mysql.py

No modifica los CSV originales. Los registros sin nombre se omiten; los barrios
o coordenadas faltantes permanecen NULL y se informan al terminar.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import re
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ORIGEN = RAIZ / "database" / "datasets" / "tablas_3fn"
SALIDA = RAIZ / "database" / "mysql" / "datos_iniciales.sql"
MODELO = RAIZ / "database" / "mysql" / "modelo_relacional.sql"

TIPOS_APP = {
    "1": (1, "cultura"),
    "2": (2, "patrimonio"),
    "3": (3, "arte urbano"),
    "4": (4, "gastronomía"),
}


def leer(nombre: str) -> list[dict[str, str]]:
    with (ORIGEN / nombre).open(encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo))


def puntaje_codificacion(texto: str) -> int:
    marcadores = "ÃÂâðï"
    return sum(texto.count(x) for x in marcadores) + sum(0x80 <= ord(c) <= 0x9F for c in texto)


def limpiar_texto(valor: str | None) -> str | None:
    if valor is None:
        return None
    texto = valor.strip()
    if not texto:
        return None
    # Algunos orígenes fueron decodificados como latin-1 una o dos veces.
    for _ in range(2):
        try:
            candidato = texto.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if puntaje_codificacion(candidato) < puntaje_codificacion(texto):
            texto = candidato
        else:
            break
    return re.sub(r"\s+", " ", texto).strip()


def clave_texto(valor: str) -> str:
    limpio = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+", "", limpio)


def numero(valor: str | None) -> float | None:
    if not valor or not valor.strip():
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def sql(valor) -> str:
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    if isinstance(valor, (int, float)):
        return str(valor)
    return "'" + str(valor).replace("\\", "\\\\").replace("'", "''") + "'"


def hash_demo(usuario: str, password: str) -> str:
    iteraciones = 390_000
    # Credenciales exclusivamente de demostración; el backend usa salts aleatorios
    # para todas las cuentas creadas por un administrador.
    salt = hashlib.sha256(f"pasaporte-ba-demo:{usuario}".encode()).digest()[:16]
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iteraciones)
    return "pbkdf2_sha256${}${}${}".format(
        iteraciones,
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode(),
    )


def direccion(fila: dict[str, str]) -> str | None:
    calle = limpiar_texto(fila["calle"])
    altura = limpiar_texto(fila["altura"])
    interseccion = limpiar_texto(fila["calle_interseccion"])
    if calle and altura:
        return f"{calle} {altura}"
    if calle and interseccion:
        return f"{calle} y {interseccion}"
    return calle


def generar() -> dict[str, int]:
    MODELO.write_text(
        (RAIZ / "backend" / "dev" / "schema_mysql_dev.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    barrios_raw = leer("barrios.csv")
    fuentes = leer("fuentes.csv")
    tipos = {f["tipo_id"]: limpiar_texto(f["tipo"]) or "Sin clasificar" for f in leer("tipos.csv")}
    lugares_raw = leer("lugares.csv")

    barrios: list[tuple[int, str, int]] = []
    barrio_por_clave: dict[str, int] = {}
    mapa_barrio: dict[str, int] = {}
    for fila in barrios_raw:
        nombre = limpiar_texto(fila["barrio"]) or ""
        clave = clave_texto(nombre)
        # La fuente trae dos codificaciones de Núñez. Ambas se consolidan.
        if clave == "NUNEZ":
            nombre = "NÚÑEZ"
        if clave not in barrio_por_clave:
            nuevo_id = len(barrios) + 1
            barrio_por_clave[clave] = nuevo_id
            barrios.append((nuevo_id, nombre, int(fila["comuna"])))
        mapa_barrio[fila["barrio_id"]] = barrio_por_clave[clave]

    categorias_clave = sorted({
        (f["fuente_id"], f["tipo_id"] or "") for f in lugares_raw
    }, key=lambda x: (int(x[0]), int(x[1]) if x[1].isdigit() else 9999))
    categorias: dict[tuple[str, str], tuple[int, str, int]] = {}
    for clave in categorias_clave:
        fuente_id, tipo_id = clave
        nombre = tipos.get(tipo_id, "Sin clasificar")
        categorias[clave] = (len(categorias) + 1, nombre, TIPOS_APP[fuente_id][0])

    lineas = [
        "-- Generado por database/etl/generar_datos_mysql.py",
        "-- Dataset: 4 fuentes abiertas integradas de la Ciudad de Buenos Aires.",
        "START TRANSACTION;",
        "SET NAMES utf8mb4;",
    ]
    lineas.extend(f"INSERT INTO comuna (id_comuna) VALUES ({i});" for i in range(1, 16))
    lineas.extend(
        f"INSERT INTO barrio (id_barrio,nombre,id_comuna) VALUES ({id_},{sql(nombre)},{comuna});"
        for id_, nombre, comuna in barrios
    )
    lineas.extend(
        f"INSERT INTO tipo_lugar (id_tipo,nombre) VALUES ({id_},{sql(nombre)});"
        for id_, nombre in (v for v in TIPOS_APP.values())
    )
    lineas.extend(
        f"INSERT INTO fuente (id_fuente,nombre) VALUES ({f['fuente_id']},{sql(limpiar_texto(f['fuente']))});"
        for f in fuentes
    )
    lineas.extend(
        f"INSERT INTO categoria (id_categoria,nombre,id_tipo) VALUES ({id_},{sql(nombre)},{id_tipo});"
        for id_, nombre, id_tipo in categorias.values()
    )

    omitidos = Counter()
    cargados = 0
    for fila in lugares_raw:
        nombre = limpiar_texto(fila["nombre"])
        if not nombre:
            omitidos["sin_nombre"] += 1
            continue
        lat, lon = numero(fila["latitud"]), numero(fila["longitud"])
        if (lat is None) != (lon is None):
            lat = lon = None
            omitidos["coordenada_incompleta"] += 1
        barrio = mapa_barrio.get(fila["barrio_id"])
        if barrio is None:
            omitidos["sin_barrio"] += 1
        id_categoria = categorias[(fila["fuente_id"], fila["tipo_id"] or "")][0]
        valores = [
            int(fila["id"]), nombre, direccion(fila), lat, lon, id_categoria, barrio,
            int(fila["fuente_id"]), f"integrado-{fila['id']}",
        ]
        lineas.append(
            "INSERT INTO lugar "
            "(id_lugar,nombre,direccion,latitud,longitud,id_categoria,id_barrio,id_fuente,id_origen) VALUES "
            f"({','.join(sql(x) for x in valores)});"
        )
        cargados += 1

    cuentas = [
        (1, "admin", "Administrador Pasaporte BA", "admin@pasaporteba.local", "Admin123!", "admin"),
        (2, "visitante", "Usuario de demostración", "visitante@pasaporteba.local", "Usuario123!", "usuario"),
    ]
    for id_, usuario, nombre, email, password, rol in cuentas:
        lineas.append(
            "INSERT INTO usuario (id_usuario,nombre_usuario,nombre,email,password_hash,rol) VALUES "
            f"({id_},{sql(usuario)},{sql(nombre)},{sql(email)},{sql(hash_demo(usuario, password))},{sql(rol)});"
        )
    lineas.extend(["COMMIT;", ""])
    SALIDA.write_text("\n".join(lineas), encoding="utf-8")
    return {"lugares": cargados, "barrios": len(barrios), "categorias": len(categorias), **omitidos}


if __name__ == "__main__":
    resumen = generar()
    print(f"Generado: {SALIDA}")
    print(" | ".join(f"{clave}={valor}" for clave, valor in resumen.items()))
