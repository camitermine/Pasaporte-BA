# Pasaporte BA — Documento de diseño

> Documento vivo. Es el **contrato** entre la parte de bases de datos y la parte de backend/app.
> Si cambia algo de las secciones 4 a 6, hay que actualizarlo acá antes de tocar el código.

## 1. Resumen

App mobile donde los usuarios hacen **check-in** en lugares de la Ciudad de Buenos Aires: bares, cafés, restaurantes, espacios culturales, monumentos y murales. Pueden ver los lugares por barrio y categoría, sus check-ins y rankings de los lugares más visitados.

El foco del TP está en las bases de datos:
- **MySQL 8**: modelo normalizado (mínimo 3FN) a partir de los datasets de BA Data.
- **HBase**: el mismo dominio, modelado de forma desnormalizada según los patrones de acceso.
- **Backend polimórfico**: la misma operación (por ejemplo `listar_lugares()`) se ejecuta contra MySQL o contra HBase, y el motor se elige por configuración o por request.

## 2. Responsabilidades

| Parte | Responsable | Entregables |
|---|---|---|
| Análisis y normalización de datasets, DER, modelo relacional, scripts SQL, diseño y scripts HBase, carga de datos (reales y sintéticos) | Grupo (bases) | `database/`, DER, secciones 3 a 8 del informe |
| Backend FastAPI (API, capa de persistencia polimórfica) | IA | `backend/` |
| App mobile Expo | IA | `frontend/` |
| `docker-compose.yml`, README | Compartido | raíz del repo |

## 3. Arquitectura

```
App mobile (Expo / React Native)
        │  HTTP + JSON   (header X-Motor: mysql | hbase)
        ▼
Backend FastAPI
  ├── api/            rutas HTTP, validación (no sabe qué motor hay abajo)
  ├── dominio/        modelos: Lugar, Checkin, Usuario, Barrio, Categoria
  └── persistencia/
        ├── base.py   interfaces (repositorios abstractos)
        ├── mysql/    implementación con SQLAlchemy + PyMySQL
        └── hbase/    implementación con happybase (Thrift)
        ▼                      ▼
     MySQL 8               HBase (+ Thrift server)
```

- La app **nunca** accede directo a las bases.
- **Selección de motor**: la variable de entorno `MOTOR_DB` define el motor por defecto, y el header `X-Motor` puede pisarla en cada request. Así el selector de la app cambia de motor en vivo, sin reiniciar el backend.
- Cada respuesta incluye un bloque `meta` con el motor usado, el tiempo y las operaciones ejecutadas (SQL o get/scan/put de HBase). Es el "modo debug" que se muestra en la app y sirve para la presentación.

## 4. Modelo de dominio (lo que ve la API)

Estas son las entidades que devuelve la API. **Son iguales sin importar el motor.** Cómo se guardan en cada base es decisión del diseño de cada una (secciones 5 y 6).

| Entidad | Campos |
|---|---|
| **Barrio** | `id`, `nombre`, `comuna` (número 1–15) |
| **Categoria** | `id`, `nombre` (ej. "Bar", "Café", "Biblioteca", "Mural"), `tipo` ("gastronomia", "cultura", "patrimonio") |
| **Lugar** | `id`, `nombre`, `direccion`, `latitud`, `longitud`, `categoria` (objeto Categoria), `barrio` (objeto Barrio), `fuente` (dataset de origen) |
| **Usuario** | `id`, `nombre_usuario`, `nombre`, `email`, `barrio` (opcional), `fecha_alta` |
| **Checkin** | `id`, `usuario` (id + nombre_usuario), `lugar` (id + nombre), `fecha_hora`, `puntaje` (1–5, opcional), `comentario` (máx. 280, opcional) |

**IDs:** enteros. Los dos motores se cargan con los **mismos IDs** desde el mismo origen, para poder comparar resultados. Las altas nuevas generan el ID con `AUTO_INCREMENT` en MySQL y con un contador atómico (`incrementColumnValue`) en HBase.

### Alcance

- **Polimórfico (en los dos motores):** Lugar (CRUD completo), Checkin (CRUD completo), Usuario (listar, obtener, crear), Barrio y Categoria (solo lectura), y las consultas de la sección 7.
- **Extras opcionales, si sobra tiempo:** amistades, feed de amigos, rutas temáticas, insignias. Si se hacen, conviene que también existan en los dos motores, o que la app los oculte cuando el motor no los soporte.

