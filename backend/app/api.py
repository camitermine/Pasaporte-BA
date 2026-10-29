"""API HTTP de Pasaporte BA.

El cliente no elige una base. El backend asigna cada responsabilidad al motor
correspondiente y devuelve esa informacion en ``meta`` para hacerla visible.
"""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder

from app.config import settings
from app.dominio import (
    CheckinCambios, CheckinIn, FiltroLugares, LoginIn, LugarIn, RevisionSugerencia,
    SugerenciaLugarIn, Usuario, UsuarioCrear,
)
from app.persistencia.base import NoAutorizado, Persistencia, Prohibido
from app.persistencia.fabrica import crear_persistencia, crear_persistencia_actividad
from app.persistencia.mysql.cuentas import CuentasMySQL, FavoritosMySQL, SugerenciasMySQL
from app.persistencia.hbase.proyeccion import ProyectorHBase

router = APIRouter()


def persistencia(request: Request) -> Persistencia:
    # Los datos maestros y las escrituras transaccionales son responsabilidad de MySQL.
    p = crear_persistencia("mysql")
    request.state.persistencia = p
    return p


P = Annotated[Persistencia, Depends(persistencia)]
Limite = Annotated[int, Query(ge=1, le=100)]


def persistencia_actividad(request: Request) -> Persistencia:
    p = crear_persistencia_actividad()
    request.state.persistencia = p
    return p


A = Annotated[Persistencia, Depends(persistencia_actividad)]


