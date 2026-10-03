# Lectura local y vigencia normativa

Rama: `feature/lectura-ia-vigencia-normativa`.

## Preparación

Instala las dependencias ya declaradas en `backend/requirements.txt`. Descarga
el modelo con `ollama pull qwen3.5:2b` y mantén Ollama disponible en
`http://127.0.0.1:11434`. Aplica `python manage.py migrate` desde `backend`.
El tag oficial de 2B es **qwen3.5:2b**: https://ollama.com/library/qwen3.5:2b.

Para el servidor estimado de 12 GB RAM y 4 GB VRAM:

```dotenv
OLLAMA_NORMATIVO_MODELO=qwen3.5:2b
OLLAMA_NORMATIVO_CONTEXTO=4096
OLLAMA_NORMATIVO_TIMEOUT=180
OLLAMA_NORMATIVO_KEEP_ALIVE=-1
EMBEDDING_PRELOAD_STARTUP=True
OLLAMA_NORMATIVO_PRELOAD_STARTUP=True
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=8
GACETA_PAUSA_SEGUNDOS=0.5
```

Configura `OLLAMA_NUM_PARALLEL=1` y `OLLAMA_MAX_LOADED_MODELS=1` en el proceso
que ejecuta Ollama. El cliente también serializa las inferencias. Los embeddings
se generan en CPU y Qwen permanece cargado en Ollama entre consultas.
Esto reduce la competencia por VRAM; el rendimiento en el servidor de 4 GB
debe medirse allí. El tamaño del archivo del modelo no es su consumo total.

El servidor WSGI/ASGI prepara ambos modelos antes de aceptar peticiones:
Sentence Transformers carga una sola instancia por proceso y ejecuta una
vectorización inicial; Qwen carga sus pesos y contexto en Ollama. El arranque
inicial puede tardar; las peticiones posteriores reutilizan los modelos.
Los comandos `migrate`, `shell` y los tests no hacen esta precarga. Si Ollama no
está disponible, el servidor indica el fallo al iniciar. Para una instalación
sin Qwen, configura `OLLAMA_NORMATIVO_PRELOAD_STARTUP=False`.
Para desactivar también la precarga de embeddings usa `EMBEDDING_PRELOAD_STARTUP=False`.
`keep_alive=-1` evita la descarga por inactividad; un reinicio de Ollama o la
presión de memoria pueden exigir cargar Qwen nuevamente. Comprueba `ollama ps`.

Ejecuta Django en **un proceso** para las tareas y la caché locales.
La revisión de Qwen se realiza en segundo plano. Los hilos no sobreviven a
un reinicio del servidor: vuelve a revisar el PDF o repite la sincronización.
Los documentos oficiales ya descargados y los errores de cada documento
permanecen en PostgreSQL. No uses varios workers con la caché local:
para distribuir tareas hace falta una cola durable y una caché compartida.

## Uso

En **Cargar artículos**, elige Qwen local, la norma y el PDF. Revisa la lista
de artículos y disposiciones transitorias, finales, derogatorias y abrogatorias.
El texto de PDFs digitales se reconstruye desde el original; páginas escaneadas
se transcriben una por una y muestran un aviso para contrastarlas con el PDF.
Cada documento debe corresponder a una norma principal; separa las compilaciones.

Los efectos de las unidades seleccionadas se guardan como detecciones pendientes.
No se modifica automáticamente el texto del artículo afectado. En **Normas →
Verificar afectaciones**, el administrador identifica destinos ambiguos, comprueba
fechas y fuente, y confirma o descarta. Los artículos y los resultados de casos
muestran avisos previos con la norma causante, fecha, alcance y PDF de respaldo.

La abrogación completa afecta a la norma y acompaña a todos sus artículos.
La derogación parcial identifica parágrafo, inciso, numeral, párrafo o frase;
solo el fragmento inequívoco confirmado se resalta como derogado. Si no se
puede localizar, hay que indicar el fragmento exacto antes de confirmar.
El resto del artículo se conserva. Las versiones anteriores siguen registradas.