## 5. MySQL — borrador del modelo relacional

> **Borrador para que lo ajustes.** El backend depende de los nombres de tablas y columnas, así que si cambiás algo avisá y actualizá esta sección.

```
comuna        (id_comuna PK [1..15])
barrio        (id_barrio PK, nombre UNIQUE NOT NULL, id_comuna FK → comuna)
tipo_lugar    (id_tipo PK, nombre UNIQUE)                      -- gastronomia / cultura / patrimonio
categoria     (id_categoria PK, nombre NOT NULL, id_tipo FK → tipo_lugar, UNIQUE(nombre, id_tipo))
fuente        (id_fuente PK, nombre, url, fecha_descarga)      -- dataset de origen
lugar         (id_lugar PK, nombre NOT NULL, direccion, latitud DECIMAL(9,6), longitud DECIMAL(9,6),
               ubicacion POINT SRID 4326 [+ SPATIAL INDEX, opcional],
               id_categoria FK, id_barrio FK, id_fuente FK, id_origen,
               UNIQUE(id_fuente, id_origen))
usuario       (id_usuario PK, nombre_usuario UNIQUE, nombre, email UNIQUE, id_barrio FK NULL, fecha_alta)
checkin       (id_checkin PK, id_usuario FK, id_lugar FK, fecha_hora NOT NULL,
               puntaje TINYINT NULL CHECK (puntaje BETWEEN 1 AND 5), comentario VARCHAR(280) NULL,
               INDEX(id_lugar, fecha_hora), INDEX(id_usuario, fecha_hora))
```

Notas para la normalización (informe, punto 1):
- En los CSV, barrio, comuna y categoría vienen repetidos como texto en cada fila. Sacarlos a sus propias tablas resuelve la redundancia y las anomalías de actualización.
- Barrio determina comuna (`barrio → comuna`). Tener la comuna en `lugar` sería una **dependencia transitiva** que rompe la 3FN. Por eso va en `barrio`.
- Cada dataset tiene columnas distintas, así que hay que unificarlos en `lugar` y dejar registrada la `fuente`.
- Charset `utf8mb4`, motor InnoDB.

**Borrado de un Lugar con check-ins:** propongo `ON DELETE RESTRICT`, y que la API devuelva `409 Conflict`. En HBase esa misma regla la valida la aplicación, lo que sirve como punto de comparación en el informe.

## 6. HBase — borrador del modelo

> **Borrador para que lo ajustes.** Los nombres de tablas, families y columnas son el contrato con el backend.

Convenciones:
- IDs con ceros a la izquierda en las row keys (`0000012345`) para que el orden lexicográfico coincida con el numérico.
- `revTs` = `Long.MAX_VALUE - timestamp_ms` (19 dígitos), para que los scans devuelvan primero lo más reciente.
- Column families con nombres cortos (`d` = datos).

| Tabla | Row key | Families / columnas | Para qué consulta |
|---|---|---|---|
| `lugares` | `idLugar` | `d:` nombre, direccion, lat, lon, id_categoria, categoria, tipo, id_barrio, barrio, comuna, fuente | Get por id; listado con scan |
| `lugares_por_barrio` | `idBarrio#idLugar` | `d:` nombre, categoria | Listar lugares de un barrio (índice secundario hecho a mano) |
| `lugares_por_categoria` | `idCategoria#idLugar` | `d:` nombre, barrio | Filtrar por categoría |
| `lugares_por_geohash` (opcional) | `geohash6#idLugar` | `d:` nombre, lat, lon | Cercanos: scan por prefijo de geohash |
| `checkins` | `idCheckin` | `d:` id_usuario, nombre_usuario, id_lugar, nombre_lugar, id_barrio, barrio, fecha_hora, puntaje, comentario | Get, update y delete por id |
| `checkins_por_lugar` | `idLugar#revTs#idCheckin` | `d:` (copia desnormalizada) | Últimos check-ins de un lugar |
| `checkins_por_usuario` | `idUsuario#revTs#idCheckin` | `d:` (copia desnormalizada) | Historial de un usuario |
| `stats_lugar` | `idLugar` | `m:yyyyMM` (contador), `t:total` (contador) | Ranking mensual sin recorrer check-ins |
| `usuarios` | `idUsuario` | `d:` nombre_usuario, nombre, email, id_barrio, barrio, comuna, fecha_alta | CRUD de usuarios |
| `usuarios_por_nombre` | `nombre_usuario` | `d:id` | Reemplaza al UNIQUE de MySQL (se verifica antes de insertar) |
| `catalogo` | `barrio#idBarrio`, `categoria#idCategoria` | `d:` nombre, comuna / tipo | Barrios y categorías |
| `secuencias` | `lugar`, `checkin`, `usuario` | `c:valor` (contador) | Generar IDs nuevos |

