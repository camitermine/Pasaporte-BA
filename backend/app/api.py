"""Rutas HTTP. No conocen el motor: solo usan las interfaces de app.persistencia.base."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder

from app.config import MOTORES, settings
from app.dominio import CheckinCambios, CheckinIn, FiltroLugares, LugarIn, UsuarioIn
from app.persistencia.base import Persistencia
from app.persistencia.fabrica import crear_persistencia

router = APIRouter()


def persistencia(
    request: Request,
    x_motor: Annotated[str | None, Header(description="mysql | hbase")] = None,
    motor: Annotated[str | None, Query(description="Alternativa al header X-Motor")] = None,
) -> Persistencia:
    try:
        p = crear_persistencia(x_motor or motor)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    request.state.persistencia = p  # para que los manejadores de error puedan incluir la traza
    return p


P = Annotated[Persistencia, Depends(persistencia)]
Limite = Annotated[int, Query(ge=1, le=100)]


def ok(p: Persistencia, data) -> dict:
    return {"data": jsonable_encoder(data), "meta": p.meta()}


# ---------------------------------------------------------------- motores y catálogo

@router.get("/motores", tags=["general"])
def motores():
    return {"data": {"disponibles": list(MOTORES), "por_defecto": settings.motor_db}}


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
def crear_lugar(p: P, datos: LugarIn):
    return ok(p, p.lugares.crear(datos))


@router.put("/lugares/{id_lugar}", tags=["lugares"])
def actualizar_lugar(p: P, id_lugar: int, datos: LugarIn):
    return ok(p, p.lugares.actualizar(id_lugar, datos))


@router.delete("/lugares/{id_lugar}", tags=["lugares"])
def eliminar_lugar(p: P, id_lugar: int):
    p.lugares.eliminar(id_lugar)
    return ok(p, {"eliminado": id_lugar})


@router.get("/lugares/{id_lugar}/checkins", tags=["lugares"])
def checkins_de_lugar(p: P, id_lugar: int, limite: Limite = 20, cursor: str | None = None):
    return ok(p, p.checkins.de_lugar(id_lugar, limite, cursor))


# ---------------------------------------------------------------- usuarios

@router.get("/usuarios", tags=["usuarios"])
def listar_usuarios(p: P, limite: Limite = 50, cursor: str | None = None):
    return ok(p, p.usuarios.listar(limite, cursor))


@router.get("/usuarios/{id_usuario}", tags=["usuarios"])
def obtener_usuario(p: P, id_usuario: int):
    return ok(p, p.usuarios.obtener(id_usuario))


@router.post("/usuarios", tags=["usuarios"], status_code=201)
def crear_usuario(p: P, datos: UsuarioIn):
    return ok(p, p.usuarios.crear(datos))


@router.get("/usuarios/{id_usuario}/checkins", tags=["usuarios"])
def checkins_de_usuario(p: P, id_usuario: int, limite: Limite = 20, cursor: str | None = None):
    return ok(p, p.checkins.de_usuario(id_usuario, limite, cursor))


# ---------------------------------------------------------------- check-ins

@router.post("/checkins", tags=["checkins"], status_code=201)
def crear_checkin(p: P, datos: CheckinIn):
    return ok(p, p.checkins.crear(datos))


@router.get("/checkins/{id_checkin}", tags=["checkins"])
def obtener_checkin(p: P, id_checkin: int):
    return ok(p, p.checkins.obtener(id_checkin))


@router.put("/checkins/{id_checkin}", tags=["checkins"])
def actualizar_checkin(p: P, id_checkin: int, cambios: CheckinCambios):
    return ok(p, p.checkins.actualizar(id_checkin, cambios))


@router.delete("/checkins/{id_checkin}", tags=["checkins"])
def eliminar_checkin(p: P, id_checkin: int):
    p.checkins.eliminar(id_checkin)
    return ok(p, {"eliminado": id_checkin})


# ---------------------------------------------------------------- consultas complejas

@router.get("/consultas/ranking-barrio", tags=["consultas"])
def ranking_barrio(p: P, barrio: int, mes: Annotated[str, Query(description="YYYY-MM")],
                   top: Annotated[int, Query(ge=1, le=50)] = 10):
    m = re.fullmatch(r"(\d{4})-(\d{2})", mes)
    if not m or not 1 <= int(m.group(2)) <= 12:
        raise HTTPException(422, "mes debe tener formato YYYY-MM")
    return ok(p, p.consultas.ranking_barrio(barrio, int(m.group(1)), int(m.group(2)), top))


@router.get("/consultas/pasaporte/{id_usuario}", tags=["consultas"])
def pasaporte(p: P, id_usuario: int):
    return ok(p, p.consultas.pasaporte(id_usuario))
