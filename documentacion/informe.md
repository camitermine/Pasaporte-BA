# Pasaporte BA — Informe del TP Integrador

**Materia:** Base de Datos — Tecnicatura en Programación Informática (UNSAM)
**Docentes:** Gabriel Flores, Rodrigo Casco
**Integrantes:** <!-- TODO: nombres y apellidos -->
**Fecha de entrega:** <!-- TODO -->
**Repositorio:** <!-- TODO: URL de GitHub -->

> Borrador de trabajo. Las partes marcadas con **TODO** las tiene que completar el grupo.
> Al terminar, exportar a `documentacion/informe.pdf` (ver `documentacion/README.md`).

---

## 1. Descripción del problema

Buenos Aires tiene miles de puntos de interés cultural y turístico: espacios culturales,
monumentos, murales y bares y restaurantes notables. Esa información está publicada en datasets
separados y no hay una forma simple de explorarla por barrio, registrar qué lugares se visitaron
ni comparar qué lugares son los más visitados.

**Pasaporte BA** es una aplicación móvil (y web) donde cada persona:

- explora y busca lugares por nombre, barrio o categoría, o por cercanía a su ubicación;
- hace *check-in* en los lugares que visita, con puntaje y comentario opcionales;
- completa un "pasaporte" con un sello por cada barrio visitado;
- consulta el ranking mensual de lugares más visitados de cada barrio;
- guarda favoritos y sugiere lugares que faltan.

Un administrador crea las cuentas, modera las sugerencias y mantiene el catálogo.

El problema combina dos tipos de datos con necesidades distintas:

- **Datos maestros** (lugares, barrios, categorías, usuarios): pocos cambios, muchas relaciones e
  integridad estricta. Encajan en un modelo relacional.
- **Actividad** (check-ins): crece sin parar, se escribe mucho y se lee siempre por usuario, por
  lugar o por mes. Encaja en una base NoSQL orientada a columnas.

## 2. Descripción y origen del dataset

