"""Implementación de la persistencia sobre MySQL (modelo normalizado, SQL explícito)."""

import re
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError, OperationalError

from app.config import settings
from app.dominio import (
    Barrio, BarrioVisitado, Categoria, Checkin, CheckinCambios, CheckinIn, FiltroLugares,
    ItemRanking, Lugar, LugarCercano, LugarIn, Pagina, Pasaporte, Ref, Usuario, UsuarioIn,
)
from app.persistencia.base import (
    Conflicto, Invalido, MotorNoDisponible, NoEncontrado, Persistencia, RepoCatalogo,
    RepoCheckins, RepoConsultas, RepoLugares, RepoUsuarios, Traza,
)

_engine = sa.create_engine(settings.mysql_url, pool_pre_ping=True, pool_recycle=1800)

# Códigos de error de MySQL
ER_DUP_ENTRY = 1062
ER_ROW_IS_REFERENCED = 1451
ER_NO_REFERENCED_ROW = 1452


class _BaseMySQL:
    def __init__(self, traza: Traza):
        self.traza = traza

    def _ejecutar(self, sql: str, params: dict | None = None, escribir: bool = False):
        """Ejecuta SQL, registra la sentencia en la traza y devuelve las filas como dicts."""
        texto = re.sub(r"\s+", " ", sql).strip()
        try:
            with self.traza.medir(texto):
                ctx = _engine.begin() if escribir else _engine.connect()
                with ctx as con:
                    res = con.execute(sa.text(sql), params or {})
                    if res.returns_rows:
                        return [dict(r._mapping) for r in res]
                    return res
        except OperationalError as e:
            raise MotorNoDisponible(f"MySQL no disponible: {e.orig}") from e
        except IntegrityError as e:
            codigo = e.orig.args[0] if e.orig and e.orig.args else None
            if codigo == ER_DUP_ENTRY:
                raise Conflicto("Ya existe un registro con esos datos únicos") from e
            if codigo == ER_ROW_IS_REFERENCED:
                raise Conflicto("El registro tiene datos relacionados y no se puede borrar") from e
            if codigo == ER_NO_REFERENCED_ROW:
                raise Invalido("Se referencia un registro que no existe") from e
            raise


# ---------------------------------------------------------------- catálogo

class CatalogoMySQL(_BaseMySQL, RepoCatalogo):
    def barrios(self) -> list[Barrio]:
        filas = self._ejecutar("SELECT id_barrio, nombre, id_comuna FROM barrio ORDER BY nombre")
        return [Barrio(id=f["id_barrio"], nombre=f["nombre"], comuna=f["id_comuna"]) for f in filas]

    def categorias(self) -> list[Categoria]:
        filas = self._ejecutar("""
            SELECT c.id_categoria, c.nombre, t.nombre AS tipo
            FROM categoria c JOIN tipo_lugar t ON t.id_tipo = c.id_tipo
            ORDER BY t.nombre, c.nombre""")
        return [Categoria(id=f["id_categoria"], nombre=f["nombre"], tipo=f["tipo"]) for f in filas]


# ---------------------------------------------------------------- lugares

_SELECT_LUGAR = """
    SELECT l.id_lugar, l.nombre, l.direccion, l.latitud, l.longitud,
           c.id_categoria, c.nombre AS categoria, t.nombre AS tipo,
           b.id_barrio, b.nombre AS barrio, b.id_comuna, f.nombre AS fuente
    FROM lugar l
    JOIN categoria c  ON c.id_categoria = l.id_categoria
    JOIN tipo_lugar t ON t.id_tipo = c.id_tipo
    JOIN barrio b     ON b.id_barrio = l.id_barrio
    LEFT JOIN fuente f ON f.id_fuente = l.id_fuente
"""


def _a_lugar(f: dict) -> Lugar:
    return Lugar(
        id=f["id_lugar"], nombre=f["nombre"], direccion=f["direccion"],
        latitud=float(f["latitud"]) if f["latitud"] is not None else None,
        longitud=float(f["longitud"]) if f["longitud"] is not None else None,
        categoria=Categoria(id=f["id_categoria"], nombre=f["categoria"], tipo=f["tipo"]),
        barrio=Barrio(id=f["id_barrio"], nombre=f["barrio"], comuna=f["id_comuna"]),
        fuente=f["fuente"],
    )