Ejemplos admitidos: la transitoria tercera derogada por Ley 2446 de
19/03/2003; la final tercera que abroga el Decreto Ley 11080; una ley que
incorpora el parágrafo VI del artículo 25 de la Ley 260. Incorporar un parágrafo
no deroga el artículo. «Todas las disposiciones contrarias» queda como cláusula
general sin asignar derogaciones concretas. Vencer un plazo no deroga una norma.
Abrogar la norma modificatoria tampoco restaura automáticamente el texto anterior.

El 2B requiere controles: puede omitir cabeceras o confundir operaciones.
Se conservan cabeceras literales, se exige evidencia del texto fuente y se
comprueba la parte afectada. Las citas se adjuntan desde el original, sin
pedir al modelo que las repita por cada destino. Si la respuesta alcanza su
límite, el bloque se divide y se reintenta en serie, hasta tres niveles;
un fallo restante no publica una revisión parcial. Las listas expresas de
artículos se contrastan con el texto operativo; no se toma el artículo fuente
como destino ni una norma modificatoria histórica como nueva causante.
Las fechas identificadas por IA son propuestas
que deben contrastarse en la revisión. Una norma anterior o de menor jerarquía
no confirma una derogación de otra posterior o superior. Las reglas judiciales
de constitucionalidad no se interpretan como derogaciones legislativas automáticas.

## Gaceta Oficial

En **Cargar artículos → Documentos penales de la Gaceta**, busca y descarga
los originales. **Páginas por listado = 0** recorre todas las páginas disponibles;
usa fechas para acotar por publicación. La relevancia penal se comprueba en
el título y el cuerpo, con un filtro conservador que puede incluir normas
relacionadas indirectamente. «Revisar e incorporar» envía el mismo PDF a Qwen.

También puedes descargar desde la consola:

```powershell
python manage.py sincronizar_gaceta_penal --max-paginas 1
python manage.py sincronizar_gaceta_penal --max-paginas 0 --desde 2000-01-01
```

Los listados de leyes, decretos y sentencias se recorren y se siguen las categorías
de resoluciones. Algunas fichas de resoluciones agrarias no ofrecen PDF individual:
se informa el faltante. Los enlaces rotos, archivos inválidos y cambios de estructura
se informan sin declarar cobertura completa. Repetir la búsqueda omite archivos
ya registrados y reintenta errores. Un recorrido limitado o con errores indica
cobertura parcial. «Listados recorridos» no certifica toda la normativa penal
existente: solo el universo accesible y el intervalo consultados.

Los PDFs se guardan bajo `MEDIA_ROOT/gaceta_penal`, con hash y procedencia.
Solo se descargan enlaces públicos del dominio oficial; se verifica cada
redirección. El sitio respondió por HTTP en la comprobación de 03/10/2026;
HTTPS no respondió. Esto no equivale a una verificación criptográfica del contenido.

## Código Penal oficial

La Fiscalía ofrece un documento en:
https://www.fiscalia.gob.bo/marco-legal/leyes/codigo-penal
La página está fechada 18/08/2025. Esa fecha es la de publicación del portal,
no certifica que su PDF incorpore todas las reformas posteriores.
Consulta las normas modificatorias en la Gaceta antes de considerar vigente
una consolidación. No se ha certificado una versión consolidada oficial a
03/10/2026. Un proyecto de ley en trámite no se aplica como norma promulgada.


## Precarga y mensajes de las pruebas

Reinicia el backend para activar la precarga WSGI/ASGI. En la comprobación local,
el arranque con ambos modelos tardó aproximadamente 35 segundos y el siguiente
embedding tardó 0,1 segundos reutilizando la misma instancia. Qwen quedó en GPU
con `ollama ps` mostrando `Forever`. Estas mediciones corresponden al equipo
local; no sustituyen una prueba en el servidor de 12 GB RAM y 4 GB VRAM.

