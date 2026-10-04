# Lectura local y vigencia normativa

Rama: `feature/lectura-ia-vigencia-normativa`.

## Preparación

Instala las dependencias de `backend/requirements.txt` y aplica `python manage.py migrate` desde `backend`.
La lectura predeterminada es **Algoritmos locales**. No utiliza Ollama ni Qwen.
Sentence Transformers se conserva para los embeddings y la búsqueda del catálogo.

```dotenv
LECTURA_NORMATIVA_MOTOR=clasico
OLLAMA_NORMATIVO_PRELOAD_STARTUP=False
OLLAMA_NORMATIVO_KEEP_ALIVE=5m
EMBEDDING_PRELOAD_STARTUP=True
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=8
GACETA_PAUSA_SEGUNDOS=0.5
PDF_OCR_IDIOMA=spa
```

El backend precarga una instancia de Sentence Transformers por proceso; Qwen
solo se solicita cuando se selecciona explícitamente su opción de lectura.
Para utilizarla, descarga `ollama pull qwen3.5:2b` y mantén Ollama disponible en
`http://127.0.0.1:11434`. El tiempo de residencia predeterminado es cinco minutos.
Configura `OLLAMA_NUM_PARALLEL=1` y `OLLAMA_MAX_LOADED_MODELS=1` en Ollama.
Un modelo residente de una ejecución anterior se puede liberar con
`ollama stop qwen3.5:2b`. Reinicia el backend después de modificar su `.env`.

Para PDFs escaneados en el modo de algoritmos, instala Tesseract con el idioma
español. Si no está en PATH, configura `PDF_TESSERACT_CMD` con la ruta al ejecutable.
El OCR se ejecuta por página en CPU, con un hilo; los PDFs digitales no lo necesitan.
El texto reconocido requiere contrastarse con el original. Sin Tesseract, un
escaneo devuelve un error explicativo, sin cambiar automáticamente a Qwen.

Ejecuta Django en **un proceso** para las tareas y la caché locales.
La revisión de ambos motores se realiza en segundo plano. Los hilos no sobreviven a
un reinicio del servidor: vuelve a revisar el PDF o repite la sincronización.
Los documentos oficiales ya descargados y los errores de cada documento
permanecen en PostgreSQL. No uses varios workers con la caché local:
para distribuir tareas hace falta una cola durable y una caché compartida.

## Uso

En **Cargar artículos → Lectura del documento**, elige **Algoritmos locales**, la norma y el PDF. Revisa la lista
de artículos y, en una tabla aparte, disposiciones finales, derogatorias y abrogatorias.
Las transitorias y adicionales no se importan.
El texto de PDFs digitales se reconstruye desde el original; páginas escaneadas
se transcriben una por una y muestran un aviso para contrastarlas con el PDF.
Si el PDF contiene varias normas, la revisión permite elegir una sección sin
recortar el archivo original. Los anexos no se mezclan con la norma principal.
Si un número de artículo contiene versiones distintas, debes elegir una alternativa
o ignorarlo. Las versiones sin resolver no se importan ni generan efectos;
impiden el reemplazo completo, pero permiten cargar otras unidades inequívocas.
Las repeticiones de texto íntegro idéntico se deduplican.

Los efectos de los artículos seleccionados y de todas las disposiciones importadas
se guardan como detecciones pendientes.
No se modifica automáticamente el texto del artículo afectado. En **Normas →
Verificar afectaciones**, el administrador revisa los destinos encontrados, comprueba
fechas y fuente, y confirma o descarta. Los artículos y los resultados de casos
muestran avisos previos con la norma causante, fecha, alcance y PDF de respaldo.

La abrogación completa afecta a la norma y acompaña a todos sus artículos.
La derogación parcial identifica parágrafo, inciso, numeral, párrafo o frase;
solo el fragmento inequívoco confirmado se resalta como derogado. Si no se
puede localizar, hay que indicar el fragmento exacto antes de confirmar.
El resto del artículo se conserva. Las versiones anteriores siguen registradas.

Ejemplos admitidos: la final tercera que abroga el Decreto Ley 11080; una ley que
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
relacionadas indirectamente. «Revisar e incorporar» usa el motor seleccionado para leer el mismo PDF.

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


## Disposiciones en su propia tabla

