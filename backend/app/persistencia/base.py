"""Interfaces de persistencia.

La API solo conoce estas clases abstractas. Cada motor (MySQL, HBase) las implementa
a su manera; el resto de la aplicación no sabe cuál está usando.
"""

import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field

from app.dominio import (
    Barrio, Categoria, Checkin, CheckinCambios, CheckinIn, FiltroLugares, ItemRanking,
    Lugar, LugarCercano, LugarIn, Pagina, Pasaporte, Usuario, UsuarioIn,
)


class NoEncontrado(Exception):
    """La entidad pedida no existe (404)."""


class Conflicto(Exception):
    """La operación viola una regla de integridad (409)."""


class Invalido(Exception):
    """Los datos referencian algo que no existe o no son válidos (422)."""


class MotorNoDisponible(Exception):
    """No se pudo conectar con la base (503)."""


@dataclass
class Traza:
    """Registro de las operaciones que se ejecutaron contra la base en una request."""
    operaciones: list[dict] = field(default_factory=list)
    inicio: float = field(default_factory=time.perf_counter)

    @contextmanager
    def medir(self, descripcion: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.operaciones.append({
                "op": descripcion,
                "ms": round((time.perf_counter() - t0) * 1000, 2),
            })

    def duracion_ms(self) -> float:
        return round((time.perf_counter() - self.inicio) * 1000, 2)


class RepoCatalogo(ABC):
    @abstractmethod
    def barrios(self) -> list[Barrio]: ...

    @abstractmethod
    def categorias(self) -> list[Categoria]: ...


class RepoLugares(ABC):
    @abstractmethod
    def listar(self, filtro: FiltroLugares, limite: int, cursor: str | None) -> Pagina[Lugar]: ...

    @abstractmethod
    def obtener(self, id_lugar: int) -> Lugar: ...

    @abstractmethod
    def crear(self, datos: LugarIn) -> Lugar: ...

    @abstractmethod
    def actualizar(self, id_lugar: int, datos: LugarIn) -> Lugar: ...

    @abstractmethod
    def eliminar(self, id_lugar: int) -> None:
        """Debe lanzar Conflicto si el lugar tiene check-ins."""

    @abstractmethod
    def cercanos(self, lat: float, lon: float, radio_m: float, limite: int) -> list[LugarCercano]: ...


class RepoUsuarios(ABC):
    @abstractmethod
    def listar(self, limite: int, cursor: str | None) -> Pagina[Usuario]: ...

    @abstractmethod
    def obtener(self, id_usuario: int) -> Usuario: ...

    @abstractmethod
    def crear(self, datos: UsuarioIn) -> Usuario: ...


class RepoCheckins(ABC):
    @abstractmethod
    def obtener(self, id_checkin: int) -> Checkin: ...

    @abstractmethod
    def crear(self, datos: CheckinIn) -> Checkin: ...

    @abstractmethod
    def actualizar(self, id_checkin: int, cambios: CheckinCambios) -> Checkin: ...

    @abstractmethod
    def eliminar(self, id_checkin: int) -> None: ...

    @abstractmethod
    def de_lugar(self, id_lugar: int, limite: int, cursor: str | None) -> Pagina[Checkin]:
        """Check-ins de un lugar, del más reciente al más viejo."""

    @abstractmethod
    def de_usuario(self, id_usuario: int, limite: int, cursor: str | None) -> Pagina[Checkin]:
        """Check-ins de un usuario, del más reciente al más viejo."""


class RepoConsultas(ABC):
    @abstractmethod
    def ranking_barrio(self, id_barrio: int, anio: int, mes: int, top: int) -> list[ItemRanking]: ...

    @abstractmethod
    def pasaporte(self, id_usuario: int) -> Pasaporte: ...


@dataclass
class Persistencia:
    """Conjunto de repositorios de un motor, más la traza de la request actual."""
    motor: str
    catalogo: RepoCatalogo
    lugares: RepoLugares
    usuarios: RepoUsuarios
    checkins: RepoCheckins
    consultas: RepoConsultas
    traza: Traza

    def meta(self) -> dict:
        return {
            "motor": self.motor,
            "duracion_ms": self.traza.duracion_ms(),
            "operaciones": self.traza.operaciones,
        }
