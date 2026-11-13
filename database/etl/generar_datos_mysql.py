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

from correcciones_texto import (
    ABREVIATURAS_DE_CALLE,
    APELLIDOS_CON_ARTICULO,
    CALLES_CORREGIDAS,
    CARACTERES_CORREGIDOS,
    CONECTORES,
    ERRORES_DE_TIPEO,
    FRASES_CORREGIDAS,
    NOMBRES_CORREGIDOS_POR_LUGAR,
    NOMBRES_DE_PILA_ADICIONALES,
    NOMBRES_OFICIALES_BARRIO,
    PALABRAS_CON_LETRA_PERDIDA,
    PALABRAS_CON_TILDE,
    PARTICULAS_DE_NOMBRE,
    PREPOSICIONES_TRAS_AVENIDA,
    PRIMERAS_PALABRAS_DE_CALLE,
    SIGLAS,
    TITULOS_DE_CALLE,
)

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

CODIFICACIONES_ERRONEAS = ("latin-1", "cp1252")
MAXIMO_REPARACIONES = 3

COLUMNAS_DE_CALLE = ("calle", "calle_interseccion")

PALABRA_CON_SIGNO_DE_PREGUNTA = re.compile(r"[^\s.,()]*\?[^\s.,()]*")
PALABRA_EN_MAYUSCULAS = re.compile(r"[A-ZÑÜÁÉÍÓÚÖ]+")
TERMINACIONES_CON_TILDE = ("CION", "SION", "STION")
TERMINACION_EXTRANJERA = "SSION"
PUNTO_COMO_SEPARADOR = re.compile(r"\b([A-ZÑÜÁÉÍÓÚ]{2,})\.(?=\s|,|$)")
AVENIDA_PEGADA = re.compile(r"\bAV\.(?=[A-ZÑÁÉÍÓÚ])")
AVENIDA_AL_INICIO = re.compile(r"^AV\.?\s+")
AVENIDA_AL_FINAL = re.compile(r"\s+AV\.?$")
DIAGONAL = re.compile(r"\bDIAGONAL (NORTE|SUR)\b")
ABREVIATURA_SIN_PUNTO = re.compile(r"\b(" + "|".join(sorted(ABREVIATURAS_DE_CALLE - {"AV"})) + r")\b(?!\.)")
INICIAL = re.compile(r"[A-ZÑ]\.")
ABREVIATURA_PEGADA = re.compile(r"\b([A-ZÑÜÁÉÍÓÚ]{2,})\.(?=[A-ZÑÜÁÉÍÓÚ])(?!(?:COM|AR|NET|ORG)\b)")
NUMERO_ROMANO = re.compile(r"(?=[IVXLC]{2,}$)C{0,3}(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})")
INICIALES_CON_PUNTO = re.compile(r"(?:[A-Z]\.){2,}")
INICIO_DE_PALABRA = re.compile(r"(?<![\w'’])\w")


def leer(nombre: str) -> list[dict[str, str]]:
    with (ORIGEN / nombre).open(encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo))


def puntaje_codificacion(texto: str) -> int:
    marcadores = "ÃÂâðï"
    return sum(texto.count(x) for x in marcadores) + sum(0x80 <= ord(c) <= 0x9F for c in texto)


def decodificar_como_utf8(texto: str, codificacion: str) -> str | None:
    try:
        return texto.encode(codificacion).decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None


def reparar_un_nivel(texto: str) -> str | None:
    candidatos = [decodificar_como_utf8(texto, codificacion) for codificacion in CODIFICACIONES_ERRONEAS]
    mejoras = [c for c in candidatos if c is not None and puntaje_codificacion(c) < puntaje_codificacion(texto)]
    return min(mejoras, key=puntaje_codificacion) if mejoras else None


def reparar_codificacion(texto: str) -> str:
    for _ in range(MAXIMO_REPARACIONES):
        reparado = reparar_un_nivel(texto)
        if reparado is None:
            break
        texto = reparado
    return texto


def corregir_caracteres(texto: str) -> str:
    return "".join(CARACTERES_CORREGIDOS.get(caracter, caracter) for caracter in texto)


def recuperar_letras_perdidas(texto: str) -> str:
    return PALABRA_CON_SIGNO_DE_PREGUNTA.sub(
        lambda palabra: PALABRAS_CON_LETRA_PERDIDA.get(palabra.group(), palabra.group()), texto
    )


