# Pasaporte BA

App mobile para hacer check-in en bares, cafés, espacios culturales, monumentos y murales de la Ciudad de Buenos Aires.
TP Integrador de Bases de Datos: el mismo backend trabaja con **MySQL** o con **HBase** (backend polimórfico).

Diseño completo: [documentacion/DISENO.md](documentacion/DISENO.md)

```
App mobile (Expo)  ──HTTP + header X-Motor──>  Backend FastAPI  ──>  MySQL 8.4
                                                                └──>  HBase 2.1 (Thrift)
```

## Requisitos

- Docker Desktop
- Python 3.11 o superior
- Node.js 20 o superior
- Android con **Expo Go** instalado (Play Store), en la **misma red Wi-Fi** que la PC

## 1. Levantar las bases

```bash
docker compose up -d
```

| Servicio | Puerto en la PC | Notas |
|---|---|---|
| MySQL 8.4 | **3307** | usuario `pasaporte` / clave `pasaporte`, base `pasaporteba` (root: `root`) |
| HBase (Thrift) | 9090 | lo usa el backend |
| HBase (UI web) | 16010 | http://localhost:16010 |

> MySQL usa el 3307 porque el 3306 suele estar ocupado por un MySQL instalado localmente.
> HBase tarda unos 30 a 60 segundos en estar listo después de `docker compose up`.

## 2. Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # en Linux/Mac: .venv/bin/pip
cp .env.example .env
```

Cargar datos de **prueba** (sintéticos, los mismos IDs en los dos motores):

```bash
.venv/Scripts/python -m dev.seed_dev
```

Levantar la API (escucha en toda la red para que la vea el celular):

```bash
.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Documentación interactiva: http://localhost:8000/docs
- El motor se elige por request con el header `X-Motor: mysql | hbase` (o `?motor=`); el valor por defecto está en `MOTOR_DB` del `.env`.

Comparar los dos motores (mismas consultas, resultados y tiempos):

```bash
.venv/Scripts/python -m dev.comparar_motores
```

## 3. App mobile

```bash
cd frontend
npm install
npx expo start
```

1. Abrí **Expo Go** en el Android y escaneá el QR que aparece en la terminal.
2. La app usa automáticamente la IP de la PC para llegar al backend (`http://<ip-de-la-pc>:8000`). Si no conecta, cambiala en **Ajustes → Backend**.
3. En **Ajustes** elegí un usuario y el motor (también se cambia tocando el botón de motor del encabezado).

### Si el celular no conecta

La PC y el celular tienen que estar conectados **al mismo router**. La PC puede estar por cable, eso no importa.

1. Buscá la IP de la PC con `ipconfig` (la que empieza con `192.168.`).
2. En el navegador del celular abrí `http://<ip-de-la-pc>:8000/motores`. Si ves un JSON, la red está bien.
3. Si no carga, revisá estas causas:
   - El **Firewall de Windows** bloquea los puertos 8000 y 8081. Cuando Windows pregunte, permití Python y Node en redes privadas.
   - El celular está en la red de **invitados** del router, que aísla a los dispositivos entre sí.
   - El celular está en otra red (datos móviles, un repetidor con otro rango de IPs).

### Alternativa por cable USB (no depende de la red)

1. En el Android, activá las Opciones de desarrollador y, dentro de ellas, la **Depuración USB**.
2. Conectalo a la PC (hace falta `adb`, que viene en Android platform-tools).
3. Redirigí los puertos del celular a la PC:
   ```bash
   adb reverse tcp:8000 tcp:8000
   ```
   ```bash
   adb reverse tcp:8081 tcp:8081
   ```
4. En la app, en **Ajustes → Backend**, poné `http://localhost:8000`.

También se puede probar en el navegador: `npx expo start --web`.

## Estructura

```
backend/
  app/
    api.py                  rutas HTTP (no conocen el motor)
    dominio.py              modelos que expone la API
    persistencia/
      base.py               interfaces (repositorios abstractos)
      fabrica.py            elige la implementación según el motor
      mysql/repos.py        implementación MySQL (SQL explícito)
      hbase/repos.py        implementación HBase (row keys, tablas índice, contadores)
  dev/                      esquema y datos de prueba para desarrollo, comparación de motores
frontend/                   app Expo (React Native + expo-router)
database/                   scripts oficiales del TP (modelo relacional, carga, HBase)
documentacion/              informe, DER, documento de diseño
docker-compose.yml
```
