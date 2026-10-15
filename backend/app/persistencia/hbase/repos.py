"""Implementación de la persistencia sobre HBase (modelo desnormalizado, orientado a consultas).

Row keys (ver claves.py):
  catalogo               barrio#<idBarrio> | categoria#<idCategoria>
  lugares                <idLugar>
  lugares_por_barrio     <idBarrio>#<idLugar>
  lugares_por_categoria  <idCategoria>#<idLugar>
  lugares_por_geohash    <geohash6>#<idLugar>
  usuarios               <idUsuario>
  usuarios_por_nombre    <nombre_usuario>
  checkins               <idCheckin>
  checkins_por_lugar     <idLugar>#<revTs>#<idCheckin>
  checkins_por_usuario   <idUsuario>#<revTs>#<idCheckin>
  stats_lugar            <idLugar>   (m:<yyyyMM> y t:total son contadores)
  secuencias             lugar | usuario | checkin   (c:valor es contador)

HBase no tiene joins, índices secundarios, FKs ni restricciones UNIQUE: todo eso lo
resuelve este módulo (tablas índice, validaciones y escrituras múltiples).
"""

import unicodedata
from collections import Counter
from datetime import datetime

import happybase
from thriftpy2.thrift import TException

from app.config import settings
from app.dominio import (
    Barrio, BarrioVisitado, Categoria, Checkin, CheckinCambios, CheckinIn, FiltroLugares,
    ItemRanking, Lugar, LugarCercano, LugarIn, Pagina, Pasaporte, Ref, Usuario, UsuarioIn,
)
from app.persistencia.base import (
    Conflicto, Invalido, MotorNoDisponible, NoEncontrado, Persistencia, RepoCatalogo,
    RepoCheckins, RepoConsultas, RepoLugares, RepoUsuarios, Traza,
)
from app.persistencia.hbase import geohash
from app.persistencia.hbase.claves import (
    a_celdas, clave, de_celdas, fin_de_prefijo, leer_contador, pad, prefijo, rev_ts,
)

_pool: happybase.ConnectionPool | None = None


def _obtener_pool() -> happybase.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = happybase.ConnectionPool(size=4, host=settings.hbase_host, port=settings.hbase_port)
    return _pool


def _con(fn):
    """Ejecuta fn(conexion). Reintenta una vez si el Thrift server cerró la conexión."""
    for intento in (1, 2):
        try:
            with _obtener_pool().connection() as conexion:
                return fn(conexion)
        except (TException, OSError) as e:
            if intento == 2:
                raise MotorNoDisponible(f"HBase no disponible: {e}") from e


def orden_texto(s: str) -> str:
    """Clave de orden sin tildes ni mayúsculas (igual criterio que la collation utf8mb4_0900_ai_ci de MySQL)."""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).casefold()


def _filtro_columna(columna: str, comparador: str, valor: str) -> str:
    valor = valor.replace("'", "''")
    return f"SingleColumnValueFilter('d', '{columna}', =, '{comparador}:{valor}', true, true)"