class LugaresMySQL(_BaseMySQL, RepoLugares):
    def listar(self, filtro: FiltroLugares, limite: int, cursor: str | None) -> Pagina[Lugar]:
        condiciones, params = [], {"lim": limite + 1}
        if filtro.id_barrio is not None:
            condiciones.append("l.id_barrio = :barrio")
            params["barrio"] = filtro.id_barrio
        if filtro.id_categoria is not None:
            condiciones.append("l.id_categoria = :categoria")
            params["categoria"] = filtro.id_categoria
        if filtro.q:
            condiciones.append("l.nombre LIKE :q")
            params["q"] = f"%{filtro.q}%"
        if cursor:
            condiciones.append("l.id_lugar > :cursor")
            params["cursor"] = int(cursor)
        where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
        filas = self._ejecutar(f"{_SELECT_LUGAR} {where} ORDER BY l.id_lugar LIMIT :lim", params)
        items = [_a_lugar(f) for f in filas[:limite]]
        siguiente = str(items[-1].id) if len(filas) > limite else None
        return Pagina(items=items, siguiente_cursor=siguiente)

    def obtener(self, id_lugar: int) -> Lugar:
        filas = self._ejecutar(f"{_SELECT_LUGAR} WHERE l.id_lugar = :id", {"id": id_lugar})
        if not filas:
            raise NoEncontrado(f"No existe el lugar {id_lugar}")
        return _a_lugar(filas[0])

    def crear(self, datos: LugarIn) -> Lugar:
        res = self._ejecutar("""
            INSERT INTO lugar (nombre, direccion, latitud, longitud, id_categoria, id_barrio)
            VALUES (:nombre, :direccion, :latitud, :longitud, :id_categoria, :id_barrio)""",
            datos.model_dump(), escribir=True)
        return self.obtener(res.lastrowid)

    def actualizar(self, id_lugar: int, datos: LugarIn) -> Lugar:
        self.obtener(id_lugar)
        self._ejecutar("""
            UPDATE lugar SET nombre = :nombre, direccion = :direccion, latitud = :latitud,
                   longitud = :longitud, id_categoria = :id_categoria, id_barrio = :id_barrio
            WHERE id_lugar = :id""", {**datos.model_dump(), "id": id_lugar}, escribir=True)
        return self.obtener(id_lugar)

    def eliminar(self, id_lugar: int) -> None:
        # La FK checkin.id_lugar es ON DELETE RESTRICT: si tiene check-ins, MySQL rechaza el DELETE.
        res = self._ejecutar("DELETE FROM lugar WHERE id_lugar = :id", {"id": id_lugar}, escribir=True)
        if res.rowcount == 0:
            raise NoEncontrado(f"No existe el lugar {id_lugar}")

    def cercanos(self, lat: float, lon: float, radio_m: float, limite: int) -> list[LugarCercano]:
        # Primero un "bounding box" (usa índices sobre latitud/longitud) y después la distancia exacta.
        dlat = radio_m / 111_320
        dlon = radio_m / (111_320 * 0.83)  # cos(-34°) ≈ 0.83
        filas = self._ejecutar(f"""
            SELECT * FROM (
                SELECT x.*, ST_Distance_Sphere(POINT(x.longitud, x.latitud), POINT(:lon, :lat)) AS distancia
                FROM ({_SELECT_LUGAR}
                      WHERE l.latitud BETWEEN :lat_min AND :lat_max
                        AND l.longitud BETWEEN :lon_min AND :lon_max) x
            ) d
            WHERE d.distancia <= :radio
            ORDER BY d.distancia
            LIMIT :lim""", {
            "lat": lat, "lon": lon, "radio": radio_m, "lim": limite,
            "lat_min": lat - dlat, "lat_max": lat + dlat, "lon_min": lon - dlon, "lon_max": lon + dlon,
        })
        return [LugarCercano(lugar=_a_lugar(f), distancia_m=round(f["distancia"], 1)) for f in filas]


# ---------------------------------------------------------------- usuarios

_SELECT_USUARIO = """
    SELECT u.id_usuario, u.nombre_usuario, u.nombre, u.email, u.fecha_alta,
           b.id_barrio, b.nombre AS barrio, b.id_comuna
    FROM usuario u LEFT JOIN barrio b ON b.id_barrio = u.id_barrio
"""


