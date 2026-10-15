"""Elige la implementación de persistencia según el motor pedido."""

from app.config import MOTORES, settings
from app.persistencia.base import Persistencia
from app.persistencia.hbase.repos import crear_persistencia_hbase
from app.persistencia.mysql.repos import crear_persistencia_mysql

_FABRICAS = {
    "mysql": crear_persistencia_mysql,
    "hbase": crear_persistencia_hbase,
}


def crear_persistencia(motor: str | None = None) -> Persistencia:
    motor = (motor or settings.motor_db).lower()
    if motor not in MOTORES:
        raise ValueError(f"Motor desconocido: {motor}. Opciones: {', '.join(MOTORES)}")
    return _FABRICAS[motor]()