class _BaseHBase:
    def __init__(self, traza: Traza):
        self.traza = traza

    # -- operaciones básicas, todas registradas en la traza

    def _get(self, tabla: str, fila: bytes, columnas: list[bytes] | None = None) -> dict:
        with self.traza.medir(f"GET {tabla} row='{fila.decode()}'"):
            return _con(lambda c: c.table(tabla).row(fila, columns=columnas))

    def _multiget(self, tabla: str, filas: list[bytes], columnas: list[bytes] | None = None) -> list:
        if not filas:
            return []
        with self.traza.medir(f"MULTI-GET {tabla} ({len(filas)} rows)"):
            return _con(lambda c: c.table(tabla).rows(filas, columns=columnas))

    def _scan(self, tabla: str, prefijo_: bytes | None = None, desde: bytes | None = None,
              limite: int | None = None, filtro: str | None = None,
              columnas: list[bytes] | None = None) -> list:
        inicio = desde or prefijo_
        fin = fin_de_prefijo(prefijo_) if prefijo_ else None
        desc = f"SCAN {tabla}"
        if prefijo_:
            desc += f" prefix='{prefijo_.decode()}'"
        if desde:
            desc += f" desde='{desde.decode(errors='replace').rstrip(chr(0))}'"
        if filtro:
            desc += f" filter={filtro}"
        if limite:
            desc += f" limit={limite}"
        with self.traza.medir(desc):
            return _con(lambda c: list(c.table(tabla).scan(
                row_start=inicio, row_stop=fin, limit=limite, filter=filtro, columns=columnas)))

    def _put(self, tabla: str, fila: bytes, datos: dict[bytes, bytes]) -> None:
        with self.traza.medir(f"PUT {tabla} row='{fila.decode()}' ({len(datos)} celdas)"):
            _con(lambda c: c.table(tabla).put(fila, datos))

    def _delete(self, tabla: str, fila: bytes, columnas: list[bytes] | None = None) -> None:
        desc = f"DELETE {tabla} row='{fila.decode()}'"
        if columnas:
            desc += f" columns={[x.decode() for x in columnas]}"
        with self.traza.medir(desc):
            _con(lambda c: c.table(tabla).delete(fila, columns=columnas))

    def _incrementar(self, tabla: str, fila: bytes, columna: bytes, valor: int = 1) -> int:
        with self.traza.medir(f"INCREMENT {tabla} row='{fila.decode()}' {columna.decode()} {valor:+d}"):
            return _con(lambda c: c.table(tabla).counter_inc(fila, columna, valor))

    def _nuevo_id(self, entidad: str) -> int:
        return self._incrementar("secuencias", entidad.encode(), b"c:valor")

    # -- lecturas compartidas

    def _barrio(self, id_barrio: int) -> Barrio:
        d = de_celdas(self._get("catalogo", clave("barrio", id_barrio)))
        if not d:
            raise Invalido(f"No existe el barrio {id_barrio}")
        return Barrio(id=id_barrio, nombre=d["nombre"], comuna=int(d["comuna"]))

    def _categoria(self, id_categoria: int) -> Categoria:
        d = de_celdas(self._get("catalogo", clave("categoria", id_categoria)))
        if not d:
            raise Invalido(f"No existe la categoría {id_categoria}")
        return Categoria(id=id_categoria, nombre=d["nombre"], tipo=d["tipo"])

    def _lugar_crudo(self, id_lugar: int) -> dict[str, str]:
        d = de_celdas(self._get("lugares", clave(id_lugar)))
        if not d:
            raise NoEncontrado(f"No existe el lugar {id_lugar}")
        return d


# ---------------------------------------------------------------- catálogo

class CatalogoHBase(_BaseHBase, RepoCatalogo):
    def barrios(self) -> list[Barrio]:
        filas = self._scan("catalogo", prefijo_=b"barrio#")
        barrios = [Barrio(id=int(k.split(b"#")[1]), nombre=d["nombre"], comuna=int(d["comuna"]))
                   for k, d in ((k, de_celdas(v)) for k, v in filas)]
        return sorted(barrios, key=lambda b: orden_texto(b.nombre))

    def categorias(self) -> list[Categoria]:
        filas = self._scan("catalogo", prefijo_=b"categoria#")
        cats = [Categoria(id=int(k.split(b"#")[1]), nombre=d["nombre"], tipo=d["tipo"])
                for k, d in ((k, de_celdas(v)) for k, v in filas)]
        return sorted(cats, key=lambda c: (c.tipo, orden_texto(c.nombre)))


# ---------------------------------------------------------------- lugares

def _a_lugar(id_lugar: int, d: dict[str, str]) -> Lugar:
    return Lugar(
        id=id_lugar, nombre=d["nombre"], direccion=d.get("direccion"),
        latitud=float(d["lat"]) if "lat" in d else None,
        longitud=float(d["lon"]) if "lon" in d else None,
        categoria=Categoria(id=int(d["id_categoria"]), nombre=d["categoria"], tipo=d["tipo"]),
        barrio=Barrio(id=int(d["id_barrio"]), nombre=d["barrio"], comuna=int(d["comuna"])),
        fuente=d.get("fuente"),
    )


