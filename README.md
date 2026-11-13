# Pasaporte BA

Aplicación móvil para descubrir puntos de interés de la Ciudad de Buenos Aires, guardarlos como
favoritos y registrar visitas. Los usuarios pueden sugerir lugares; un administrador crea las
cuentas, modera las propuestas y mantiene el catálogo.

## Arquitectura

```text
Expo / React Native
        │ HTTP + Bearer token
        ▼
FastAPI
   ├── MySQL: usuarios, sesiones, roles, catálogo, favoritos, sugerencias y check-in canónico
   └── HBase: historiales de check-in, pasaporte, índices y rankings
```

En modo automático, el backend decide qué motor corresponde a cada operación. Cada respuesta
incluye `meta.motor` para poder identificarlo y explicarlo durante la presentación.

Para mostrar el backend polimórfico, en la app (*Perfil → Motor de base de datos*) se puede
forzar MySQL o HBase. La app envía el header `X-Motor` y las **lecturas** se resuelven con la
implementación de ese motor detrás de la misma interfaz. Las escrituras siempre van a MySQL y se
replican a HBase, para que ambas bases sigan sincronizadas.

## Datos

El repositorio incluye los cuatro CSV recibidos en `database/datasets/tablas_3fn/`. El ETL:

```powershell
python database\etl\generar_datos_mysql.py
```

genera `database/mysql/datos_iniciales.sql` con 8.322 lugares válidos, 48 barrios y 228 categorías
de origen. Los CSV originales se conservan sin modificaciones. Durante la limpieza, el ETL:

- Consolida las dos codificaciones de Núñez en un único barrio.
- Consolida categorías que solo difieren en acentos (por ejemplo `OLEO S/TELA` y `ÖLEO S/TELA`),
  porque MySQL las considera iguales en la restricción `UNIQUE`.
- Omite 10 registros sin nombre y no inventa valores.
- Conserva 270 lugares sin barrio con `id_barrio = NULL`.
- Convierte coordenadas incompletas a `NULL`.
- Corrige texto mal codificado cuando es recuperable.
- Usa los tipos de origen como categorías agrupadas en cultura, patrimonio, arte urbano o
  gastronomía.

