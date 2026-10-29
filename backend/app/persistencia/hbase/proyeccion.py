"""Proyeccion de datos maestros MySQL necesarios para las consultas HBase."""

import happybase

from app.config import settings
from app.dominio import Lugar, Usuario
from app.persistencia.hbase import geohash
from app.persistencia.hbase.claves import a_celdas, clave, de_celdas, pad
from app.persistencia.base import MotorNoDisponible, Traza


class ProyectorHBase:
    def __init__(self, traza: Traza):
        self.traza = traza

    def _conexion(self):
        return happybase.Connection(settings.hbase_host, settings.hbase_port)

    def sincronizar_lugar(self, lugar: Lugar) -> None:
        if lugar.barrio is None:
            return
        try:
            with self.traza.medir(f"HBASE PROJECT lugar {lugar.id}"):
                con = self._conexion()
                principal = con.table("lugares")
                anterior = de_celdas(principal.row(clave(lugar.id)))
                if anterior:
                    con.table("lugares_por_barrio").delete(
                        clave(int(anterior["id_barrio"]), lugar.id))
                    con.table("lugares_por_categoria").delete(
                        clave(int(anterior["id_categoria"]), lugar.id))
                    if anterior.get("geohash"):
                        con.table("lugares_por_geohash").delete(
                            f"{anterior['geohash']}#{pad(lugar.id)}".encode())
                gh = None
                if lugar.latitud is not None and lugar.longitud is not None:
                    gh = geohash.codificar(lugar.latitud, lugar.longitud, 6)
                principal.put(clave(lugar.id), a_celdas({
                    "nombre": lugar.nombre, "direccion": lugar.direccion,
                    "lat": lugar.latitud, "lon": lugar.longitud, "geohash": gh,
                    "id_categoria": lugar.categoria.id, "categoria": lugar.categoria.nombre,
                    "tipo": lugar.categoria.tipo, "id_barrio": lugar.barrio.id,
                    "barrio": lugar.barrio.nombre, "comuna": lugar.barrio.comuna,
                    "fuente": lugar.fuente,
                }))
                con.table("lugares_por_barrio").put(
                    clave(lugar.barrio.id, lugar.id),
                    a_celdas({"nombre": lugar.nombre.lower(), "id_categoria": lugar.categoria.id}),
                )
                con.table("lugares_por_categoria").put(
                    clave(lugar.categoria.id, lugar.id),
                    a_celdas({"nombre": lugar.nombre.lower(), "id_barrio": lugar.barrio.id}),
                )
                if gh:
                    con.table("lugares_por_geohash").put(
                        f"{gh}#{pad(lugar.id)}".encode(),
                        a_celdas({"lat": lugar.latitud, "lon": lugar.longitud}),
                    )
                con.close()
        except Exception as e:
            raise MotorNoDisponible(f"No se pudo actualizar la proyección HBase: {e}") from e

    def desactivar_lugar(self, id_lugar: int) -> None:
        try:
            with self.traza.medir(f"HBASE DELETE PROJECT lugar {id_lugar}"):
                con = self._conexion()
                principal = con.table("lugares")
                anterior = de_celdas(principal.row(clave(id_lugar)))
                if anterior:
                    con.table("lugares_por_barrio").delete(clave(int(anterior["id_barrio"]), id_lugar))
                    con.table("lugares_por_categoria").delete(clave(int(anterior["id_categoria"]), id_lugar))
                    if anterior.get("geohash"):
                        con.table("lugares_por_geohash").delete(
                            f"{anterior['geohash']}#{pad(id_lugar)}".encode())
                    principal.delete(clave(id_lugar))
                con.close()
        except Exception as e:
            raise MotorNoDisponible(f"No se pudo actualizar la proyección HBase: {e}") from e

    def sincronizar_usuario(self, usuario: Usuario) -> None:
        try:
            with self.traza.medir(f"HBASE PROJECT usuario {usuario.id}"):
                con = self._conexion()
                con.table("usuarios").put(clave(usuario.id), a_celdas({
                    "nombre_usuario": usuario.nombre_usuario, "nombre": usuario.nombre,
                    "email": usuario.email, "id_barrio": usuario.barrio.id if usuario.barrio else None,
                    "barrio": usuario.barrio.nombre if usuario.barrio else None,
                    "comuna": usuario.barrio.comuna if usuario.barrio else None,
                    "fecha_alta": usuario.fecha_alta,
                }))
                con.table("usuarios_por_nombre").put(
                    usuario.nombre_usuario.encode(), a_celdas({"id": usuario.id}))
                con.close()
        except Exception as e:
            raise MotorNoDisponible(f"No se pudo actualizar la proyección HBase: {e}") from e
