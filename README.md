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

El usuario no selecciona una base. El backend decide qué motor corresponde y cada respuesta
incluye `meta.motor` para poder identificarlo y explicarlo durante la presentación.

## Datos

El repositorio incluye los cuatro CSV recibidos en `database/datasets/tablas_3fn/`. El ETL:

```powershell
python database\etl\generar_datos_mysql.py
```

genera `database/mysql/datos_iniciales.sql` con 8.322 lugares válidos, 48 barrios y 232 categorías
de origen. Los CSV originales se conservan sin modificaciones. Durante la limpieza, el ETL:

- Consolida las dos codificaciones de Núñez en un único barrio.
- Omite 10 registros sin nombre y no inventa valores.
- Conserva 270 lugares sin barrio con `id_barrio = NULL`.
- Convierte coordenadas incompletas a `NULL`.
- Corrige texto mal codificado cuando es recuperable.
- Usa los tipos de origen como categorías agrupadas en cultura, patrimonio, arte urbano o
  gastronomía.

El material recibido no contiene URL, fecha de descarga ni licencia de las cuatro fuentes; esos
datos deben completarse antes de la entrega del informe.

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

Expo muestra un código QR. Hay que escanearlo con Expo Go desde un teléfono conectado a la misma
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
- Indicador del motor que resolvió cada operación, sin selector para el usuario.

## Verificación

```powershell
Set-Location frontend
npx tsc --noEmit
npx eslint .

Set-Location ..
python -m compileall -q backend\app backend\dev database\etl database\hbase
```

La comparación es una herramienta interna del TP; no aparece como selector en la app. Con ambas
bases cargadas se ejecutan las mismas lecturas y se verifican resultados y medianas de tiempo:

```powershell
Set-Location backend
.venv\Scripts\python -m dev.comparar_motores --usuario 1 --lugar 1 --barrio 1 --mes 2026-10 --repeticiones 10
```

Antes de sacar conclusiones de rendimiento hay que generar un volumen representativo de
check-ins y repetir las mediciones en condiciones controladas.