class LugaresHBase(_BaseHBase, RepoLugares):
    def listar(self, filtro: FiltroLugares, limite: int, cursor: str | None) -> Pagina[Lugar]:
        # Elegimos la tabla según el filtro: cada filtro necesita su propia tabla índice.
        filtros = []
        if filtro.id_barrio is not None:
            tabla, pref = "lugares_por_barrio", prefijo(filtro.id_barrio)
            if filtro.id_categoria is not None:
                filtros.append(_filtro_columna("id_categoria", "binary", str(filtro.id_categoria)))
        elif filtro.id_categoria is not None:
            tabla, pref = "lugares_por_categoria", prefijo(filtro.id_categoria)
        else:
            tabla, pref = "lugares", None
        if filtro.q:
            filtros.append(_filtro_columna("nombre", "substring", filtro.q.lower()))

        desde = cursor.encode() + b"\x00" if cursor else None
        filas = self._scan(tabla, prefijo_=pref, desde=desde, limite=limite + 1,
                           filtro=" AND ".join(filtros) or None)
        hay_mas = len(filas) > limite
        filas = filas[:limite]

        if tabla == "lugares":
            items = [_a_lugar(int(k), de_celdas(v)) for k, v in filas]
        else:
            # La tabla índice solo tiene un resumen: traemos los lugares completos con un multi-get.
            ids = [int(k.split(b"#")[1]) for k, _ in filas]
            completos = dict(self._multiget("lugares", [clave(i) for i in ids]))
            items = [_a_lugar(i, de_celdas(completos[clave(i)])) for i in ids if clave(i) in completos]

        siguiente = filas[-1][0].decode() if hay_mas and filas else None
        return Pagina(items=items, siguiente_cursor=siguiente)

    def obtener(self, id_lugar: int) -> Lugar:
        return _a_lugar(id_lugar, self._lugar_crudo(id_lugar))

    def crear(self, datos: LugarIn) -> Lugar:
        # Validamos antes de consumir un ID de la secuencia.
        barrio, categoria = self._barrio(datos.id_barrio), self._categoria(datos.id_categoria)
        id_lugar = self._nuevo_id("lugar")
        return self._escribir(id_lugar, datos, barrio, categoria, fuente=None)

    def actualizar(self, id_lugar: int, datos: LugarIn) -> Lugar:
        anterior = self._lugar_crudo(id_lugar)
        barrio, categoria = self._barrio(datos.id_barrio), self._categoria(datos.id_categoria)
        self._borrar_indices(id_lugar, anterior)
        # Las columnas opcionales que quedan vacías hay que borrarlas explícitamente.
        sin_coords = datos.latitud is None or datos.longitud is None
        vacias = [f"d:{c}".encode() for c, vacia in
                  (("direccion", datos.direccion is None), ("lat", sin_coords), ("lon", sin_coords),
                   ("geohash", sin_coords))
                  if vacia and c in anterior]
        if vacias:
            self._delete("lugares", clave(id_lugar), vacias)
        # Nota: los check-ins guardan una copia de nombre_lugar; los anteriores conservan el nombre viejo.
        return self._escribir(id_lugar, datos, barrio, categoria, fuente=anterior.get("fuente"))

    def eliminar(self, id_lugar: int) -> None:
        anterior = self._lugar_crudo(id_lugar)
        # Sin FKs: la integridad referencial la verifica la aplicación.
        if self._scan("checkins_por_lugar", prefijo_=prefijo(id_lugar), limite=1):
            raise Conflicto("El registro tiene datos relacionados y no se puede borrar")
        self._borrar_indices(id_lugar, anterior)
        self._delete("lugares", clave(id_lugar))
        self._delete("stats_lugar", clave(id_lugar))

    def cercanos(self, lat: float, lon: float, radio_m: float, limite: int) -> list[LugarCercano]:
        precision = geohash.precision_para_radio(radio_m)
        candidatos = []
        for celda in geohash.celdas_alrededor(lat, lon, precision):
            # La celda (sin '#') es prefijo de todos los geohash6 que caen dentro de ella.
            for k, v in self._scan("lugares_por_geohash", prefijo_=celda.encode(),
                                   columnas=[b"d:lat", b"d:lon"]):
                d = de_celdas(v)
                dist = geohash.distancia_m(lat, lon, float(d["lat"]), float(d["lon"]))
                if dist <= radio_m:
                    candidatos.append((dist, int(k.split(b"#")[1])))
        candidatos.sort()
        candidatos = candidatos[:limite]
        completos = dict(self._multiget("lugares", [clave(i) for _, i in candidatos]))
        return [LugarCercano(lugar=_a_lugar(i, de_celdas(completos[clave(i)])), distancia_m=round(dist, 1))
                for dist, i in candidatos if clave(i) in completos]

    # -- helpers

    def _escribir(self, id_lugar: int, datos: LugarIn, barrio: Barrio, categoria: Categoria,
                  fuente: str | None) -> Lugar:
        tiene_coords = datos.latitud is not None and datos.longitud is not None
        gh = geohash.codificar(datos.latitud, datos.longitud, 6) if tiene_coords else None
        fila = {
            "nombre": datos.nombre, "direccion": datos.direccion,
            "lat": datos.latitud if tiene_coords else None, "lon": datos.longitud if tiene_coords else None,
            "geohash": gh,
            "id_categoria": categoria.id, "categoria": categoria.nombre, "tipo": categoria.tipo,
            "id_barrio": barrio.id, "barrio": barrio.nombre, "comuna": barrio.comuna,
            "fuente": fuente,
        }
        self._put("lugares", clave(id_lugar), a_celdas(fila))
        # Tablas índice (desnormalizadas): guardan lo necesario para filtrar sin ir a "lugares".
        nombre_min = datos.nombre.lower()
        self._put("lugares_por_barrio", clave(barrio.id, id_lugar),
                  a_celdas({"nombre": nombre_min, "id_categoria": categoria.id}))
        self._put("lugares_por_categoria", clave(categoria.id, id_lugar),
                  a_celdas({"nombre": nombre_min, "id_barrio": barrio.id}))
        if gh:
            self._put("lugares_por_geohash", f"{gh}#{pad(id_lugar)}".encode(),
                      a_celdas({"lat": datos.latitud, "lon": datos.longitud}))
        return _a_lugar(id_lugar, {k: str(v) for k, v in fila.items() if v is not None})

    def _borrar_indices(self, id_lugar: int, d: dict[str, str]) -> None:
        self._delete("lugares_por_barrio", clave(int(d["id_barrio"]), id_lugar))
        self._delete("lugares_por_categoria", clave(int(d["id_categoria"]), id_lugar))
        if "geohash" in d:
            self._delete("lugares_por_geohash", f"{d['geohash']}#{pad(id_lugar)}".encode())