def acentuar_terminacion(palabra: str) -> str:
    if len(palabra) > 4 and palabra.endswith(TERMINACIONES_CON_TILDE) and not palabra.endswith(TERMINACION_EXTRANJERA):
        return palabra[:-3] + "IÓN"
    return palabra


def corregir_palabra(palabra: str) -> str:
    corregida = ERRORES_DE_TIPEO.get(palabra, palabra)
    return acentuar_terminacion(PALABRAS_CON_TILDE.get(corregida, corregida))


def corregir_frases(texto: str) -> str:
    for frase, correccion in FRASES_CORREGIDAS.items():
        texto = re.sub(rf"\b{frase}\b", correccion, texto)
    return texto


def corregir_ortografia(texto: str) -> str:
    return PALABRA_EN_MAYUSCULAS.sub(lambda palabra: corregir_palabra(palabra.group()), corregir_frases(texto))


def limpiar_texto(valor: str | None) -> str | None:
    if valor is None:
        return None
    texto = valor.strip()
    if not texto:
        return None
    texto = recuperar_letras_perdidas(corregir_caracteres(reparar_codificacion(texto)))
    return corregir_ortografia(re.sub(r"\s+", " ", texto).strip())


def separar_abreviaturas(texto: str | None) -> str | None:
    return ABREVIATURA_PEGADA.sub(r"\1. ", texto) if texto else texto


def nombre_lugar(fila: dict[str, str]) -> str | None:
    nombre = separar_abreviaturas(limpiar_texto(fila["nombre"]))
    return NOMBRES_CORREGIDOS_POR_LUGAR.get(fila["id"]) or formato_titulo(nombre)


def es_sigla(palabra: str) -> bool:
    nucleo = re.sub(r"^\W+|[^\w.]+$", "", palabra)
    return (
        nucleo.rstrip(".") in SIGLAS
        or bool(NUMERO_ROMANO.fullmatch(nucleo))
        or bool(INICIALES_CON_PUNTO.fullmatch(nucleo))
    )


def formatear_palabra(palabra: str, es_primera: bool) -> str:
    if es_sigla(palabra):
        return palabra
    minuscula = palabra.lower()
    if not es_primera and minuscula in CONECTORES:
        return minuscula
    return INICIO_DE_PALABRA.sub(lambda letra: letra.group().upper(), minuscula)


def formato_titulo(texto: str | None) -> str | None:
    if not texto or texto != texto.upper():
        return texto
    palabras = texto.split(" ")
    return " ".join(
        formatear_palabra(palabra, indice == 0 or palabras[indice - 1].endswith("?"))
        for indice, palabra in enumerate(palabras)
    )


def nombre_barrio(texto: str) -> str:
    return NOMBRES_OFICIALES_BARRIO.get(clave_texto(texto)) or formato_titulo(texto) or texto


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


def separar_con_comas(calle: str) -> str:
    texto = calle.replace("..", ".,")
    return PUNTO_COMO_SEPARADOR.sub(
        lambda palabra: palabra.group() if palabra.group(1) in ABREVIATURAS_DE_CALLE else palabra.group(1) + ",",
        texto,
    )


def quitar_avenida(calle: str) -> tuple[str, bool]:
    sin_avenida = AVENIDA_AL_FINAL.sub("", AVENIDA_AL_INICIO.sub("", calle))
    return sin_avenida, sin_avenida != calle


def preparar_calle(calle: str) -> tuple[str, bool]:
    con_puntos = ABREVIATURA_SIN_PUNTO.sub(r"\1.", AVENIDA_PEGADA.sub("AV. ", calle.upper()))
    return quitar_avenida(separar_con_comas(con_puntos))


def clave_calle(calle: str) -> tuple[str, ...]:
    return tuple(sorted(clave_texto(palabra) for palabra in re.findall(r"[^\s.,]+", calle)))


def mover_al_inicio(palabras: list[str], finales_movibles: set[str]) -> list[str]:
    corte = len(palabras)
    while corte > 0 and palabras[corte - 1] in finales_movibles:
        corte -= 1
    return palabras[corte:] + palabras[:corte]


def mover_titulos_al_inicio(palabras: list[str]) -> list[str]:
    return mover_al_inicio(palabras, TITULOS_DE_CALLE)


