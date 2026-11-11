# Documentación — guía de trabajo

Esta carpeta junta lo que pide el punto 10 de la consigna (informe + DER).

| Archivo | Qué es | Estado |
|---|---|---|
| `informe.md` | Borrador del informe con las 16 secciones obligatorias | Bastante avanzado; tiene **TODO** marcados |
| `DER.md` | Diagrama Entidad-Relación en Mermaid + cardinalidades | Listo; falta exportarlo a imagen |
| `informe.pdf` | Entrega final | Falta generarlo |
| `DER.png` | DER exportado como imagen | Falta exportarlo |
| `capturas/` | Capturas de la app para la sección 13 | Falta crearla |

## Checklist de pendientes

Buscar `TODO` en `informe.md` para encontrar cada punto.

### Datos (prioridad alta, son de lo que más se evalúa)
- [ ] **Sección 2:** nombre exacto, URL, fecha de descarga y licencia de los 4 datasets de BA Data
  (espacios culturales, monumentos, murales y oferta gastronómica). Preguntarle a quien los
  descargó.
- [ ] **Secciones 3 y 4:** describir la estructura **original** de cada dataset, antes de
  normalizar. Si se tienen los CSV originales, guardarlos en `database/datasets/originales/`. Con
  eso se completa la "evolución" que pide la consigna (tabla plana → 1FN → 2FN → 3FN).
- [ ] Normalizar nombres en el ETL (mayúsculas, tildes faltantes como "Agronomia" o
  "Constitucion", "Boca" → "La Boca") y documentarlo en la sección 15.

### Diagramas
- [ ] Exportar el DER: pegar el bloque Mermaid de `DER.md` en <https://mermaid.live>, descargar
  PNG o SVG y guardarlo como `documentacion/DER.png`.
- [ ] Preguntar a los docentes si aceptan la notación pata de gallo o si quieren la notación de
  Chen vista en clase. Si piden Chen, redibujarlo en draw.io con las mismas entidades y
  cardinalidades.

### Evidencia
- [ ] **Sección 13:** sacar capturas de la versión web (`npx expo start --web`) siguiendo la lista
  sugerida del informe y guardarlas en `documentacion/capturas/`.
- [ ] **Sección 14:** revisar los números del benchmark (están tomados de
  `backend/dev/resultados/benchmark.csv`). Opcional: un gráfico.

### Redacción
- [ ] Integrantes, fecha, link al repo y herramienta de gestión de tareas (sección 11).
- [ ] Sección 15: sumar problemas propios del grupo.
- [ ] Sección 16: conclusiones (hay ideas sugeridas).
- [ ] Releer todo para que suene al grupo: en la defensa **cualquier integrante** puede ser
  consultado sobre cualquier parte.

## Cómo generar el PDF

Opción simple: abrir `informe.md` en VS Code con la extensión *Markdown PDF* (o pegarlo en Google
Docs) y exportar. Para que el DER salga en el PDF, insertar `DER.png` como imagen en la sección 5.

## Qué mostrar en la presentación

La consigna pide mostrar el problema, el dataset, el DER, el modelo relacional, el modelo NoSQL,
la arquitectura, la app funcionando, el uso de los dos motores, una consulta representativa y las
conclusiones. Guion sugerido para la parte en vivo (versión web, compartiendo pantalla):

1. Login y recorrido por Inicio, detalle de un lugar y un check-in (CRUD).
2. Mi pasaporte y Ranking: las consultas complejas.
3. **Perfil → Motor de base de datos:** abrir el mismo ranking o pasaporte en MySQL y en HBase y
   mostrar la barra de diagnóstico (consultas ejecutadas y ms). Ahí se ve el backend polimórfico.
4. Explicar por qué las escrituras siempre van a MySQL y se replican a HBase.
5. Mostrar la tabla de la sección 14 (cuándo gana cada motor).
