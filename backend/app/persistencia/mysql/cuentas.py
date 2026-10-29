"""Persistencia relacional de autenticacion y funciones propias de la aplicacion.

Estas operaciones son deliberadamente MySQL: requieren unicidad, relaciones,
permisos y moderacion transaccional. HBase se reserva para las lecturas de
actividad, historiales y contadores.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from app.dominio import (
    Barrio, Categoria, Lugar, Pagina, Ref, RevisionSugerencia, Sesion,
    SugerenciaLugar, SugerenciaLugarIn, Usuario, UsuarioCrear,
)
from app.persistencia.base import Conflicto, NoAutorizado, NoEncontrado, Prohibido, Traza
from app.persistencia.mysql.repos import (
    _BaseMySQL, _SELECT_LUGAR, _SELECT_USUARIO, _a_lugar, _a_usuario,
)

ITERACIONES = 390_000
DURACION_SESION_DIAS = 7


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERACIONES)
    return "pbkdf2_sha256${}${}${}".format(
        ITERACIONES,
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode(),
    )


def verificar_password(password: str, codificado: str) -> bool:
    try:
        algoritmo, iteraciones, salt_b64, digest_b64 = codificado.split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64)
        esperado = base64.urlsafe_b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iteraciones))
        return hmac.compare_digest(actual, esperado)
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


_SELECT_SUGERENCIA = """
    SELECT s.id_sugerencia, s.nombre, s.direccion, s.latitud, s.longitud,
           s.comentario, s.estado, s.fecha_alta, s.fecha_revision,
           s.motivo_revision, s.id_lugar_creado,
           u.id_usuario, u.nombre_usuario,
           c.id_categoria, c.nombre AS categoria, t.nombre AS tipo,
           b.id_barrio, b.nombre AS barrio, b.id_comuna,
           r.id_usuario AS id_revisor, r.nombre_usuario AS revisor
    FROM sugerencia_lugar s
    JOIN usuario u ON u.id_usuario = s.id_usuario
    JOIN categoria c ON c.id_categoria = s.id_categoria
    JOIN tipo_lugar t ON t.id_tipo = c.id_tipo
    LEFT JOIN barrio b ON b.id_barrio = s.id_barrio
    LEFT JOIN usuario r ON r.id_usuario = s.id_revisor