# ---------------------------------------------------------------- usuarios

def _a_usuario(id_usuario: int, d: dict[str, str]) -> Usuario:
    barrio = (Barrio(id=int(d["id_barrio"]), nombre=d["barrio"], comuna=int(d["comuna"]))
              if "id_barrio" in d else None)
    return Usuario(id=id_usuario, nombre_usuario=d["nombre_usuario"], nombre=d["nombre"], email=d["email"],
                   barrio=barrio, fecha_alta=datetime.fromisoformat(d["fecha_alta"]))


class UsuariosHBase(_BaseHBase, RepoUsuarios):
    def listar(self, limite: int, cursor: str | None) -> Pagina[Usuario]:
        desde = cursor.encode() + b"\x00" if cursor else None
        filas = self._scan("usuarios", desde=desde, limite=limite + 1)
        items = [_a_usuario(int(k), de_celdas(v)) for k, v in filas[:limite]]
        siguiente = filas[limite - 1][0].decode() if len(filas) > limite else None
        return Pagina(items=items, siguiente_cursor=siguiente)

    def obtener(self, id_usuario: int) -> Usuario:
        d = de_celdas(self._get("usuarios", clave(id_usuario)))
        if not d:
            raise NoEncontrado(f"No existe el usuario {id_usuario}")
        return _a_usuario(id_usuario, d)

    def crear(self, datos: UsuarioIn) -> Usuario:
        # Sin UNIQUE: usamos una tabla índice por nombre_usuario y verificamos antes de escribir.
        # (No es atómico: dos altas simultáneas con el mismo nombre podrían pasar. Ver informe.)
        if self._get("usuarios_por_nombre", datos.nombre_usuario.encode()):
            raise Conflicto("Ya existe un registro con esos datos únicos")
        barrio = self._barrio(datos.id_barrio) if datos.id_barrio is not None else None
        id_usuario = self._nuevo_id("usuario")
        fila = {
            "nombre_usuario": datos.nombre_usuario, "nombre": datos.nombre, "email": datos.email,
            "id_barrio": barrio.id if barrio else None, "barrio": barrio.nombre if barrio else None,
            "comuna": barrio.comuna if barrio else None,
            "fecha_alta": datetime.now().replace(microsecond=0),
        }
        self._put("usuarios", clave(id_usuario), a_celdas(fila))
        self._put("usuarios_por_nombre", datos.nombre_usuario.encode(), a_celdas({"id": id_usuario}))
        return self.obtener(id_usuario)


