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
monumentos, murales y oferta gastronómica. Falta registrar la URL exacta, la fecha de descarga y
la licencia de cada dataset (ver `documentacion/informe.md`, sección 2).

## Documentación

El informe, el DER y la guía de pendientes están en `documentacion/`.

## Puesta en marcha local

Cada integrante trabaja con sus propias bases locales. Requisitos en la computadora:

- Git.
- Docker Desktop abierto.
- Python 3.11 o superior.
- Node.js 20 o superior.

En el teléfono se necesita Expo Go compatible con SDK 58. El teléfono y la computadora deben
estar conectados a la misma red Wi-Fi. Todos los comandos siguientes se ejecutan desde la raíz
del repositorio en PowerShell.

### 1. Bases de datos

```powershell
docker compose up -d
Get-Content backend\dev\schema_mysql_dev.sql -Raw | docker exec -i pasaporteba-mysql mysql -upasaporte -ppasaporte pasaporteba
Get-Content database\mysql\datos_iniciales.sql -Raw | docker exec -i pasaporteba-mysql mysql -upasaporte -ppasaporte pasaporteba
```

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
