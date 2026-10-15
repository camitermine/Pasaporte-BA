"""Modelos de dominio: lo que expone la API, igual para cualquier motor."""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Barrio(BaseModel):
    id: int
    nombre: str
    comuna: int


class Categoria(BaseModel):
    id: int
    nombre: str
    tipo: str


class Ref(BaseModel):
    """Referencia corta a otra entidad (id + nombre)."""
    id: int
    nombre: str


class Lugar(BaseModel):
    id: int
    nombre: str
    direccion: str | None = None
    latitud: float | None = None
    longitud: float | None = None
    categoria: Categoria
    barrio: Barrio
    fuente: str | None = None


class LugarIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    direccion: str | None = Field(None, max_length=200)
    latitud: float | None = Field(None, ge=-90, le=90)
    longitud: float | None = Field(None, ge=-180, le=180)
    id_categoria: int
    id_barrio: int


class LugarCercano(BaseModel):
    lugar: Lugar
    distancia_m: float


class Usuario(BaseModel):
    id: int
    nombre_usuario: str
    nombre: str
    email: str
    barrio: Barrio | None = None
    fecha_alta: datetime


class UsuarioIn(BaseModel):
    nombre_usuario: str = Field(min_length=3, max_length=30, pattern=r"^[a-z0-9_.]+$")
    nombre: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    id_barrio: int | None = None


class Checkin(BaseModel):
    id: int
    usuario: Ref
    lugar: Ref
    fecha_hora: datetime
    puntaje: int | None = None
    comentario: str | None = None


class CheckinIn(BaseModel):
    id_usuario: int
    id_lugar: int
    fecha_hora: datetime | None = None  # si no viene, ahora
    puntaje: int | None = Field(None, ge=1, le=5)
    comentario: str | None = Field(None, max_length=280)


class CheckinCambios(BaseModel):
    puntaje: int | None = Field(None, ge=1, le=5)
    comentario: str | None = Field(None, max_length=280)


class Pagina(BaseModel, Generic[T]):
    items: list[T]
    siguiente_cursor: str | None = None


class FiltroLugares(BaseModel):
    id_barrio: int | None = None
    id_categoria: int | None = None
    q: str | None = None


class ItemRanking(BaseModel):
    puesto: int
    lugar: Ref
    categoria: str
    checkins: int


class BarrioVisitado(BaseModel):
    barrio: Barrio
    checkins: int


class Pasaporte(BaseModel):
    usuario: Ref
    total_checkins: int
    lugares_distintos: int
    barrios_visitados: list[BarrioVisitado]
    barrios_faltantes: list[Barrio]
    progreso: float  # % de barrios visitados
