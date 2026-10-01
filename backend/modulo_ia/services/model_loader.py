# modulo_ia/services/model_loader.py
"""
Punto único de carga del modelo de Sentence Transformers y de la versión
"activa" con la que se generan y comparan embeddings.

Antes esto estaba duplicado en tres archivos (embedding_service.py,
carga_pdf_service.py y regenerar_embeddings_articulos.py), cada uno con
su propio caché de modelo y su propio DIMENSION_VECTOR. Con el
versionado de embeddings (ver modulo_ia/models/embedding.py) eso pasa de
ser una duplicación inocua a un riesgo real: bastaría con que uno de los
tres quedara desactualizado para que se generen embeddings con el modelo
equivocado bajo la etiqueta de versión equivocada.

- settings.SENTENCE_TRANSFORMER_MODEL: qué le pasás a SentenceTransformer(...)
  para cargarlo — un id de Hugging Face ("sentence-transformers/paraphrase-
  mpnet-base-v2") o una ruta local al modelo ya afinado.
- settings.EMBEDDING_MODEL_VERSION: la etiqueta corta con la que ESE modelo
  queda identificado en la base de datos (EmbeddingArticulo.modelo_version /
  EmbeddingChunk.modelo_version). Separar el "qué cargar" del "cómo se
  llama" permite que un modelo afinado en una ruta local como
  /models/sw-derecho-embeddings-v1 quede etiquetado simplemente como
  "sw-derecho-embeddings-v1", sin la ruta completa.

Cambiar de modelo (por ejemplo, pasar del modelo base al afinado con el
dataset de TSJ) es cambiar estas dos variables de entorno y correr
`python manage.py regenerar_embeddings_articulos --version <la nueva>` —
los embeddings de la versión anterior quedan intactos en la base, así que
volver atrás es solo volver a cambiar las variables, sin regenerar nada.
"""
from django.conf import settings

DIMENSION_VECTOR = 768  # debe coincidir con VectorField(dimensions=768) en modulo_ia/models/embedding.py

_modelo_cache = {}  # cacheado por SENTENCE_TRANSFORMER_MODEL, a nivel de módulo/worker


def obtener_modelo():
    """Carga (o reutiliza del caché) el SentenceTransformer configurado."""
    ruta_modelo = settings.SENTENCE_TRANSFORMER_MODEL
    if ruta_modelo not in _modelo_cache:
        import logging
        from sentence_transformers import SentenceTransformer
        logging.getLogger(__name__).info("Cargando modelo de embeddings: %s", ruta_modelo)
        _modelo_cache[ruta_modelo] = SentenceTransformer(ruta_modelo)
    return _modelo_cache[ruta_modelo]


def version_activa() -> str:
    """La etiqueta de versión con la que se generan y comparan embeddings ahora mismo."""
    return settings.EMBEDDING_MODEL_VERSION