Las disposiciones finales, derogatorias y abrogatorias se guardan en
`disposiciones_normativas`, asociadas a su PDF. No se guardan como artículos,
no generan embeddings y no participan en el ranking de artículos. Las
transitorias y adicionales no se importan. El catálogo y la revisión del PDF
muestran una tabla propia de disposiciones.

La migración 0015 crea la tabla. La 0016 copia las disposiciones antiguas con
fuente disponible y retira todas las unidades que no son artículos del catálogo
activo; conserva sus registros originales por el historial y las referencias.
Ambas migraciones ya se aplicaron en la base local. En otro servidor ejecuta
`python manage.py migrate` y después, para documentos existentes,
`python manage.py recuperar_disposiciones`.

El aviso se muestra antes y después de cargar el documento y en la disposición
del catálogo. Los efectos de las disposiciones se registran aunque no se
seleccionen artículos. Las derogaciones y abrogaciones expresas con una norma
inequívoca se detectan por su evidencia literal también en el motor clásico;
la lectura de Qwen sigue disponible para otras cláusulas.

Comprobación del PDF real de la Ley 1636 ya cargado: dos disposiciones (DF ÚNICA
y DD ÚNICA) y dos avisos pendientes de derogación: Parágrafo III del Artículo
323 Bis y todo el Artículo 281 Quater. El numeral 2 de la lista no se interpreta
como Artículo 2. Los avisos pendientes duplicados o producidos por ese error
se retiraron de la vista, conservando su evidencia. No se cambió ninguna
confirmación ni se aplicaron automáticamente derogaciones.

En la base local existen los artículos 323 y 281, pero no los destinos exactos
323 Bis y 281 Quater: quedan como avisos hasta cargar esos artículos. No se
aplica el efecto a artículos con números o sufijos diferentes.

La recuperación también procesó los PDFs disponibles de las normas anteriores;
cinco registros apuntan a PDFs que ya no están físicamente en `media`. Esos
documentos requieren recuperar el archivo o subirlo nuevamente para reanalizarlos.

Validación: 288 pruebas de backend y 112 de frontend aprobadas. Compilación
correcta y lint sin errores nuevos. La recuperación incluye una prueba de
repetición para evitar avisos duplicados.


### Volver a la pantalla de carga

Al navegar dentro de la aplicación, la revisión conserva el PDF original, el avance y el resultado en memoria de la sesión. Volver a «Cargar artículos» retoma el progreso sin iniciar otra lectura; si ya terminó, presenta la revisión para confirmarla. La carga confirmada consulta su tarea del servidor, incluso si terminó mientras el usuario estaba fuera. Antes de ofrecer el formulario se verifica si hay una carga activa. Estos datos se eliminan al cambiar de usuario o cerrar sesión. La revisión en memoria no sobrevive a recargar completamente el navegador; el servidor continúa trabajando.

Los avisos no aplican efectos automáticamente. Las reglas temporales y las cláusulas generales son informativas. Un efecto concreto con destino cargado se revisa en Catálogo → Normas por un usuario autorizado. Si falta la norma o el artículo exacto, es solo un aviso: primero debe incorporarse ese destino y después verificarse la fuente, la fecha y el alcance. Artículo 323 no sustituye a 323 Bis; artículo 281 no sustituye a 281 Quater. Los contadores de artículos importados son distintos de los efectos detectados en las disposiciones.


## Algoritmos locales

La opción analiza cabeceras, artículos y disposiciones finales, derogatorias y
abrogatorias. Conserva sufijos como Bis, Quater y Octies y distingue referencias
o textos reformados citados de los artículos propios de la norma.
Detecta modificaciones, incorporaciones, derogaciones y abrogaciones expresas,
sus destinos y alcances, notas históricas y reglas temporales. Una cláusula
general o con destinos ambiguos produce un aviso para revisión; no permite
deducir derogaciones tácitas. Las transitorias y adicionales se excluyen.
No hace llamadas a Qwen durante esta lectura ni durante el análisis de efectos.

El texto afectado no se reescribe automáticamente. Los efectos se presentan
como avisos y siguen el flujo de confirmación con fuente, fecha y alcance.
La recuperación posterior conserva la sección y las alternativas seleccionadas.

Una lectura local del Código Penal de SEGIP de 110 páginas, incluyendo separación
de seis normas anexas y detección de efectos, tomó aproximadamente 2,6 segundos.
Esta medición no incluye embeddings, publicación en la base de datos ni OCR;
el tiempo depende del documento y del equipo.