Puntos para el informe (punto 4: ventajas y limitaciones):
- Un check-in se escribe en 3 tablas más el contador (desnormalización intencional): la lectura es rápida, pero la escritura cuesta más y la consistencia queda a cargo de la app.
- Sin índices secundarios: cada filtro necesita su tabla índice, que hay que mantener al crear, modificar y borrar.
- Sin integridad referencial ni transacciones entre filas: el backend valida que el lugar y el usuario existan.
- Paginación por cursor (row key de inicio), no por `OFFSET`.

## 7. Consultas con complejidad (punto 7 de la consigna)

| Consulta | MySQL | HBase |
|---|---|---|
| **Ranking mensual por barrio**: top N lugares con más check-ins en un mes, para un barrio | `JOIN` checkin/lugar/barrio + `GROUP BY` + `RANK() OVER (...)` | Scan `lugares_por_barrio` (prefijo) + get en `stats_lugar` de la columna `m:yyyyMM` + ordenamiento en la app |
| **Pasaporte del usuario**: barrios visitados, cantidad de lugares distintos y barrios que le faltan | `JOIN` + `COUNT(DISTINCT)` + `LEFT JOIN` barrios | Scan `checkins_por_usuario` + agregación en la app |
| **Cercanos** (opcional): lugares a menos de X metros | `ST_Distance_Sphere` | Scan por prefijo de geohash + filtro por distancia en la app |

Esta tabla alimenta el punto 14 del informe (comparación entre implementaciones).

## 8. API REST

Todas las respuestas tienen esta forma:

```json
{
  "data": { },
  "meta": { "motor": "hbase", "duracion_ms": 12.4,
            "operaciones": ["SCAN lugares_por_barrio prefix='0007#' limit=20"] }
}
```

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/motores` | Motores disponibles y motor por defecto |
| GET | `/barrios` · `/categorias` | Catálogos |
| GET | `/lugares?barrio=&categoria=&q=&limite=&cursor=` | Listado paginado con filtros |
| GET | `/lugares/{id}` | Detalle |
| POST · PUT · DELETE | `/lugares` · `/lugares/{id}` | Alta, modificación, baja (409 si tiene check-ins) |
| GET | `/lugares/{id}/checkins` | Últimos check-ins del lugar |
| GET | `/lugares/cercanos?lat=&lon=&radio_m=` | Opcional |
| GET · POST | `/usuarios` · GET `/usuarios/{id}` | Usuarios |
| GET | `/usuarios/{id}/checkins` | Historial |
| POST · GET · PUT · DELETE | `/checkins` · `/checkins/{id}` | CRUD de check-ins (PUT solo puntaje y comentario) |
| GET | `/consultas/ranking-barrio?barrio=&mes=YYYY-MM&top=10` | Consulta compleja |
| GET | `/consultas/pasaporte/{id_usuario}` | Consulta compleja |

## 9. App mobile

Expo (React Native), probada con Expo Go en el celular. No hay login: en Ajustes se elige el "usuario actual" de una lista.

| Pantalla | Qué hace |
|---|---|
| Explorar | Listado de lugares con filtros de barrio y categoría (mapa opcional) |
| Detalle de lugar | Datos, últimos check-ins, botones para hacer check-in, editar y borrar |
| Formulario de lugar | Alta y modificación |
| Mi pasaporte | Mis check-ins (editar y borrar) y barrios visitados |
| Rankings | Ranking mensual por barrio |
| Ajustes | **Selector de motor (MySQL / HBase)**, usuario actual, URL del backend, modo debug on/off |

Hay un indicador del motor activo siempre visible, y en el modo debug se muestra `meta.operaciones` al pie de cada pantalla.

## 10. Infraestructura

`docker-compose.yml` en la raíz con:
- `mysql` (`mysql:8.4`, puerto **3307** en la PC, porque el 3306 lo usa el MySQL local de la cursada)
- `hbase` (`harisekhon/hbase:2.1`, standalone con ZooKeeper embebido; puertos 16010 UI, 9090 Thrift y 8080 REST)
- `backend` (opcional; también puede correr local con `uvicorn`)

Estructura del repo, según el punto 11 de la consigna:

```
/backend
/frontend
/database
    /datasets          CSV originales descargados de BA Data
    /mysql             modelo_relacional.sql, datos_iniciales.sql
    /hbase             scripts de creación de tablas y carga
    /etl               scripts que limpian y normalizan los CSV y generan los datos sintéticos