Los datos provienen del portal de datos abiertos de la Ciudad
(<https://data.buenosaires.gob.ar>, categoría *Cultura y turismo*): espacios culturales,
monumentos, murales y oferta gastronómica. Las URL oficiales, la licencia CC BY 2.5 AR y la
aclaración sobre la fecha histórica de descarga están documentadas en la sección 2 del informe.

## Documentación

El informe, el DER y la guía de pendientes están en `documentacion/`.

## Puesta en marcha con Docker (recomendada para probar)

Solo se necesita **Git** y **Docker Desktop abierto**. Desde la raíz del repositorio:

```powershell
docker compose up -d --build
```

La primera vez tarda unos minutos porque arma las imágenes. Cuando termina, abrir
**<http://localhost:8081>** en el navegador.

| Servicio | Qué hace | Puerto en la PC |
|---|---|---|
| `web` | Versión web de la app (Expo exportado, servido con nginx) | 8081 |
| `backend` | API FastAPI. Documentación en `/docs` | 8000 |
| `mysql` | Datos maestros y transacciones | 3307 |
| `hbase` | Historiales, pasaporte y rankings (UI del Master en 16010) | 9090 |
| `hbase-init` | Reconstruye HBase desde MySQL en cada arranque y termina | — |

La primera vez que se crea el volumen de MySQL se cargan solos `modelo_relacional.sql` y
`datos_iniciales.sql`. En cada `up`, `hbase-init` vuelve a proyectar HBase desde MySQL, y el
backend arranca cuando esa carga termina.

Comandos útiles:

```powershell
docker compose ps                # estado de los servicios (hbase-init figura "Exited (0)": es normal)
docker compose logs -f backend   # ver los logs de un servicio
docker compose stop              # apagar todo sin perder datos
docker compose up -d --build     # después de un git pull con cambios en el código
docker compose down -v           # BORRA las bases y las recrea en el próximo up
```

`down -v` hace falta cuando cambia `datos_iniciales.sql`: los scripts de carga solo corren con el
volumen vacío. Borra también los check-ins, favoritos y sugerencias que se hayan cargado a mano.

Si un puerto está ocupado (por ejemplo, el 8081 por un `npx expo start` abierto), cerrar ese
proceso o cambiar el puerto de la izquierda en `docker-compose.yml`.

## Puesta en marcha para desarrollo

Para editar el código con recarga automática o probar la app en el teléfono, el backend y la
app se corren fuera de Docker. Requisitos en la computadora:

- Git.
- Docker Desktop abierto.
- Python 3.11 o superior.
- Node.js 20 o superior.

En el teléfono se necesita Expo Go compatible con SDK 58. El teléfono y la computadora deben
estar conectados a la misma red Wi-Fi. Todos los comandos siguientes se ejecutan desde la raíz
del repositorio en PowerShell.

### 1. Bases de datos

Se levantan solo las bases; si el stack completo está corriendo, primero
`docker compose stop backend web` para liberar los puertos 8000 y 8081.

```powershell
docker compose up -d mysql hbase
cmd /c "docker exec -i pasaporteba-mysql mysql --default-character-set=utf8mb4 -upasaporte -ppasaporte pasaporteba < database\mysql\modelo_relacional.sql"
cmd /c "docker exec -i pasaporteba-mysql mysql --default-character-set=utf8mb4 -upasaporte -ppasaporte pasaporteba < database\mysql\datos_iniciales.sql"
```

Si las bases se crean por primera vez, MySQL ya carga el esquema y los datos solo y estos dos
comandos se pueden saltear. Si MySQL todavía está arrancando, el primer comando falla con un error de conexión: esperar
unos segundos y repetirlo. Se usa `cmd /c` con `<` porque el pipe de PowerShell 5.1
(`Get-Content | docker exec`) cambia la codificación y rompe las tildes y las ñ. Estos comandos
**borran y recrean** la base local; hay que volver a correrlos cada vez que cambia
`datos_iniciales.sql`, y después recargar HBase (paso 2).

### 2. Backend

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
backend\.venv\Scripts\python database\hbase\cargar_desde_mysql.py
backend\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

Documentación interactiva: `http://localhost:8000/docs`.

### 3. Aplicación móvil

```powershell
Set-Location frontend
npm ci
npx expo start
```

Para presentar desde la computadora (por ejemplo, compartiendo pantalla en Meet) se puede usar la
versión web, que se muestra centrada con ancho de celular:

```powershell
npx expo start --web
```

En web el mapa de `Cerca` se reemplaza por un mapa embebido de OpenStreetMap. Como el repositorio
está en OneDrive, a veces Metro no detecta cambios en los archivos: si la app no se actualiza,
reiniciar con `npx expo start --web --clear`.

Para usarla en el teléfono, Expo muestra un código QR. Hay que escanearlo con Expo Go desde un teléfono conectado a la misma
red. La app calcula la URL del backend con la IP usada por Expo; también se puede modificar desde
`Ajustes`. Si Windows pregunta por el firewall, se debe permitir el acceso de Node y Python en
redes privadas.

## Cuentas iniciales

| Rol | Usuario | Contraseña |
|---|---|---|
| Administrador | `admin` | `Admin123!` |
| Usuario | `visitante` | `Usuario123!` |

Son credenciales locales de demostración. Las cuentas nuevas solo pueden ser creadas por un
administrador y las contraseñas se guardan con PBKDF2-SHA256 y salt aleatorio.

## Funcionalidades actuales

- Login real con sesiones revocables y roles.
- Exploración y búsqueda por barrio o categoría.
- Mapa de lugares cercanos mediante la ubicación del dispositivo.
- Favoritos.
- Check-ins sin foto, marcados como no verificados.
- Pasaporte de barrios y ranking mensual.
- Sugerencias de lugares y moderación administrativa.
- Alta, modificación y baja lógica de lugares solo para administradores.
- Indicador del motor que resolvió cada operación y selector de motor para las lecturas (modo demo).

## Verificación

```powershell
Set-Location frontend
npx tsc --noEmit
npx eslint .

Set-Location ..
python -m compileall -q backend\app backend\dev database\etl database\hbase
```

## Comparación de rendimiento MySQL vs HBase

La comparación de rendimiento es una herramienta interna del TP. Primero se
genera actividad simulada sobre los lugares reales (usuarios `sim_*` y check-ins entre mayo y
octubre de 2026, siempre los mismos para la misma semilla), después se proyecta a HBase y por
último se miden las mismas lecturas en ambos motores, verificando que devuelvan lo mismo:

```powershell
Set-Location backend
.venv\Scripts\python -m dev.generar_actividad --checkins 100000
.venv\Scripts\python ..\database\hbase\cargar_desde_mysql.py
.venv\Scripts\python -m dev.comparar_motores --repeticiones 30 --csv dev\resultados\benchmark.csv
```

`comparar_motores` elige solo casos representativos (el usuario, lugar y barrio con más actividad,
uno mediano y uno con poca); con `--usuario`, `--lugar` o `--barrio` se fuerza uno. Los datos
simulados aparecen en los rankings de la app; para la demo se eliminan con
`.venv\Scripts\python -m dev.generar_actividad --borrar` y se vuelve a correr `cargar_desde_mysql.py`.
