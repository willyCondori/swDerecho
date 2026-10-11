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

Las migraciones `modulo_ia/0004_busqueda_articulos_caso.py` y
`modulo_ia/0005_ranking_vigencia.py` contienen su definición y su reversión.
`modulo_ia/0009_excluir_articulos_no_utiles.py` excluye, antes del límite
de candidatos, los artículos cuya última valoración en ese caso sea «No útil».
La decisión se comparte entre los usuarios que pueden acceder al caso y
persiste al cambiar la descripción, el PDF o el modelo. «Útil» y «Sin valorar»
revocan la exclusión. Las reglas de sugerencias también aplican esa decisión.
Las valoraciones no eliminan artículos del catálogo ni afectan otros casos.
Se utiliza desde `RankingService` mediante parámetros, sin
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
activas. Antes del límite se excluyen las unidades que no sean artículos y
las derogaciones/abrogaciones totales confirmadas con fecha de efecto cumplida
(día de Bolivia). Las afectaciones parciales, futuras, pendientes, descartadas
o restauradas no excluyen el artículo. Las figuras complementarias usan el
mismo filtro. Se conservan hasta 15 resultados principales y hasta 3 sugerencias
complementarias adicionales, sin duplicados y con los principales primero.
El filtro de rama es opcional. El límite se acota entre 1 y 200.
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
en el serializer público. Las páginas escaneadas sin texto legible se transcriben
con el OCR local compartido con el catálogo. Se requiere Tesseract y su idioma
español (`spa`); debe estar en PATH, en `C:/Program Files/Tesseract-OCR`, o
configurado mediante `PDF_TESSERACT_CMD`. `PDF_OCR_IDIOMA` permite cambiar el idioma.
La caché incluye la versión del extractor y el idioma. Si falta el motor o no
se obtiene texto legible, el análisis falla con un mensaje visible en el detalle
del caso y conserva el resultado anterior. Solo los PDF realmente vacíos pueden
usar la descripción de respaldo. No se extraen hechos ni petitorios.

## Documentos de normas

La pantalla `/documentos` reúne los PDF del catálogo, con búsqueda por nombre
de archivo/norma y filtros por norma, rama y versión del archivo. La versión
actual/reemplazada no expresa vigencia jurídica. La carga enlaza al flujo de
revisión existente; la descarga está disponible a los roles operativos y la
eliminación requiere administrador. Los PDF con avisos, versiones de artículos
o disposiciones siguen protegidos. El guardado exclusivo (`xb`) agrega sufijos
cuando el nombre coincide y evita sobrescribir otro archivo.

Los PDF de normas y de casos se pueden abrir en un lector integrado con
navegación por páginas, selección de texto y zoom. El lector solicita el
archivo a los endpoints autenticados existentes; no utiliza las rutas públicas
de media. Al cerrar cancela la petición pendiente y libera la URL temporal.
La descarga sigue disponible. El acceso «PDF original» de los artículos también
abre este lector, incluida la selección de una fuente histórica.

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
