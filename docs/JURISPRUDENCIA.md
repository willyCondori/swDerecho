# Jurisprudencia del TSJ

## Consulta desde el sistema

- **Fuentes y documentos → TSJ · Genesis** (`/catalogo/tsj`): búsqueda
  paginada en el servicio oficial, enlace a la fuente y opción de incorporar
  una resolución para guardarla y generar sus embeddings en segundo plano.
  Administrador y abogado pueden incorporar; asistente solo consulta.
- **Catálogo jurídico → Jurisprudencia** (`/jurisprudencia`): listado paginado
  de resoluciones guardadas, búsqueda por texto/número/expediente, filtros de
  fecha, sala, departamento y disponibilidad para IA. El lector muestra el
  texto completo dentro del sistema. Los contadores se actualizan cada
  20 segundos, por lo que reflejan lo incorporado durante la carga masiva.
- Los resultados de jurisprudencia de un caso incluyen un acceso al mismo
  lector de resoluciones, sin descargar archivos.

La incorporación individual conserva el patrón de tareas de Gaceta: progreso
consultable por su usuario, cache del servidor y recuperación del identificador
en la sesión del navegador. La carga masiva por contenedor es independiente de
esas tareas; actualizar la aplicación no reinicia dicha carga.

El cliente está adaptado a `willyCondori/tsj_scraper`, revisión
`51a4ee061520d1e669caf306d0e145f364fdf731`. Usa Genesis:
`POST https://apigenesis.tsj.bo/api/v1/resoluciones/busqueda_avanzada`
y `GET https://apigenesis.tsj.bo/api/v1/resoluciones/{id}`.

La sincronización consulta el corpus público penal con una búsqueda general
(`penal` por defecto), obtiene los detalles, limpia HTML, guarda texto y
metadatos, fragmenta y genera vectores de 768 dimensiones. Las credenciales
de acceso van en `TSJ_API_KEY` y `TSJ_API_USERNAME`, nunca en código ni Git.
En Docker, configurar `.env.docker` y recrear el backend para aplicar cambios.

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.actual.yaml up -d --build
docker compose --env-file .env.docker -f compose.yaml -f compose.actual.yaml exec -T backend python manage.py sincronizar_jurisprudencia_tsj --paginas 1 --limite 5
```

Para ampliar la colección, ejecutar sin `--limite`, eligiendo `--paginas N`.
`--desde-pagina N` permite continuar un recorrido. Se hacen pausas de 1.5 s
entre consultas y reintentos limitados para 429/5xx. Los JSON idénticos se omiten;
los cambios reemplazan los fragmentos afectados y sus embeddings. Si solo cambia
la versión del modelo, se conservan los vectores de la versión anterior.
El comando reporta resoluciones rechazadas y termina con error si la carga fue
parcial, conservando lo importado correctamente. Las páginas del buscador pueden
cambiar al incorporarse resoluciones; conviene volver a recorrerlas periódicamente.
No se ejecuta una descarga masiva al iniciar el servidor ni al analizar un caso.

También se pueden importar los JSON ya descargados por el scraper:

```powershell
cd backend
python manage.py importar_jurisprudencia_tsj --directorio RUTA/data/raw
```

El directorio debe estar disponible dentro del contenedor si se usa Docker;
por ejemplo copiarlo temporalmente a `/tmp/tsj-raw` con `docker cp`.
También está montado, en modo de solo lectura, `backend/data/jurisprudencia`
como `/app/data/jurisprudencia`. La colección entregada contiene otra carpeta
`raw` dentro de `raw`, por lo que su directorio de importación es
`/app/data/jurisprudencia/raw/raw`.
No se utiliza el ZIP de pares hechos–artículo como si fueran resoluciones completas.

Para importar esa colección en segundo plano, sin bloquear el servidor web:

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.actual.yaml run -d --no-deps --name sw-derecho-jurisprudencia-importacion -e EMBEDDING_BATCH_SIZE=32 -e OMP_NUM_THREADS=4 -e MKL_NUM_THREADS=4 backend python manage.py importar_jurisprudencia_tsj --directorio /app/data/jurisprudencia/raw/raw --progreso-cada 10
docker logs --tail 30 sw-derecho-jurisprudencia-importacion
docker inspect sw-derecho-jurisprudencia-importacion --format '{{.State.Status}} {{.State.ExitCode}}'
```