"""


def _a_sugerencia(f: dict) -> SugerenciaLugar:
    barrio = None
    if f["id_barrio"] is not None:
        barrio = Barrio(id=f["id_barrio"], nombre=f["barrio"], comuna=f["id_comuna"])
    revisor = None
    if f["id_revisor"] is not None:
        revisor = Ref(id=f["id_revisor"], nombre=f["revisor"])
    return SugerenciaLugar(
        id=f["id_sugerencia"],
        usuario=Ref(id=f["id_usuario"], nombre=f["nombre_usuario"]),
        nombre=f["nombre"], direccion=f["direccion"],
        latitud=float(f["latitud"]) if f["latitud"] is not None else None,
        longitud=float(f["longitud"]) if f["longitud"] is not None else None,
        categoria=Categoria(id=f["id_categoria"], nombre=f["categoria"], tipo=f["tipo"]),
        barrio=barrio, comentario=f["comentario"], estado=f["estado"],
        fecha_alta=f["fecha_alta"], revisor=revisor,
        fecha_revision=f["fecha_revision"], motivo_revision=f["motivo_revision"],
        id_lugar_creado=f["id_lugar_creado"],
    )


class CuentasMySQL(_BaseMySQL):
    def login(self, identificador: str, password: str) -> Sesion:
        filas = self._ejecutar(f"""{_SELECT_USUARIO}
            WHERE (u.nombre_usuario = :identificador OR u.email = :identificador)
            LIMIT 1""", {"identificador": identificador.strip().lower()})
        if not filas or not filas[0]["activo"] or not verificar_password(password, filas[0]["password_hash"]):
            raise NoAutorizado("Usuario o contraseña incorrectos")
        usuario = _a_usuario(filas[0])
        token = secrets.token_urlsafe(32)
        expiracion = datetime.now() + timedelta(days=DURACION_SESION_DIAS)
        self._ejecutar("""
            INSERT INTO sesion (id_usuario, token_hash, fecha_expiracion)
            VALUES (:usuario, :token, :expiracion)""",
            {"usuario": usuario.id, "token": _token_hash(token), "expiracion": expiracion}, escribir=True)
        return Sesion(token=token, usuario=usuario)

    def autenticar(self, token: str | None) -> Usuario:
        if not token:
            raise NoAutorizado("Iniciá sesión para continuar")
        filas = self._ejecutar(f"""{_SELECT_USUARIO}
            WHERE u.activo = TRUE AND u.id_usuario = (
                SELECT s.id_usuario FROM sesion s
                WHERE s.token_hash = :token AND s.revocada = FALSE
                  AND s.fecha_expiracion > NOW()
                LIMIT 1
            )""", {"token": _token_hash(token)})
        if not filas:
            raise NoAutorizado("La sesión no es válida o venció")
        return _a_usuario(filas[0])

    def logout(self, token: str) -> None:
        self._ejecutar("UPDATE sesion SET revocada = TRUE WHERE token_hash = :token",
                       {"token": _token_hash(token)}, escribir=True)

    def crear_usuario(self, datos: UsuarioCrear) -> Usuario:
        params = datos.model_dump(exclude={"password"})
        params["password_hash"] = hash_password(datos.password)
        res = self._ejecutar("""
            INSERT INTO usuario
                (nombre_usuario, nombre, email, password_hash, rol, id_barrio)
            VALUES
                (:nombre_usuario, :nombre, :email, :password_hash, :rol, :id_barrio)""",
            params, escribir=True)
        filas = self._ejecutar(f"{_SELECT_USUARIO} WHERE u.id_usuario = :id", {"id": res.lastrowid})
        return _a_usuario(filas[0])


class FavoritosMySQL(_BaseMySQL):
    def listar(self, id_usuario: int, limite: int, cursor: str | None) -> Pagina[Lugar]:
        condiciones = ["l.activo = TRUE", "l.id_lugar IN (SELECT id_lugar FROM favorito WHERE id_usuario = :usuario)"]
        params: dict = {"usuario": id_usuario, "lim": limite + 1}
        if cursor:
            condiciones.append("l.id_lugar > :cursor")
            params["cursor"] = int(cursor)
        filas = self._ejecutar(
            f"{_SELECT_LUGAR} WHERE {' AND '.join(condiciones)} ORDER BY l.id_lugar LIMIT :lim", params,
        )
        items = [_a_lugar(f) for f in filas[:limite]]
        siguiente = str(items[-1].id) if len(filas) > limite else None
        return Pagina(items=items, siguiente_cursor=siguiente)

    def agregar(self, id_usuario: int, id_lugar: int) -> None:
        lugar = self._ejecutar(
            "SELECT id_lugar FROM lugar WHERE id_lugar = :lugar AND activo = TRUE",
            {"lugar": id_lugar},
        )
        if not lugar:
            raise NoEncontrado(f"No existe el lugar {id_lugar}")
        self._ejecutar("""
            INSERT IGNORE INTO favorito (id_usuario, id_lugar)
            VALUES (:usuario, :lugar)""",
            {"usuario": id_usuario, "lugar": id_lugar}, escribir=True)

    def quitar(self, id_usuario: int, id_lugar: int) -> None:
        self._ejecutar("DELETE FROM favorito WHERE id_usuario = :usuario AND id_lugar = :lugar",
                       {"usuario": id_usuario, "lugar": id_lugar}, escribir=True)

    def contiene(self, id_usuario: int, id_lugar: int) -> bool:
        filas = self._ejecutar("""
            SELECT EXISTS(SELECT 1 FROM favorito WHERE id_usuario = :usuario AND id_lugar = :lugar) AS valor""",
            {"usuario": id_usuario, "lugar": id_lugar})
        return bool(filas[0]["valor"])


class SugerenciasMySQL(_BaseMySQL):
    def crear(self, id_usuario: int, datos: SugerenciaLugarIn) -> SugerenciaLugar:
        params = datos.model_dump()
        params["usuario"] = id_usuario
        res = self._ejecutar("""
            INSERT INTO sugerencia_lugar
                (id_usuario, nombre, direccion, latitud, longitud, id_categoria, id_barrio, comentario)
            VALUES
                (:usuario, :nombre, :direccion, :latitud, :longitud, :id_categoria, :id_barrio, :comentario)""",
            params, escribir=True)
        return self.obtener(res.lastrowid)

    def obtener(self, id_sugerencia: int) -> SugerenciaLugar:
        filas = self._ejecutar(f"{_SELECT_SUGERENCIA} WHERE s.id_sugerencia = :id", {"id": id_sugerencia})
        if not filas:
            raise NoEncontrado(f"No existe la sugerencia {id_sugerencia}")
        return _a_sugerencia(filas[0])

    def listar(self, usuario: Usuario, estado: str | None = None) -> list[SugerenciaLugar]:
        condiciones, params = [], {}
        if usuario.rol != "admin":
            condiciones.append("s.id_usuario = :usuario")
            params["usuario"] = usuario.id
        if estado:
            condiciones.append("s.estado = :estado")
            params["estado"] = estado
        where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
        filas = self._ejecutar(f"{_SELECT_SUGERENCIA} {where} ORDER BY s.fecha_alta DESC", params)
        return [_a_sugerencia(f) for f in filas]

    def revisar(self, id_sugerencia: int, admin: Usuario, revision: RevisionSugerencia) -> SugerenciaLugar:
        if admin.rol != "admin":
            raise Prohibido("Solo un administrador puede revisar sugerencias")
        sugerencia = self.obtener(id_sugerencia)
        if sugerencia.estado != "pendiente":
            raise Conflicto("La sugerencia ya fue revisada")
        id_lugar = None
        estado = "rechazada"
        if revision.aprobar:
            res = self._ejecutar("""
                INSERT INTO lugar (nombre, direccion, latitud, longitud, id_categoria, id_barrio)
                SELECT nombre, direccion, latitud, longitud, id_categoria, id_barrio
                FROM sugerencia_lugar WHERE id_sugerencia = :id AND estado = 'pendiente'""",
                {"id": id_sugerencia}, escribir=True)
            id_lugar = res.lastrowid
            estado = "aprobada"
        self._ejecutar("""
            UPDATE sugerencia_lugar
            SET estado = :estado, id_revisor = :revisor, fecha_revision = NOW(),
                motivo_revision = :motivo, id_lugar_creado = :lugar
            WHERE id_sugerencia = :id AND estado = 'pendiente'""",
            {"estado": estado, "revisor": admin.id, "motivo": revision.motivo,
             "lugar": id_lugar, "id": id_sugerencia}, escribir=True)
        return self.obtener(id_sugerencia)


def crear_servicios_mysql(traza: Traza | None = None):
    traza = traza or Traza()
    return CuentasMySQL(traza), FavoritosMySQL(traza), SugerenciasMySQL(traza)