def _a_usuario(f: dict) -> Usuario:
    barrio = (Barrio(id=f["id_barrio"], nombre=f["barrio"], comuna=f["id_comuna"])
              if f["id_barrio"] is not None else None)
    return Usuario(id=f["id_usuario"], nombre_usuario=f["nombre_usuario"], nombre=f["nombre"],
                   email=f["email"], barrio=barrio, fecha_alta=f["fecha_alta"])


class UsuariosMySQL(_BaseMySQL, RepoUsuarios):
    def listar(self, limite: int, cursor: str | None) -> Pagina[Usuario]:
        where = "WHERE u.id_usuario > :cursor" if cursor else ""
        filas = self._ejecutar(f"{_SELECT_USUARIO} {where} ORDER BY u.id_usuario LIMIT :lim",
                               {"cursor": int(cursor) if cursor else 0, "lim": limite + 1})
        items = [_a_usuario(f) for f in filas[:limite]]
        return Pagina(items=items, siguiente_cursor=str(items[-1].id) if len(filas) > limite else None)

    def obtener(self, id_usuario: int) -> Usuario:
        filas = self._ejecutar(f"{_SELECT_USUARIO} WHERE u.id_usuario = :id", {"id": id_usuario})
        if not filas:
            raise NoEncontrado(f"No existe el usuario {id_usuario}")
        return _a_usuario(filas[0])

    def crear(self, datos: UsuarioIn) -> Usuario:
        res = self._ejecutar("""
            INSERT INTO usuario (nombre_usuario, nombre, email, id_barrio, fecha_alta)
            VALUES (:nombre_usuario, :nombre, :email, :id_barrio, NOW())""",
            datos.model_dump(), escribir=True)
        return self.obtener(res.lastrowid)


# ---------------------------------------------------------------- check-ins

_SELECT_CHECKIN = """
    SELECT ch.id_checkin, ch.fecha_hora, ch.puntaje, ch.comentario,
           u.id_usuario, u.nombre_usuario, l.id_lugar, l.nombre AS nombre_lugar
    FROM checkin ch
    JOIN usuario u ON u.id_usuario = ch.id_usuario
    JOIN lugar l   ON l.id_lugar = ch.id_lugar
"""


def _a_checkin(f: dict) -> Checkin:
    return Checkin(
        id=f["id_checkin"], fecha_hora=f["fecha_hora"], puntaje=f["puntaje"], comentario=f["comentario"],
        usuario=Ref(id=f["id_usuario"], nombre=f["nombre_usuario"]),
        lugar=Ref(id=f["id_lugar"], nombre=f["nombre_lugar"]),
    )


class CheckinsMySQL(_BaseMySQL, RepoCheckins):
    def obtener(self, id_checkin: int) -> Checkin:
        filas = self._ejecutar(f"{_SELECT_CHECKIN} WHERE ch.id_checkin = :id", {"id": id_checkin})
        if not filas:
            raise NoEncontrado(f"No existe el check-in {id_checkin}")
        return _a_checkin(filas[0])

    def crear(self, datos: CheckinIn) -> Checkin:
        params = datos.model_dump()
        params["fecha_hora"] = datos.fecha_hora or datetime.now().replace(microsecond=0)
        res = self._ejecutar("""
            INSERT INTO checkin (id_usuario, id_lugar, fecha_hora, puntaje, comentario)
            VALUES (:id_usuario, :id_lugar, :fecha_hora, :puntaje, :comentario)""",
            params, escribir=True)
        return self.obtener(res.lastrowid)

    def actualizar(self, id_checkin: int, cambios: CheckinCambios) -> Checkin:
        self.obtener(id_checkin)
        self._ejecutar("UPDATE checkin SET puntaje = :puntaje, comentario = :comentario WHERE id_checkin = :id",
                       {**cambios.model_dump(), "id": id_checkin}, escribir=True)
        return self.obtener(id_checkin)

    def eliminar(self, id_checkin: int) -> None:
        res = self._ejecutar("DELETE FROM checkin WHERE id_checkin = :id", {"id": id_checkin}, escribir=True)
        if res.rowcount == 0:
            raise NoEncontrado(f"No existe el check-in {id_checkin}")

    def _listar(self, columna: str, valor: int, limite: int, cursor: str | None) -> Pagina[Checkin]:
        params = {"valor": valor, "lim": limite + 1}
        condicion_cursor = ""
        if cursor:
            fecha, id_c = cursor.split("|")
            condicion_cursor = "AND (ch.fecha_hora, ch.id_checkin) < (:c_fecha, :c_id)"
            params.update(c_fecha=fecha, c_id=int(id_c))
        filas = self._ejecutar(f"""{_SELECT_CHECKIN}
            WHERE ch.{columna} = :valor {condicion_cursor}
            ORDER BY ch.fecha_hora DESC, ch.id_checkin DESC LIMIT :lim""", params)
        items = [_a_checkin(f) for f in filas[:limite]]
        siguiente = None
        if len(filas) > limite:
            ultimo = items[-1]
            siguiente = f"{ultimo.fecha_hora.isoformat(sep=' ')}|{ultimo.id}"
        return Pagina(items=items, siguiente_cursor=siguiente)

    def de_lugar(self, id_lugar: int, limite: int, cursor: str | None) -> Pagina[Checkin]:
        return self._listar("id_lugar", id_lugar, limite, cursor)

    def de_usuario(self, id_usuario: int, limite: int, cursor: str | None) -> Pagina[Checkin]:
        return self._listar("id_usuario", id_usuario, limite, cursor)


