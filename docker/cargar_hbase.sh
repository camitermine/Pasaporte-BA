#!/bin/sh
# Reconstruye las proyecciones de HBase desde MySQL. HBase tarda en levantar
# el Thrift, así que se reintenta hasta que responda.
intentos=0
until python /app/database/hbase/cargar_desde_mysql.py; do
  intentos=$((intentos + 1))
  if [ "$intentos" -ge 40 ]; then
    echo "HBase no respondió a tiempo" >&2
    exit 1
  fi
  echo "HBase todavía no está listo, reintento en 5 s ($intentos/40)..."
  sleep 5
done
