# Optimización de extracción y búsqueda

## Instalación

Desde `backend`, con el entorno Python del proyecto activado:

```powershell
python manage.py migrate
```

Las migraciones añaden tres índices GIN de trigramas, la extensión `pg_trgm`,
una tabla de texto extraído para documentos del caso y la función SQL
`buscar_articulos_caso`. No regeneran embeddings ni cambian su versión.
Los índices se aplican a `UPPER(campo)`, la expresión utilizada por las
consultas `icontains` de Django en PostgreSQL.

## Función de PostgreSQL

La migración `modulo_ia/0004_busqueda_articulos_caso.py` contiene su definición
y su reversión. Se utiliza desde `RankingService` mediante parámetros, sin
concatenar valores del usuario en SQL.

```sql
-- caso_id, versión del modelo, rama_id (NULL = todas), candidatos por chunk
SELECT * FROM buscar_articulos_caso(
    123, 'version-activa-del-modelo', NULL, 50
);
```

La versión debe coincidir con `EMBEDDING_MODEL_VERSION`. La consulta devuelve
`chunk_id`, `articulo_id` y `distancia`; los vectores permanecen en PostgreSQL.
Una unión LATERAL calcula los candidatos de cada fragmento en una llamada.
Esto reduce viajes entre Python y PostgreSQL; el cálculo de distancia sigue
siendo exacto y continúa dependiendo del número de artículos y fragmentos.

Solo participan embeddings de la misma versión, artículos activos y normas
activas. El filtro de rama es opcional. El límite se acota entre 1 y 200.
Si un chunk no tiene candidatos, devuelve una fila con artículo/distancia NULL;
el servicio la omite. Si no existen embeddings de chunks de esa versión, no
devuelve filas y el servicio informa que debe reanalizarse el caso.

La función usa `SECURITY INVOKER`: mantiene los permisos del usuario de BD.
No es un endpoint público; la autorización del caso sigue en la API existente.
En llamadas directas a la BD, el llamante debe comprobar acceso al caso.

## Embeddings y extracción

`EMBEDDING_BATCH_SIZE` controla los lotes; el valor predeterminado es 16.
Se puede configurar en `.env` y reiniciar el backend. Ajustarlo a 8, 16 o 32
requiere medir memoria y tiempo con documentos representativos.

Los embeddings se calculan antes de la transacción de publicación.
Los chunks y resultados se reemplazan atómicamente: un fallo posterior restaura
el análisis previo. En la carga de normas se conservan los errores por artículo
y el reemplazo atómico de la norma, con savepoints para fallos de escritura.

El texto de un PDF del caso se reutiliza por documento, SHA-256 del archivo y
versión del extractor/pypdf. Un PDF cambiado invalida la caché incluso si conserva
su ruta. La tabla se elimina en cascada al borrar el documento y no se incluye
en el serializer público. Los PDF sin texto siguen usando la descripción de
respaldo; no se incorporó un motor OCR ni se modificó la estrategia de fragmentación.

## Contrato del catálogo

El listado admite `compacto=true`: devuelve `contenido_preview` (360 caracteres)
y omite `contenido`. Este modo queda disponible como opción de la API.
La interfaz solicita el listado con el contenido completo y lo muestra al
expandir, sin consultas adicionales.
`por_norma` y `por_rama` ahora devuelven `{count, next, previous, results}`,
con `page` y `page_size`, igual que el listado general.

## Límites y comprobaciones

No se activó HNSW: su búsqueda aproximada requiere comparar recuperación y
relevancia contra esta búsqueda exacta antes de cambiar el ranking jurídico.
No se modificaron hilos, colas, caché de progreso ni polling para concurrencia.

Las pruebas cubren una consulta para varios chunks, cero consultas adicionales
para entidades precargadas, filtros por rama/versión/estado, upsert por lote,
invalidez del caché PDF, cálculo fuera de transacción, rollback y visualización
del contenido completo en la interfaz. No sustituyen una medición de tiempos
con el modelo y los documentos reales ni una prueba de carga.