# ---------------------------------------------------------------- consultas complejas

class ConsultasMySQL(_BaseMySQL, RepoConsultas):
    def ranking_barrio(self, id_barrio: int, anio: int, mes: int, top: int) -> list[ItemRanking]:
        inicio = datetime(anio, mes, 1)
        fin = datetime(anio + (mes == 12), mes % 12 + 1, 1)
        filas = self._ejecutar("""
            WITH conteo AS (
                SELECT l.id_lugar, l.nombre, c.nombre AS categoria, COUNT(*) AS checkins
                FROM checkin ch
                JOIN lugar l     ON l.id_lugar = ch.id_lugar
                JOIN categoria c ON c.id_categoria = l.id_categoria
                WHERE l.id_barrio = :barrio
                  AND ch.fecha_hora >= :inicio AND ch.fecha_hora < :fin
                GROUP BY l.id_lugar, l.nombre, c.nombre
            )
            SELECT id_lugar, nombre, categoria, checkins,
                   RANK() OVER (ORDER BY checkins DESC) AS puesto
            FROM conteo
            ORDER BY puesto, nombre
            LIMIT :top""", {"barrio": id_barrio, "inicio": inicio, "fin": fin, "top": top})
        return [ItemRanking(puesto=f["puesto"], lugar=Ref(id=f["id_lugar"], nombre=f["nombre"]),
                            categoria=f["categoria"], checkins=f["checkins"]) for f in filas]

    def pasaporte(self, id_usuario: int) -> Pasaporte:
        usuario = UsuariosMySQL(self.traza).obtener(id_usuario)
        totales = self._ejecutar("""
            SELECT COUNT(*) AS total, COUNT(DISTINCT id_lugar) AS distintos
            FROM checkin WHERE id_usuario = :u""", {"u": id_usuario})[0]
        filas = self._ejecutar("""
            SELECT b.id_barrio, b.nombre, b.id_comuna, COUNT(ch.id_checkin) AS checkins
            FROM barrio b
            LEFT JOIN (checkin ch JOIN lugar l ON l.id_lugar = ch.id_lugar)
                   ON l.id_barrio = b.id_barrio AND ch.id_usuario = :u
            GROUP BY b.id_barrio, b.nombre, b.id_comuna
            ORDER BY checkins DESC, b.nombre""", {"u": id_usuario})
        visitados, faltantes = [], []
        for f in filas:
            barrio = Barrio(id=f["id_barrio"], nombre=f["nombre"], comuna=f["id_comuna"])
            if f["checkins"]:
                visitados.append(BarrioVisitado(barrio=barrio, checkins=f["checkins"]))
            else:
                faltantes.append(barrio)
        return Pasaporte(
            usuario=Ref(id=usuario.id, nombre=usuario.nombre_usuario),
            total_checkins=totales["total"], lugares_distintos=totales["distintos"],
            barrios_visitados=visitados, barrios_faltantes=faltantes,
            progreso=round(100 * len(visitados) / len(filas), 1) if filas else 0.0,
        )


def crear_persistencia_mysql() -> Persistencia:
    traza = Traza()
    return Persistencia(
        motor="mysql",
        catalogo=CatalogoMySQL(traza), lugares=LugaresMySQL(traza), usuarios=UsuariosMySQL(traza),
        checkins=CheckinsMySQL(traza), consultas=ConsultasMySQL(traza), traza=traza,
    )