/documentacion         informe, DER, este documento
docker-compose.yml
README.md
```

## 11. Decisiones tomadas en la implementación

Sirven para el punto 15 del informe (problemas encontrados y decisiones tomadas).

- **Paginación por cursor opaco.** MySQL usa `id > cursor` (o `(fecha, id) < cursor` en check-ins). HBase usa el último row key leído como `row_start`. HBase no tiene `OFFSET`, así que para que la interfaz sea común los dos motores usan cursor.
- **Búsqueda por texto.** MySQL usa `LIKE` con la collation `utf8mb4_0900_ai_ci`, que no distingue tildes ni mayúsculas. HBase usa un `SingleColumnValueFilter` con `SubstringComparator`, que no distingue mayúsculas pero **sí tildes**: "cafe" no encuentra "Café". Es una diferencia real entre los motores y sirve para la comparación.
- **Integridad referencial en HBase.** Antes de crear un check-in, la aplicación verifica que existan el usuario y el lugar (en MySQL lo hace la FK). Antes de borrar un lugar, verifica que no tenga check-ins con un scan de `checkins_por_lugar` con limit=1 (en MySQL lo hace `ON DELETE RESTRICT`).
- **Unicidad en HBase.** `usuarios_por_nombre` cumple la función del UNIQUE. La verificación y la escritura no son atómicas, así que dos altas simultáneas con el mismo nombre podrían pasar. Es una limitación conocida.
- **Desnormalización y datos viejos.** Cada check-in guarda una copia de `nombre_lugar` y `barrio`. Si se renombra un lugar, los check-ins anteriores conservan el nombre viejo. Es el costo de leer sin joins.
- **Orden alfabético.** En HBase el orden se hace en la aplicación con el mismo criterio que la collation de MySQL (sin tildes ni mayúsculas), para que los dos motores devuelvan lo mismo.
- **Cercanos.** MySQL filtra primero por un bounding box (índice sobre latitud y longitud) y después calcula `ST_Distance_Sphere`. HBase calcula el geohash de la celda que contiene al punto y sus 8 vecinas, hace un scan por prefijo de cada una y filtra por distancia haversine en la aplicación.
- **Traza de operaciones.** Cada respuesta incluye en `meta.operaciones` el SQL o las operaciones de HBase que se ejecutaron, con su tiempo. La app las muestra en el panel de debug, y `backend/dev/comparar_motores.py` las usa para comparar los motores.

## 12. Pendientes

- [x] Imagen de HBase: `harisekhon/hbase:2.1`
- [x] Backend polimórfico (MySQL + HBase) con CRUD de lugares, check-ins y usuarios, y las consultas de la sección 7
- [x] App mobile (Expo) con selector de motor y panel de debug
- [ ] Modelo MySQL oficial → `database/mysql/modelo_relacional.sql`. Si difiere del borrador de la sección 5, hay que ajustar `backend/app/persistencia/mysql/repos.py`.
- [ ] Script oficial de creación de tablas HBase → `database/hbase/` (puede partir de `backend/app/persistencia/hbase/esquema.py`)
- [ ] ETL de los CSV reales de BA Data → reemplaza a los datos de prueba de `backend/dev/seed_dev.py`
- [ ] Definir el volumen de datos sintéticos (propuesta: 500 usuarios y 50.000 check-ins repartidos en 12 meses)
- [ ] Repo de Git