Los datos provienen del portal de datos abiertos del Gobierno de la Ciudad de Buenos Aires
(<https://data.buenosaires.gob.ar>), categoría *Cultura y turismo*. Se integraron **4 datasets**,
uno por fuente:

| Fuente (en el CSV) | Dataset original | Tipo en la app | URL | Fecha de descarga | Licencia |
|---|---|---|---|---|---|
| `espacios_culturales` | <!-- TODO --> | Cultura | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |
| `monumentos` | <!-- TODO --> | Patrimonio | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |
| `murales` | <!-- TODO --> | Arte urbano | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |
| `oferta_gastronomica` | <!-- TODO --> | Gastronomía | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |

> **TODO:** confirmar con quien descargó los datos el nombre exacto de cada dataset, su URL y la
> fecha. Los datasets de BA Data suelen publicarse con licencia CC BY 2.5 AR; verificarlo en la
> ficha de cada uno. Cargar también la URL y la fecha en la tabla `fuente` (ya tiene las columnas
> `url` y `fecha_descarga`).

Después de unir y limpiar los datos, el sistema contiene:

| Entidad | Registros |
|---|---|
| Lugares válidos | 8.322 (de 8.332 filas; 10 sin nombre descartadas) |
| Barrios | 48 |
| Comunas | 15 |
| Categorías de origen | 228 |
| Tipos de la app | 4 |
| Fuentes | 4 |

## 3. Análisis inicial de los datos

<!-- TODO: describir la estructura ORIGINAL de cada uno de los 4 datasets (columnas principales,
cantidad de filas). Si se conservan los CSV originales, agregarlos en database/datasets/originales/. -->

Problemas encontrados al analizar los datos:

| Problema | Ejemplo | Tipo de anomalía que provoca |
|---|---|---|
| El nombre del barrio se repite como texto en cada lugar | "PALERMO" en miles de filas | Actualización: renombrar un barrio implica tocar miles de filas. |
| La comuna depende del barrio, no del lugar | `lugar → barrio → comuna` | Dependencia transitiva: el mismo barrio podría quedar con comunas distintas. |
| La categoría se repite como texto | "MURAL", "BAR", "BUSTO" | Actualización e inconsistencias de escritura. |
| Variantes del mismo valor | Núñez aparece dos veces en `barrios.csv` con distinta codificación; "OLEO S/TELA" y "ÖLEO S/TELA" | Datos duplicados que rompen restricciones `UNIQUE`. |
| Texto mal codificado | caracteres con *mojibake* (Ã±, Ã©) | Datos ilegibles. |
| Registros sin nombre | 10 filas | No se pueden mostrar ni identificar. |
| Lugares sin barrio | 270 filas | No se puede saber a qué barrio pertenecen. |
| Coordenadas incompletas | latitud sin longitud (1 caso) | Ubicación inválida. |
| Dirección partida en 3 columnas | `calle`, `calle_interseccion`, `altura` | Se combinan en un único campo `direccion`. |
| Nombres en mayúsculas y sin tildes | "AGRONOMIA", "CONSTITUCION" | Problema de presentación (pendiente, ver sección 15). |
| Sin metadatos de origen | sin URL, fecha ni licencia | No se puede rastrear la procedencia. |

## 4. Proceso de normalización

<!-- TODO: completar con la tabla original "plana" de cada dataset (0FN/1FN) para mostrar la
evolución. Lo de abajo describe el resultado que ya está implementado. -->

**Punto de partida (tabla única por dataset, sin normalizar):**

```
LUGAR_ORIGINAL(id, nombre, fuente, tipo, calle, calle_interseccion, altura,
               barrio, comuna, latitud, longitud)
```

**1FN.** Todos los atributos son atómicos y no hay grupos repetitivos. La dirección se trata
como un único atributo descriptivo (no se consulta por calle).

**2FN.** La clave es simple (`id`), así que no hay dependencias parciales. Al unir los 4
datasets se agrega `fuente` y el identificador pasa a ser `(fuente, id_origen)`, que se conserva
como restricción `UNIQUE (id_fuente, id_origen)` para trazabilidad.

**3FN.** Se eliminan las dependencias transitivas:

| Dependencia transitiva | Solución |
|---|---|
| `lugar → barrio → comuna` | Tabla `barrio(id_barrio, nombre, id_comuna)` y tabla `comuna`. `lugar` solo guarda `id_barrio`. |
| `lugar → categoría → tipo` | Tabla `categoria(id_categoria, nombre, id_tipo)` y `tipo_lugar`. |
| `lugar → fuente → (nombre, url, fecha)` | Tabla `fuente`. |

**Resultado (3FN):**

```
COMUNA(id_comuna)
BARRIO(id_barrio, nombre, id_comuna→COMUNA)
TIPO_LUGAR(id_tipo, nombre)
CATEGORIA(id_categoria, nombre, id_tipo→TIPO_LUGAR)
FUENTE(id_fuente, nombre, url, fecha_descarga)
LUGAR(id_lugar, nombre, direccion, latitud, longitud, id_categoria→CATEGORIA,
      id_barrio→BARRIO, id_fuente→FUENTE, id_origen, activo, fecha_alta, fecha_modificacion)
```

A esto se suman las entidades propias de la aplicación, también en 3FN: `USUARIO`, `CHECKIN`,
`FAVORITO`, `SUGERENCIA_LUGAR` y `SESION`.

La limpieza la hace el ETL `database/etl/generar_datos_mysql.py`, que lee los CSV y genera
`database/mysql/datos_iniciales.sql` sin modificar los originales.

## 5. Diagrama Entidad-Relación

Ver `documentacion/DER.md` (incluye el diagrama y la explicación de cada cardinalidad).

<!-- TODO: insertar acá la imagen exportada: ![DER](DER.png) -->

## 6. Modelo relacional

Motor: **MySQL 8.4**. Script completo: `database/mysql/modelo_relacional.sql`.

| Tabla | PK | FK | Restricciones relevantes |
|---|---|---|---|
| `comuna` | `id_comuna` | — | `CHECK (id_comuna BETWEEN 1 AND 15)` |
| `barrio` | `id_barrio` | `id_comuna → comuna` | `nombre UNIQUE` |
| `tipo_lugar` | `id_tipo` | — | `nombre UNIQUE` |
| `categoria` | `id_categoria` | `id_tipo → tipo_lugar` | `UNIQUE (nombre, id_tipo)` |
| `fuente` | `id_fuente` | — | `nombre UNIQUE` |
| `lugar` | `id_lugar` | `id_categoria`, `id_barrio` (nullable), `id_fuente` (nullable) | `UNIQUE (id_fuente, id_origen)`; índices por ubicación y por filtros; `activo` para baja lógica |
| `usuario` | `id_usuario` | `id_barrio` (nullable) | `nombre_usuario UNIQUE`, `email UNIQUE`, `rol ENUM` |
| `checkin` | `id_checkin` | `id_usuario`, `id_lugar` (`ON DELETE RESTRICT`) | `CHECK (puntaje BETWEEN 1 AND 5)`; índices `(id_lugar, fecha_hora)` y `(id_usuario, fecha_hora)` |
| `favorito` | `(id_usuario, id_lugar)` | ambas con `ON DELETE CASCADE` | PK compuesta: no hay favoritos duplicados |
| `sugerencia_lugar` | `id_sugerencia` | autor, revisor, categoría, barrio, lugar creado (`ON DELETE SET NULL`) | `estado ENUM`; índice `(estado, fecha_alta)` |
| `sesion` | `id_sesion` | `id_usuario` (`ON DELETE CASCADE`) | `token_hash UNIQUE` |

Decisiones:

- **Baja lógica de lugares** (`activo = FALSE`): un lugar con check-ins no se puede borrar
  físicamente (`ON DELETE RESTRICT`), porque se perdería historial.
- **Contraseñas** con PBKDF2-SHA256 y salt aleatorio; de las sesiones se guarda solo el hash del
  token.
- Los índices compuestos siguen las consultas reales: el historial de un lugar o de un usuario
  ordenado por fecha.

## 7. Diseño de la solución NoSQL

Motor: **Apache HBase 2.1** (base de datos orientada a columnas, modelo *wide-column*). Su uso
fue autorizado por los docentes, ya que es el motor que el grupo trabajó en el TP de bases NoSQL.

En HBase se guarda una **proyección desnormalizada** del catálogo y toda la **actividad**. Cada
tabla está pensada para responder **una consulta concreta** con un único *scan* por prefijo de
row key:

| Tabla | Row key | Para qué consulta |
|---|---|---|
| `lugares` | `<idLugar>` | Detalle de un lugar (incluye barrio, comuna y categoría copiados) |
| `lugares_por_barrio` | `<idBarrio>#<idLugar>` | Listar lugares de un barrio |
| `lugares_por_categoria` | `<idCategoria>#<idLugar>` | Listar lugares de una categoría |
| `lugares_por_geohash` | `<geohash6>#<idLugar>` | Lugares cercanos a un punto |
| `usuarios` / `usuarios_por_nombre` | `<idUsuario>` / `<nombre_usuario>` | Perfil y búsqueda por nombre |
| `checkins` | `<idCheckin>` | Check-in individual |
| `checkins_por_lugar` | `<idLugar>#<tsInvertido>#<idCheckin>` | Últimos check-ins de un lugar (los más nuevos primero) |
| `checkins_por_usuario` | `<idUsuario>#<tsInvertido>#<idCheckin>` | Historial y pasaporte de un usuario |
| `stats_lugar` | `<idLugar>` con columnas `m:<yyyyMM>` y `t:total` | Contadores atómicos para el ranking mensual |
| `secuencias` | `lugar` / `usuario` / `checkin` | Generación de IDs (no hay `AUTO_INCREMENT`) |

Técnicas de modelado usadas:

- **IDs con ceros a la izquierda** (`0000000147`) para que el orden lexicográfico coincida con el
  numérico.
- **Timestamp invertido** en la row key, para que un scan devuelva primero lo más reciente.
- **Geohash** para convertir la búsqueda por cercanía en scans por prefijo.
- **Contadores atómicos** (`increment`) para no recorrer todos los check-ins al armar un ranking.
- **Escritura múltiple**: un check-in se escribe en 3 tablas, cada una ordenada para una
  consulta.

Scripts NoSQL: `backend/app/persistencia/hbase/esquema.py` crea las tablas, y
`database/hbase/cargar_desde_mysql.py` carga la proyección inicial desde MySQL.

## 8. Justificación de la utilización de NoSQL

**Qué información va a HBase:** la actividad (check-ins), los índices de lectura del catálogo y
los agregados (contadores por lugar y mes).

**Por qué un modelo columnar como HBase:**

- Los check-ins crecen sin límite y son un caso típico de *append* (se agregan, casi no se
  modifican). HBase escala horizontalmente particionando por row key.
- Todas las lecturas de actividad son por un prefijo conocido (usuario, lugar o mes): eso es
  exactamente un scan por rango de row key, sin joins.
- Los contadores atómicos permiten rankings sin `GROUP BY` sobre millones de filas.

**Ventajas frente al modelo relacional:**

- Lecturas de agregados (pasaporte, ranking) que no se degradan con el volumen: con 1 millón de
  check-ins, el pasaporte del usuario más activo tarda 27 ms en HBase contra 172 ms en MySQL
  (ver sección 14).
- Esquema flexible: agregar un mes nuevo al contador es agregar una columna.

**Desventajas y limitaciones:**

- No tiene claves foráneas, restricciones `UNIQUE`, transacciones entre filas ni joins. Todo eso
  lo resuelve la aplicación (validaciones manuales y escrituras múltiples).
- La desnormalización duplica datos: si cambia el nombre de un lugar, los check-ins viejos
  conservan el nombre anterior.
- Cada consulta nueva requiere diseñar una tabla nueva.
- En consultas puntuales chicas (un historial corto) MySQL es más rápido, por el costo de
  conexión de Thrift.
- Es más pesado de operar (necesita ZooKeeper y la JVM).

Por eso la solución es **híbrida**: MySQL sigue siendo la fuente de verdad y HBase es una
proyección optimizada para lectura.

## 9. Arquitectura general de la aplicación

```
 Expo / React Native (iOS, Android, Web)
            │  HTTP + JSON, token Bearer
            ▼
 FastAPI (backend/app/api.py)
            │  solo conoce las interfaces RepoLugares, RepoCheckins, RepoConsultas...
            ▼
 Capa de persistencia (backend/app/persistencia)
     ├── mysql/   implementación relacional (SQLAlchemy + PyMySQL)
     ├── hbase/   implementación columnar (HappyBase + Thrift)
     └── hibrida.py  coordina la escritura MySQL → HBase de la actividad
            │                         │
            ▼                         ▼
      MySQL 8.4 (Docker)       HBase 2.1 (Docker)
```

El frontend nunca accede a las bases: toda interacción pasa por el backend.

## 10. Explicación del backend polimórfico

`backend/app/persistencia/base.py` define interfaces abstractas (`RepoLugares`, `RepoCheckins`,
`RepoConsultas`, `RepoUsuarios`, `RepoCatalogo`) con operaciones como `listar()`, `obtener()`,
`crear()`, `actualizar()`, `eliminar()`, `cercanos()`, `ranking_barrio()` y `pasaporte()`.

Cada motor las implementa a su manera:

| Operación | MySQL | HBase |
|---|---|---|
| `lugares.listar(barrio)` | `SELECT ... WHERE id_barrio = ? ORDER BY ...` | scan de `lugares_por_barrio` con prefijo `<idBarrio>#` + multi-get |
| `lugares.cercanos()` | filtro por *bounding box* + distancia | scan de las celdas geohash vecinas |
| `consultas.ranking_barrio()` | `COUNT(*) ... GROUP BY ... RANK()` | lectura de contadores `stats_lugar` |
| `consultas.pasaporte()` | joins + `GROUP BY barrio` | scan de `checkins_por_usuario` |

La fábrica (`persistencia/fabrica.py`) construye el conjunto de repositorios de un motor. La API
recibe ese conjunto por inyección de dependencias y no sabe qué tecnología hay detrás.

**Selección del motor:**

- **Modo automático (por defecto):** el backend asigna cada responsabilidad al motor más
  adecuado. MySQL resuelve el catálogo, las cuentas y todas las escrituras; HBase resuelve los
  historiales, el pasaporte y los rankings. Configurable con la variable de entorno
  `ACTIVIDAD_DB`.
- **Modo demostración:** con el header HTTP `X-Motor: mysql` o `X-Motor: hbase` (en la app:
  *Perfil → Motor de base de datos*), **la misma lectura** se ejecuta con la implementación del
  motor elegido. Las escrituras ignoran el selector: siempre van a MySQL y se replican a HBase,
  para que las dos bases no se desincronicen.
- Cada respuesta incluye `meta.motor`, la duración y las operaciones ejecutadas. La app las
  muestra en el badge del encabezado y en la barra de diagnóstico.

**CRUD implementado:** lugares (alta, consulta individual, listado, modificación y baja lógica, solo
admin) y check-ins (alta, consulta, modificación y baja, por su autor).

**Consultas complejas:** pasaporte del usuario (barrios visitados y faltantes, con progreso),
ranking mensual por barrio (con empates tipo `RANK()`) y lugares cercanos por radio.

## 11. Tecnologías utilizadas

| Capa | Tecnología |
|---|---|
| Base relacional | MySQL 8.4 |
| Base NoSQL | Apache HBase 2.1 (imagen `harisekhon/hbase`), acceso por Thrift |
| Backend | Python 3.11+, FastAPI, SQLAlchemy, PyMySQL, HappyBase, Pydantic |
| Frontend | Expo SDK 58, React Native, Expo Router, TypeScript (móvil y web) |
| Infraestructura | Docker Compose |
| Control de versiones | Git + GitHub (ramas por funcionalidad y pull requests) |
| Gestión de tareas | <!-- TODO: GitHub Projects / Trello / Notion... --> |

## 12. Instrucciones para ejecutar el proyecto

Ver `README.md` en la raíz del repositorio. Resumen: `docker compose up -d`, crear el esquema y
cargar los datos iniciales, cargar la proyección en HBase, levantar el backend con `uvicorn` y la
app con `npx expo start` (o `npx expo start --web` para la versión de escritorio).

## 13. Ejemplos de funcionamiento

<!-- TODO: capturas de pantalla. Sugerencia de capturas (en la versión web):
1. Login.
2. Inicio con el desafío del pasaporte y el listado de lugares.
3. Filtro por barrio y búsqueda por nombre.
4. Detalle de un lugar y alta de un check-in.
5. Edición y borrado del check-in.
6. Mi pasaporte con los sellos por barrio.
7. Ranking mensual de un barrio.
8. Cercanos con el mapa.
9. Admin: alta, edición y baja de un lugar; moderación de sugerencias.
10. Perfil → Motor: la misma pantalla resuelta con MySQL y con HBase, mostrando la barra de
    diagnóstico con las operaciones y los milisegundos. -->

## 14. Comparación entre ambas implementaciones

Medición con `backend/dev/comparar_motores.py`: 30 repeticiones por caso y la **mediana** en ms.
Las dos implementaciones devuelven resultados equivalentes en todos los casos. Escenario con
**1.000.001 check-ins** simulados:

| Consulta | Caso | MySQL (ms) | HBase (ms) |
|---|---|---:|---:|
| Historial por usuario | más activo (1.303 check-ins) | 3,6 | 8,3 |
| Actividad por lugar | más activo (59.899 check-ins) | 3,8 | 8,3 |
| Ranking mensual | barrio más activo (13.463 check-ins) | 24,0 | 14,0 |
| Ranking mensual | barrio mediano | 6,9 | 9,1 |
| Pasaporte del usuario | más activo | 172,2 | 27,1 |
| Pasaporte del usuario | mediano | 9,9 | 10,0 |

Datos completos para 10.000, 100.000 y 1.000.000 de check-ins en
`backend/dev/resultados/benchmark.csv`.

**Conclusión de la comparación:** en lecturas puntuales y paginadas MySQL gana, porque sus
índices compuestos resuelven el caso y HBase paga el costo de Thrift. En las consultas de
**agregación sobre mucho volumen** (pasaporte del usuario muy activo, ranking del barrio con más
actividad), HBase gana con claridad gracias a los contadores precalculados y a los scans por
prefijo. Y su ventaja crece con el volumen.

<!-- TODO (opcional): agregar un gráfico de mediana vs. volumen para pasaporte y ranking. -->

## 15. Problemas encontrados y decisiones tomadas

| Problema | Decisión |
|---|---|
| Dos codificaciones distintas de "Núñez" | Se consolidan en un único barrio en el ETL. |
| Categorías que solo difieren en acentos ("OLEO S/TELA" / "ÖLEO S/TELA") rompían la carga en una base nueva | El ETL las consolida usando la misma regla que la collation de MySQL. Quedan 228 categorías. |
| 10 lugares sin nombre | Se omiten; no se inventan valores. |
| 270 lugares sin barrio | Se cargan con `id_barrio = NULL`; no admiten check-in hasta que se valide el barrio. |
| Coordenadas incompletas | Se guardan como `NULL`. |
| HBase no tiene FKs, `UNIQUE` ni transacciones | Validación en la aplicación, escrituras múltiples y MySQL como fuente de verdad. |
| Mantener sincronizadas las dos bases | Escritura canónica en MySQL y replicación inmediata a HBase. Si HBase falla, se puede reconstruir la proyección con `cargar_desde_mysql.py`. |
| Mostrar el polimorfismo sin desincronizar los datos | Selector de motor solo para lecturas (header `X-Motor`). |
| `react-native-maps` no funciona en web | Componente de mapa separado por plataforma; en web se usa un mapa de OpenStreetMap. |
| Nombres en mayúsculas y sin tildes en el dataset | Por ahora la app los muestra en formato título. **TODO:** normalizarlos en el ETL. |
| <!-- TODO: agregar otros problemas que haya tenido el grupo --> | |

## 16. Conclusiones

<!-- TODO: redactarlas en grupo. Ideas:
- La normalización hizo visible y evitó anomalías reales del dataset (Núñez, OLEO/ÖLEO).
- No hay un motor "mejor": cada uno rinde en un tipo de acceso distinto (ver sección 14).
- Separar la lógica de la persistencia permitió cambiar de motor sin tocar la API ni la app.
- El costo de NoSQL: la integridad que en MySQL da el motor, en HBase la tiene que garantizar el
  código.
- Qué harían distinto o qué agregarían (fotos de los lugares, parte social, verificación del
  check-in por GPS...). -->