def _token(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise NoAutorizado("Iniciá sesión para continuar")
    token = authorization[7:].strip()
    if not token:
        raise NoAutorizado("Iniciá sesión para continuar")
    return token


def usuario_actual(p: P, token: Annotated[str, Depends(_token)]) -> Usuario:
    return CuentasMySQL(p.traza).autenticar(token)


Actual = Annotated[Usuario, Depends(usuario_actual)]
Token = Annotated[str, Depends(_token)]


def exigir_admin(usuario: Usuario) -> None:
    if usuario.rol != "admin":
        raise Prohibido("Esta operación requiere permisos de administrador")


def exigir_mismo_usuario_o_admin(actual: Usuario, id_usuario: int) -> None:
    if actual.id != id_usuario and actual.rol != "admin":
        raise Prohibido("No podés acceder a los datos de otro usuario")


def proyectar_lugar_si_corresponde(p: Persistencia, lugar) -> None:
    if settings.actividad_db.lower() == "hbase":
        ProyectorHBase(p.traza).sincronizar_lugar(lugar)


def proyectar_usuario_si_corresponde(p: Persistencia, usuario: Usuario) -> None:
    if settings.actividad_db.lower() == "hbase":
        ProyectorHBase(p.traza).sincronizar_usuario(usuario)


def ok(p: Persistencia, data) -> dict:
    return {"data": jsonable_encoder(data), "meta": p.meta()}


# ---------------------------------------------------------------- autenticacion

@router.post("/auth/login", tags=["autenticación"])
def login(p: P, datos: LoginIn):
    return ok(p, CuentasMySQL(p.traza).login(datos.usuario, datos.password))


@router.get("/auth/me", tags=["autenticación"])
def mi_sesion(p: P, actual: Actual):
    return ok(p, actual)


@router.post("/auth/logout", tags=["autenticación"])
def logout(p: P, token: Token):
    CuentasMySQL(p.traza).logout(token)
    return ok(p, {"sesion_cerrada": True})


# ---------------------------------------------------------------- estado y catalogo

@router.get("/motores", tags=["general"])
def motores():
    return {"data": {
        "seleccion_usuario": False,
        "datos_maestros": "mysql",
        "actividad": settings.actividad_db,
    }}


@router.get("/barrios", tags=["catálogo"])
def barrios(p: P):
    return ok(p, p.catalogo.barrios())


@router.get("/categorias", tags=["catálogo"])
def categorias(p: P):
    return ok(p, p.catalogo.categorias())


# ---------------------------------------------------------------- lugares

@router.get("/lugares", tags=["lugares"])
def listar_lugares(p: P, barrio: int | None = None, categoria: int | None = None,
                   q: str | None = None, limite: Limite = 20, cursor: str | None = None):
    filtro = FiltroLugares(id_barrio=barrio, id_categoria=categoria, q=q or None)
    return ok(p, p.lugares.listar(filtro, limite, cursor))


@router.get("/lugares/cercanos", tags=["lugares"])
def lugares_cercanos(p: P, lat: float, lon: float,
                     radio_m: Annotated[float, Query(gt=0, le=20_000)] = 1000, limite: Limite = 20):
    return ok(p, p.lugares.cercanos(lat, lon, radio_m, limite))


@router.get("/lugares/{id_lugar}", tags=["lugares"])
def obtener_lugar(p: P, id_lugar: int):
    return ok(p, p.lugares.obtener(id_lugar))


@router.post("/lugares", tags=["lugares"], status_code=201)
def crear_lugar(p: P, actual: Actual, datos: LugarIn):
    exigir_admin(actual)
    lugar = p.lugares.crear(datos)
    proyectar_lugar_si_corresponde(p, lugar)
    return ok(p, lugar)


@router.put("/lugares/{id_lugar}", tags=["lugares"])
def actualizar_lugar(p: P, actual: Actual, id_lugar: int, datos: LugarIn):
    exigir_admin(actual)
    lugar = p.lugares.actualizar(id_lugar, datos)
    proyectar_lugar_si_corresponde(p, lugar)
    return ok(p, lugar)


@router.delete("/lugares/{id_lugar}", tags=["lugares"])
def eliminar_lugar(p: P, actual: Actual, id_lugar: int):
    exigir_admin(actual)
    p.lugares.eliminar(id_lugar)
    if settings.actividad_db.lower() == "hbase":
        ProyectorHBase(p.traza).desactivar_lugar(id_lugar)
    return ok(p, {"desactivado": id_lugar})


@router.get("/lugares/{id_lugar}/checkins", tags=["lugares"])
def checkins_de_lugar(p: A, id_lugar: int, limite: Limite = 20, cursor: str | None = None):
    return ok(p, p.checkins.de_lugar(id_lugar, limite, cursor))


# ---------------------------------------------------------------- usuarios y cuentas administradas

@router.get("/usuarios", tags=["usuarios"])
def listar_usuarios(p: P, actual: Actual, limite: Limite = 50, cursor: str | None = None):
    exigir_admin(actual)
    return ok(p, p.usuarios.listar(limite, cursor))


@router.get("/usuarios/{id_usuario}", tags=["usuarios"])
def obtener_usuario(p: P, actual: Actual, id_usuario: int):
    exigir_mismo_usuario_o_admin(actual, id_usuario)
    return ok(p, p.usuarios.obtener(id_usuario))


@router.post("/usuarios", tags=["usuarios"], status_code=201)
def crear_usuario(p: P, actual: Actual, datos: UsuarioCrear):
    exigir_admin(actual)
    usuario = CuentasMySQL(p.traza).crear_usuario(datos)
    proyectar_usuario_si_corresponde(p, usuario)
    return ok(p, usuario)


@router.get("/usuarios/{id_usuario}/checkins", tags=["usuarios"])
def checkins_de_usuario(p: A, actual: Actual, id_usuario: int,
                        limite: Limite = 20, cursor: str | None = None):
    exigir_mismo_usuario_o_admin(actual, id_usuario)
    return ok(p, p.checkins.de_usuario(id_usuario, limite, cursor))


# ---------------------------------------------------------------- favoritos

@router.get("/me/favoritos", tags=["favoritos"])
def listar_favoritos(p: P, actual: Actual, limite: Limite = 50, cursor: str | None = None):
    return ok(p, FavoritosMySQL(p.traza).listar(actual.id, limite, cursor))


@router.get("/me/favoritos/{id_lugar}", tags=["favoritos"])
def consultar_favorito(p: P, actual: Actual, id_lugar: int):
    return ok(p, {"favorito": FavoritosMySQL(p.traza).contiene(actual.id, id_lugar)})


@router.put("/me/favoritos/{id_lugar}", tags=["favoritos"])
def agregar_favorito(p: P, actual: Actual, id_lugar: int):
    FavoritosMySQL(p.traza).agregar(actual.id, id_lugar)
    return ok(p, {"favorito": True})


@router.delete("/me/favoritos/{id_lugar}", tags=["favoritos"])
def quitar_favorito(p: P, actual: Actual, id_lugar: int):
    FavoritosMySQL(p.traza).quitar(actual.id, id_lugar)
    return ok(p, {"favorito": False})


# ---------------------------------------------------------------- sugerencias y moderacion

@router.post("/sugerencias", tags=["sugerencias"], status_code=201)
def crear_sugerencia(p: P, actual: Actual, datos: SugerenciaLugarIn):
    return ok(p, SugerenciasMySQL(p.traza).crear(actual.id, datos))


@router.get("/sugerencias", tags=["sugerencias"])
def listar_sugerencias(p: P, actual: Actual,
                       estado: Annotated[str | None, Query(pattern="^(pendiente|aprobada|rechazada)$")] = None):
    return ok(p, SugerenciasMySQL(p.traza).listar(actual, estado))


@router.put("/sugerencias/{id_sugerencia}/revision", tags=["sugerencias"])
def revisar_sugerencia(p: P, actual: Actual, id_sugerencia: int, revision: RevisionSugerencia):
    exigir_admin(actual)
    resultado = SugerenciasMySQL(p.traza).revisar(id_sugerencia, actual, revision)
    if resultado.id_lugar_creado:
        proyectar_lugar_si_corresponde(p, p.lugares.obtener(resultado.id_lugar_creado))
    return ok(p, resultado)


# ---------------------------------------------------------------- check-ins

@router.post("/checkins", tags=["checkins"], status_code=201)
def crear_checkin(p: A, actual: Actual, datos: CheckinIn):
    propios = datos.model_copy(update={"id_usuario": actual.id})
    return ok(p, p.checkins.crear(propios))


@router.get("/checkins/{id_checkin}", tags=["checkins"])
def obtener_checkin(p: A, id_checkin: int):
    return ok(p, p.checkins.obtener(id_checkin))


@router.put("/checkins/{id_checkin}", tags=["checkins"])
def actualizar_checkin(p: A, actual: Actual, id_checkin: int, cambios: CheckinCambios):
    checkin = p.checkins.obtener(id_checkin)
    exigir_mismo_usuario_o_admin(actual, checkin.usuario.id)
    return ok(p, p.checkins.actualizar(id_checkin, cambios))


@router.delete("/checkins/{id_checkin}", tags=["checkins"])
def eliminar_checkin(p: A, actual: Actual, id_checkin: int):
    checkin = p.checkins.obtener(id_checkin)
    exigir_mismo_usuario_o_admin(actual, checkin.usuario.id)
    p.checkins.eliminar(id_checkin)
    return ok(p, {"eliminado": id_checkin})


# ---------------------------------------------------------------- consultas complejas

@router.get("/consultas/ranking-barrio", tags=["consultas"])
def ranking_barrio(p: A, barrio: int, mes: Annotated[str, Query(description="YYYY-MM")],
                   top: Annotated[int, Query(ge=1, le=50)] = 10):
    m = re.fullmatch(r"(\d{4})-(\d{2})", mes)
    if not m or not 1 <= int(m.group(2)) <= 12:
        raise HTTPException(422, "mes debe tener formato YYYY-MM")
    return ok(p, p.consultas.ranking_barrio(barrio, int(m.group(1)), int(m.group(2)), top))


@router.get("/consultas/pasaporte/{id_usuario}", tags=["consultas"])
def pasaporte(p: A, actual: Actual, id_usuario: int):
    exigir_mismo_usuario_o_admin(actual, id_usuario)
    return ok(p, p.consultas.pasaporte(id_usuario))
