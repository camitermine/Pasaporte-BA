# Documentación de la entrega

| Archivo | Contenido | Estado |
|---|---|---|
| `informe.md` | Informe completo y correspondencia con las consignas | Listo; falta reemplazar los nombres de integrantes |
| `DER.md` | DER en Mermaid y explicación de cardinalidades | Listo |
| `informe.pdf` | Versión final para entregar | Se genera desde `informe.md` |
| `../backend/dev/resultados/benchmark.csv` | Resultados reproducibles MySQL–HBase | Listo |

Antes de entregar, reemplazar en `informe.md` la línea de integrantes con los cinco nombres y
volver a generar el PDF. La fecha exacta de descarga histórica de los datasets no se conservó;
el informe lo declara expresamente y registra la fecha de consulta de las fichas oficiales.

## Evidencia técnica

- Modelo relacional: `database/mysql/modelo_relacional.sql`.
- Datos iniciales: `database/mysql/datos_iniciales.sql`.
- Modelo HBase: `backend/app/persistencia/hbase/esquema.py`.
- Proyección MySQL → HBase: `database/hbase/cargar_desde_mysql.py`.
- Comparación: `backend/dev/comparar_motores.py` y `backend/dev/resultados/benchmark.csv`.
- Ejecución: `README.md` en la raíz y `docker-compose.yml`.

## Guion breve de demostración

1. Iniciar sesión y recorrer Inicio, detalle y alta de check-in.
2. Mostrar pasaporte y ranking como consultas no triviales.
3. Repetir una lectura con MySQL y HBase desde Ajustes y señalar `meta.motor` y los tiempos.
4. Ingresar como administrador y mostrar mantenimiento de lugares y moderación de sugerencias.
5. Explicar la tabla comparativa de la sección 14 del informe.