Para PDFs con artículos consecutivos y cabeceras reconocibles se consulta a
Qwen sobre las cabeceras y sus índices originales, conservando el texto íntegro
para reconstruir artículos y analizar efectos. Si hay saltos de numeración o
cabeceras ambiguas, se mantiene la lectura de todas las líneas. La Ley 1636
pasó de 17 a 2 bloques de identificación de estructura.

Los tests provocan deliberadamente `Texto no vectorizable`, `callback fallido`,
`carga fallida` y `Fallo de ranking` usando `unittest.mock`. Es normal ver sus
tracebacks en el registro aunque el resultado final sea `OK`; no se ocultan los
errores porque el mismo registro sirve para diagnosticar fallos reales.
Las pruebas de PDFs inválidos también generan HTTP 400 (`Bad Request`).

Un HTTP 401 (`Unauthorized`) en notificaciones señala una petición sin
autenticación válida. Si ocurre en el navegador, vuelve a iniciar sesión; si
continúa, revisa la respuesta de `/api/usuarios/auth/refresh/`. Para un HTTP 400
al subir un PDF real, consulta la respuesta JSON de esa petición: el estado por
sí solo no indica la causa.


Medición completa posterior: Ley 1636, nueve páginas y 37.657 caracteres,
59 segundos con Qwen residente y avisos temporales directos. La medición previa
a eliminar esas inferencias temporales fue de 238 segundos. No se alteraron las
22 unidades ni las reformas identificadas: la disposición derogatoria afecta
todo el Artículo 281 Quater y únicamente el Parágrafo III del Artículo 323 Bis.
Los plazos sin verbos de reforma producen un aviso informativo a partir del
original, sin consultar Qwen ni declarar artículos derogados. Cuando un plazo
acompaña una reforma, se conserva el análisis de Qwen. Son mediciones locales
puntuales, no un tiempo garantizado para todos los PDFs.

Validación: 270 tests de backend y 108 de frontend aprobados; tras el ajuste de
avisos temporales se aprobaron 82 tests de lectura, revisión, vigencia y endpoints
(incluidas dos pruebas nuevas). Compilación frontend correcta y lint sin errores.


## Flujo de derogación y abrogación por confirmación

1. Al revisar un PDF se muestran la norma causante, su fecha, la disposición
   de origen (por ejemplo, disposición final tercera o disposición derogatoria
   única), la norma o artículo afectado, el alcance y la cita literal.
2. Si la norma y, cuando corresponda, el artículo están cargados y coinciden
   inequívocamente, el aviso indica que el destino fue encontrado. Subir el PDF
   registra la detección pendiente; no confirma el cambio jurídico.
3. En **Catálogo → Normas → Verificar afectaciones normativas**, el usuario con
   permiso de revisión (actualmente Administrador) verifica fechas y fundamento
   y pulsa **Confirmar derogación** o **Confirmar abrogación**. Una afectación
   parcial exige identificar el fragmento exacto. Los permisos existentes se
   mantienen.
4. Si el destino no está cargado o es ambiguo, se muestra **Solo aviso**, sin
   botón para aplicar el cambio. El backend también rechaza cualquier intento
   de forzar otro destino. Si se carga después el destino citado, se podrá
   revisar y confirmar la detección pendiente.

Los serializers exponen `estado_vigencia` separado del `estado` administrativo.
Solo una confirmación con efecto alcanzado marca una norma como `abrogada` o un
artículo como `derogado`/`derogado_parcialmente`. Antes de confirmar, y para
efectos futuros, aparece `sin_derogacion_confirmada`: no es una certificación de
vigencia exhaustiva. Los textos y PDFs históricos se conservan. No hay nuevas
migraciones para este ajuste.

Validación de este flujo: 66 pruebas de backend y ocho de interfaz aprobadas;
compilación correcta y lint sin errores nuevos.
