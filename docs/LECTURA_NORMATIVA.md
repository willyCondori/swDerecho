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
OLLAMA_NORMATIVO_KEEP_ALIVE=0
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=8
GACETA_PAUSA_SEGUNDOS=0.5
```

Configura `OLLAMA_NUM_PARALLEL=1` y `OLLAMA_MAX_LOADED_MODELS=1` en el proceso
que ejecuta Ollama. El cliente también serializa las inferencias. Los embeddings
se generan en CPU y Qwen se descarga de memoria al acabar cada consulta.
Esto reduce la competencia por VRAM; el rendimiento en el servidor de 4 GB
debe medirse allí. El tamaño del archivo del modelo no es su consumo total.

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