# ---------------------------------------------------------------- check-ins

def _a_checkin(id_checkin: int, d: dict[str, str]) -> Checkin:
    return Checkin(
        id=id_checkin, fecha_hora=datetime.fromisoformat(d["fecha_hora"]),
        puntaje=int(d["puntaje"]) if "puntaje" in d else None, comentario=d.get("comentario"),
        usuario=Ref(id=int(d["id_usuario"]), nombre=d["nombre_usuario"]),
        lugar=Ref(id=int(d["id_lugar"]), nombre=d["nombre_lugar"]),
    )


class CheckinsHBase(_BaseHBase, RepoCheckins):
    def obtener(self, id_checkin: int) -> Checkin:
        return _a_checkin(id_checkin, self._crudo(id_checkin))

    def crear(self, datos: CheckinIn) -> Checkin:
        # Sin FKs: validamos a mano que existan el usuario y el lugar.
        usuario = de_celdas(self._get("usuarios", clave(datos.id_usuario), [b"d:nombre_usuario"]))
        if not usuario:
            raise Invalido("Se referencia un registro que no existe")
        try:
            lugar = self._lugar_crudo(datos.id_lugar)
        except NoEncontrado as e:
            raise Invalido("Se referencia un registro que no existe") from e

        fecha = datos.fecha_hora or datetime.now().replace(microsecond=0)
        id_checkin = self._nuevo_id("checkin")
        # Desnormalización: el mismo check-in se escribe en 3 tablas, cada una ordenada para una consulta.
        fila = a_celdas({
            "id_usuario": datos.id_usuario, "nombre_usuario": usuario["nombre_usuario"],
            "id_lugar": datos.id_lugar, "nombre_lugar": lugar["nombre"],
            "id_barrio": lugar["id_barrio"], "barrio": lugar["barrio"],
            "fecha_hora": fecha, "puntaje": datos.puntaje, "comentario": datos.comentario,
        })
        for tabla, k in self._claves(id_checkin, datos.id_usuario, datos.id_lugar, fecha):
            self._put(tabla, k, fila)
        # Contadores atómicos para los rankings (evitan recorrer todos los check-ins).
        self._incrementar("stats_lugar", clave(datos.id_lugar), f"m:{fecha:%Y%m}".encode())
        self._incrementar("stats_lugar", clave(datos.id_lugar), b"t:total")
        return self.obtener(id_checkin)

    def actualizar(self, id_checkin: int, cambios: CheckinCambios) -> Checkin:
        d = self._crudo(id_checkin)
        poner = a_celdas({"puntaje": cambios.puntaje, "comentario": cambios.comentario})
        borrar = [f"d:{c}".encode() for c, v in (("puntaje", cambios.puntaje), ("comentario", cambios.comentario))
                  if v is None and c in d]
        for tabla, k in self._claves_de(id_checkin, d):
            if poner:
                self._put(tabla, k, poner)
            if borrar:
                self._delete(tabla, k, borrar)
        return self.obtener(id_checkin)

    def eliminar(self, id_checkin: int) -> None:
        d = self._crudo(id_checkin)
        for tabla, k in self._claves_de(id_checkin, d):
            self._delete(tabla, k)
        fecha = datetime.fromisoformat(d["fecha_hora"])
        self._incrementar("stats_lugar", clave(int(d["id_lugar"])), f"m:{fecha:%Y%m}".encode(), -1)
        self._incrementar("stats_lugar", clave(int(d["id_lugar"])), b"t:total", -1)

    def de_lugar(self, id_lugar: int, limite: int, cursor: str | None) -> Pagina[Checkin]:
        return self._listar("checkins_por_lugar", id_lugar, limite, cursor)

    def de_usuario(self, id_usuario: int, limite: int, cursor: str | None) -> Pagina[Checkin]:
        return self._listar("checkins_por_usuario", id_usuario, limite, cursor)

    # -- helpers

    def _crudo(self, id_checkin: int) -> dict[str, str]:
        d = de_celdas(self._get("checkins", clave(id_checkin)))
        if not d:
            raise NoEncontrado(f"No existe el check-in {id_checkin}")
        return d

    @staticmethod
    def _claves(id_checkin: int, id_usuario: int, id_lugar: int, fecha: datetime) -> list[tuple[str, bytes]]:
        ts = rev_ts(fecha)
        return [
            ("checkins", clave(id_checkin)),
            ("checkins_por_lugar", clave(id_lugar, ts, id_checkin)),
            ("checkins_por_usuario", clave(id_usuario, ts, id_checkin)),
        ]

    def _claves_de(self, id_checkin: int, d: dict[str, str]) -> list[tuple[str, bytes]]:
        return self._claves(id_checkin, int(d["id_usuario"]), int(d["id_lugar"]),
                            datetime.fromisoformat(d["fecha_hora"]))

    def _listar(self, tabla: str, id_: int, limite: int, cursor: str | None) -> Pagina[Checkin]:
        desde = cursor.encode() + b"\x00" if cursor else None
        filas = self._scan(tabla, prefijo_=prefijo(id_), desde=desde, limite=limite + 1)
        items = [_a_checkin(int(k.split(b"#")[2]), de_celdas(v)) for k, v in filas[:limite]]
        siguiente = filas[limite - 1][0].decode() if len(filas) > limite else None
        return Pagina(items=items, siguiente_cursor=siguiente)


