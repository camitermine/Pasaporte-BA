"""Coordinacion de actividad entre MySQL y HBase.

MySQL conserva el registro canonico y sus claves foraneas. HBase mantiene la
proyeccion desnormalizada utilizada para historiales, pasaporte y rankings.
"""

from app.dominio import Checkin, CheckinCambios, CheckinIn, Pagina
from app.persistencia.base import Invalido, RepoCheckins
from app.persistencia.hbase.repos import CheckinsHBase
from app.persistencia.mysql.repos import CheckinsMySQL, LugaresMySQL


class CheckinsHibridos(RepoCheckins):
    def __init__(self, mysql: CheckinsMySQL, hbase: CheckinsHBase, lugares: LugaresMySQL):
        self.mysql = mysql
        self.hbase = hbase
        self.lugares = lugares

    def obtener(self, id_checkin: int) -> Checkin:
        return self.hbase.obtener(id_checkin)

    def crear(self, datos: CheckinIn) -> Checkin:
        lugar = self.lugares.obtener(datos.id_lugar)
        if lugar.barrio is None:
            raise Invalido("El lugar todavía no tiene un barrio validado y no admite check-in")
        canonico = self.mysql.crear(datos)
        return self.hbase.replicar(canonico, lugar.barrio.id, lugar.barrio.nombre)

    def actualizar(self, id_checkin: int, cambios: CheckinCambios) -> Checkin:
        self.mysql.actualizar(id_checkin, cambios)
        return self.hbase.actualizar(id_checkin, cambios)

    def eliminar(self, id_checkin: int) -> None:
        self.hbase.eliminar(id_checkin)
        self.mysql.eliminar(id_checkin)

    def de_lugar(self, id_lugar: int, limite: int, cursor: str | None) -> Pagina[Checkin]:
        return self.hbase.de_lugar(id_lugar, limite, cursor)

    def de_usuario(self, id_usuario: int, limite: int, cursor: str | None) -> Pagina[Checkin]:
        return self.hbase.de_usuario(id_usuario, limite, cursor)