def es_parte_de_titulos(parte: list[str]) -> bool:
    return all(palabra in TITULOS_DE_CALLE for palabra in parte)


def ordenar_partes_con_comas(texto: str) -> list[str]:
    partes = [parte.split() for parte in texto.split(",") if parte.split()]
    titulos = [palabra for parte in partes if es_parte_de_titulos(parte) for palabra in parte]
    nombres = [parte for parte in partes if not es_parte_de_titulos(parte)]
    if nombres:
        nombres[0] = mover_al_inicio(nombres[0], PARTICULAS_DE_NOMBRE)
    return titulos + [palabra for parte in reversed(nombres) for palabra in mover_titulos_al_inicio(parte)]


def completa_nombre(palabra: str, nombres_de_pila: set[str]) -> bool:
    return (
        palabra in nombres_de_pila
        or palabra in TITULOS_DE_CALLE
        or palabra in PARTICULAS_DE_NOMBRE
        or bool(INICIAL.fullmatch(palabra))
    )


def es_nombre_invertible(palabras: list[str], nombres_de_pila: set[str]) -> bool:
    return (
        len(palabras) > 1
        and palabras[0] not in nombres_de_pila
        and palabras[0] not in PRIMERAS_PALABRAS_DE_CALLE
        and "Y" not in palabras
        and not any(palabra.isdigit() for palabra in palabras)
    )


def poner_nombre_antes_del_apellido(palabras: list[str], nombres_de_pila: set[str]) -> list[str]:
    if not es_nombre_invertible(palabras, nombres_de_pila):
        return palabras
    corte = len(palabras)
    while corte > 1 and completa_nombre(palabras[corte - 1], nombres_de_pila):
        corte -= 1
    complemento = palabras[corte:]
    titulos = [palabra for palabra in complemento if palabra in TITULOS_DE_CALLE]
    nombres = [palabra for palabra in complemento if palabra not in TITULOS_DE_CALLE]
    return titulos + nombres + palabras[:corte]


def ordenar_palabras(texto: str, nombres_de_pila: set[str]) -> list[str]:
    if "," in texto:
        return ordenar_partes_con_comas(texto)
    return mover_titulos_al_inicio(poner_nombre_antes_del_apellido(texto.split(), nombres_de_pila))


def anteponer_avenida(nombre: str) -> str:
    primera, _, resto = nombre.partition(" ")
    if primera.lower() in PREPOSICIONES_TRAS_AVENIDA:
        primera = primera.lower()
    return f"Av. {primera} {resto}".strip()


def corregir_articulos(nombre: str) -> str:
    for incorrecto, correcto in APELLIDOS_CON_ARTICULO.items():
        nombre = nombre.replace(incorrecto, correcto)
    return nombre


def formatear_calle(texto: str, es_avenida: bool, nombres_de_pila: set[str]) -> str:
    diagonal = DIAGONAL.search(texto)
    palabras = ordenar_palabras(DIAGONAL.sub("", texto), nombres_de_pila)
    if diagonal:
        return formato_titulo(" ".join([diagonal.group(), *palabras]))
    nombre = corregir_articulos(formato_titulo(" ".join(palabras)))
    return anteponer_avenida(nombre) if es_avenida else nombre


def obtener_nombres_de_pila(textos: list[str]) -> set[str]:
    partes_de_nombre = [texto.split(",")[1] for texto in textos if texto.count(",") >= 1]
    return {
        palabra
        for parte in partes_de_nombre
        for palabra in parte.split()
        if palabra.isalpha() and palabra not in TITULOS_DE_CALLE
    } | NOMBRES_DE_PILA_ADICIONALES


def empieza_con_preposicion(texto: str) -> bool:
    return texto.split(" ", 1)[0].lower() in PREPOSICIONES_TRAS_AVENIDA


def es_avenida_sin_marcar(texto: str, avenidas: set[tuple[str, ...]]) -> bool:
    return empieza_con_preposicion(texto) and clave_calle(texto) in avenidas