El contenedor conserva los logs al terminar. `running` significa que sigue
trabajando; `exited 0` indica finalización correcta. Un código distinto de cero
requiere revisar los rechazos o errores. Para reanudar una carga interrumpida,
volver a ejecutar el mismo comando con otro nombre de contenedor: las resoluciones
ya actualizadas se omiten. Cada resolución se guarda completa con sus vectores
en una transacción; no hay archivos movidos ni borrados. La carga de 21.697
resoluciones puede tardar varias horas en CPU y solo lo ya importado estará
disponible para los análisis mientras el proceso continúa.

Al pulsar «Analizar caso con IA», el pipeline compara los embeddings de los
hechos (descripción o texto del PDF/OCR, según el flujo existente) con los de
jurisprudencia en PostgreSQL/pgvector. Solo compara versiones iguales del modelo;
selecciona el fragmento más parecido de cada resolución y guarda hasta 5
resoluciones distintas con su evidencia textual, puntuación y huella de fuente.
Ambos rankings se publican en la misma transacción del análisis del caso.

`GET /api/casos/{id}/jurisprudencia/` devuelve los resultados bajo los mismos
permisos que el detalle del caso. La interfaz muestra número, fecha, sala,
expediente, fragmento, similitud y enlaces oficiales. Distingue corpus vacío,
modelo sin embeddings, otra rama y ausencia de coincidencias. Los cambios
de descripción/PDF/modelo o de fuente se señalan como desactualizados;
se actualizan al volver a analizar.

Los hechos del caso permanecen en SW Derecho: no se transmiten al buscador TSJ.
La API externa se usa durante la sincronización, fuera de los requests de análisis.
Una caída del TSJ no impide consultar resoluciones ya incorporadas.

La colección actual cubre materia Penal. Los documentos sin contenido textual
se rechazan con un mensaje: el OCR masivo de los PDF externos del TSJ no forma
parte de esta conexión. No hay garantía de que la búsqueda `penal` incluya toda
la jurisprudencia publicada. La API fue comprobada el 8 de octubre de 2026:
respondió HTTP 200 en listado y detalle.

`JURISPRUDENCIA_TOP_N` (1–20, por defecto 5) y `JURISPRUDENCIA_UMBRAL`
(por defecto 0.65 de similitud coseno) son configurables. El umbral inicial no
está calibrado sobre un benchmark de jurisprudencia. El modelo actual fue afinado
para hechos–artículos: reutilizarlo permite comparar vectores coherentes, pero sus
métricas de artículos no demuestran precisión en jurisprudencia. Se necesita
evaluación con hechos y resoluciones pertinentes revisadas antes de atribuirle
una precisión jurídica. Los resultados son candidatos semánticos y conservan
el contexto para revisión; no se asume que una cita implique aplicabilidad.

Pruebas: importación idempotente, actualización de fuente/modelo, fallo de
vectorización sin pérdida de datos, consulta real pgvector, deduplicación,
versiones incompatibles, permisos, rollback conjunto del análisis, contrato de
API y renderizado/refresco/errores de la interfaz.

Validación local del 8 de octubre de 2026: 546 pruebas de backend y 201 de
frontend aprobadas; compilación Docker correcta. Carga inicial desde la API:
5 resoluciones reales y 200 embeddings. Se comprobó el pipeline completo y
el endpoint con el modelo real usando un caso temporal, revertido después
de la comprobación. Esta prueba acredita la conexión y recuperación; no
constituye una evaluación de pertinencia jurídica. La colección inicial es
una muestra y debe ampliarse con el comando de sincronización.
