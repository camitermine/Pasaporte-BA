"""Construye persistencias internas; el motor de cada función no lo elige el cliente."""

from app.config import MOTORES, settings
from app.persistencia.base import Persistencia
from app.persistencia.hbase.repos import crear_persistencia_hbase
from app.persistencia.hbase.repos import CheckinsHBase, ConsultasHBase
from app.persistencia.hibrida import CheckinsHibridos
from app.persistencia.mysql.repos import crear_persistencia_mysql
from app.persistencia.mysql.repos import (
    CatalogoMySQL, CheckinsMySQL, LugaresMySQL, UsuariosMySQL,
)
from app.persistencia.base import Traza

_FABRICAS = {
    "mysql": crear_persistencia_mysql,
    "hbase": crear_persistencia_hbase,
}


def crear_persistencia(motor: str | None = None) -> Persistencia:
    motor = (motor or settings.motor_db).lower()
    if motor not in MOTORES:
        raise ValueError(f"Motor desconocido: {motor}. Opciones: {', '.join(MOTORES)}")
    return _FABRICAS[motor]()


def crear_persistencia_actividad() -> Persistencia:
    """Persistencia automatica para la actividad; nunca la elige el cliente."""
    if settings.actividad_db.lower() == "mysql":
        return crear_persistencia_mysql()
    if settings.actividad_db.lower() != "hbase":
        raise ValueError("ACTIVIDAD_DB debe ser mysql o hbase")
    traza = Traza()
    lugares = LugaresMySQL(traza)
    return Persistencia(
        motor="hbase",
        catalogo=CatalogoMySQL(traza),
        lugares=lugares,
        usuarios=UsuariosMySQL(traza),
        checkins=CheckinsHibridos(CheckinsMySQL(traza), CheckinsHBase(traza), lugares),
        consultas=ConsultasHBase(traza),
        traza=traza,
    )