def normalizar_calles(lugares: list[dict[str, str]]) -> dict[str, str]:
    calles = {limpiar_texto(fila[columna]) for fila in lugares for columna in COLUMNAS_DE_CALLE} - {None}
    preparadas = {calle: preparar_calle(calle) for calle in calles}
    textos = [texto for texto, _ in preparadas.values()]
    nombres_de_pila = obtener_nombres_de_pila(textos)
    orden_con_comas = {clave_calle(texto): texto for texto in textos if "," in texto}
    avenidas = {clave_calle(texto) for texto, es_avenida in preparadas.values() if es_avenida}
    return {
        calle: CALLES_CORREGIDAS.get(clave_texto(calle))
        or formatear_calle(
            orden_con_comas.get(clave_calle(texto), texto),
            es_avenida or es_avenida_sin_marcar(texto, avenidas),
            nombres_de_pila,
        )
        for calle, (texto, es_avenida) in preparadas.items()
    }


def nombre_calle(valor: str | None, calles: dict[str, str]) -> str | None:
    limpia = limpiar_texto(valor)
    return calles.get(limpia) if limpia else None


def direccion(fila: dict[str, str], calles: dict[str, str]) -> str | None:
    calle = nombre_calle(fila["calle"], calles)
    altura = limpiar_texto(fila["altura"])
    interseccion = nombre_calle(fila["calle_interseccion"], calles)
    if calle and altura:
        return f"{calle} {altura}"
    if calle and interseccion:
        return f"{calle} y {interseccion}"
    return calle


def generar() -> dict[str, int]:
    MODELO.write_text(
        (RAIZ / "backend" / "dev" / "schema_mysql_dev.sql").read_text(encoding="utf-8"),
        encoding="utf-8", newline="\n",
    )
    barrios_raw = leer("barrios.csv")
    fuentes = leer("fuentes.csv")
    tipos = {f["tipo_id"]: formato_titulo(limpiar_texto(f["tipo"])) or "Sin clasificar" for f in leer("tipos.csv")}
    lugares_raw = leer("lugares.csv")
    calles = normalizar_calles(lugares_raw)

    barrios: list[tuple[int, str, int]] = []
    barrio_por_clave: dict[str, int] = {}
    mapa_barrio: dict[str, int] = {}
    for fila in barrios_raw:
        nombre = nombre_barrio(limpiar_texto(fila["barrio"]) or "")
        clave = clave_texto(nombre)
        if clave not in barrio_por_clave:
            nuevo_id = len(barrios) + 1
            barrio_por_clave[clave] = nuevo_id
            barrios.append((nuevo_id, nombre, int(fila["comuna"])))
        mapa_barrio[fila["barrio_id"]] = barrio_por_clave[clave]

    categorias_clave = sorted({
        (f["fuente_id"], f["tipo_id"] or "") for f in lugares_raw
    }, key=lambda x: (int(x[0]), int(x[1]) if x[1].isdigit() else 9999))
    # Una categoría es única por (nombre, tipo) sin distinguir acentos, igual que la
    # restricción UNIQUE de MySQL (collation *_ai_ci). La fuente trae variantes como
    # "OLEO S/TELA" y "ÖLEO S/TELA": se consolidan en la primera que aparece.
    categorias: dict[tuple[str, str], tuple[int, str, int]] = {}
    categoria_por_clave: dict[tuple[str, int], tuple[int, str, int]] = {}
    for clave in categorias_clave:
        fuente_id, tipo_id = clave
        nombre = tipos.get(tipo_id, "Sin clasificar")
        id_tipo = TIPOS_APP[fuente_id][0]
        unica = (clave_texto(nombre), id_tipo)
        if unica not in categoria_por_clave:
            categoria_por_clave[unica] = (len(categoria_por_clave) + 1, nombre, id_tipo)
        categorias[clave] = categoria_por_clave[unica]

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
        for id_, nombre, id_tipo in categoria_por_clave.values()
    )

    omitidos = Counter()
    cargados = 0
    for fila in lugares_raw:
        nombre = nombre_lugar(fila)
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
            int(fila["id"]), nombre, direccion(fila, calles), lat, lon, id_categoria, barrio,
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
    SALIDA.write_text("\n".join(lineas), encoding="utf-8", newline="\n")
    return {"lugares": cargados, "barrios": len(barrios), "categorias": len(categoria_por_clave), **omitidos}


if __name__ == "__main__":
    resumen = generar()
    print(f"Generado: {SALIDA}")
    print(" | ".join(f"{clave}={valor}" for clave, valor in resumen.items()))