# ---------------------------------------------------------------- consultas complejas

class ConsultasHBase(_BaseHBase, RepoConsultas):
    def ranking_barrio(self, id_barrio: int, anio: int, mes: int, top: int) -> list[ItemRanking]:
        # 1) lugares del barrio (tabla índice)  2) contador del mes de cada uno  3) orden en la app
        lugares = self._scan("lugares_por_barrio", prefijo_=prefijo(id_barrio))
        ids = [int(k.split(b"#")[1]) for k, _ in lugares]
        columna = f"m:{anio}{mes:02d}".encode()
        contadores = dict(self._multiget("stats_lugar", [clave(i) for i in ids], [columna]))
        conteos = [(leer_contador(contadores.get(clave(i), {}).get(columna)), i) for i in ids]
        conteos = sorted((c for c in conteos if c[0] > 0), key=lambda x: -x[0])

        completos = dict(self._multiget("lugares", [clave(i) for _, i in conteos[:top]],
                                        [b"d:nombre", b"d:categoria"]))
        ranking, puesto_anterior, cant_anterior = [], 0, None
        for posicion, (cant, i) in enumerate(conteos[:top], start=1):
            puesto = puesto_anterior if cant == cant_anterior else posicion  # mismo criterio que RANK()
            d = de_celdas(completos.get(clave(i), {}))
            ranking.append(ItemRanking(puesto=puesto, lugar=Ref(id=i, nombre=d.get("nombre", "?")),
                                       categoria=d.get("categoria", "?"), checkins=cant))
            puesto_anterior, cant_anterior = puesto, cant
        return sorted(ranking, key=lambda r: (r.puesto, orden_texto(r.lugar.nombre)))

    def pasaporte(self, id_usuario: int) -> Pasaporte:
        usuario = UsuariosHBase(self.traza).obtener(id_usuario)
        filas = self._scan("checkins_por_usuario", prefijo_=prefijo(id_usuario),
                           columnas=[b"d:id_lugar", b"d:id_barrio"])
        por_barrio, lugares = Counter(), set()
        for _, v in filas:
            d = de_celdas(v)
            por_barrio[int(d["id_barrio"])] += 1
            lugares.add(d["id_lugar"])
        barrios = CatalogoHBase(self.traza).barrios()
        visitados = sorted(
            (BarrioVisitado(barrio=b, checkins=por_barrio[b.id]) for b in barrios if por_barrio[b.id]),
            key=lambda x: (-x.checkins, orden_texto(x.barrio.nombre)))
        faltantes = [b for b in barrios if not por_barrio[b.id]]
        return Pasaporte(
            usuario=Ref(id=usuario.id, nombre=usuario.nombre_usuario),
            total_checkins=len(filas), lugares_distintos=len(lugares),
            barrios_visitados=visitados, barrios_faltantes=faltantes,
            progreso=round(100 * len(visitados) / len(barrios), 1) if barrios else 0.0,
        )


def crear_persistencia_hbase() -> Persistencia:
    traza = Traza()
    return Persistencia(
        motor="hbase",
        catalogo=CatalogoHBase(traza), lugares=LugaresHBase(traza), usuarios=UsuariosHBase(traza),
        checkins=CheckinsHBase(traza), consultas=ConsultasHBase(traza), traza=traza,
    )
