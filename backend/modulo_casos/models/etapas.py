from django.db import models


class EtapaCaso(models.TextChoices):
    """
    Etapas del seguimiento de un caso, en orden cronológico habitual.

    Lista fija y genérica (aplica a cualquier rama del derecho). Se
    define acá, sin importar otros modelos, para poder reutilizarla en
    Caso y en SeguimientoCaso sin imports circulares.
    """
    REGISTRADO               = "registrado", "Caso registrado"
    EN_ANALISIS              = "en_analisis", "En análisis y estrategia"
    INVESTIGACION_PRELIMINAR = "investigacion_preliminar", "Investigación preliminar"
    DENUNCIA_DEMANDA         = "denuncia_demanda", "Denuncia / demanda presentada"
    AUDIENCIAS               = "audiencias", "En audiencias"
    JUICIO                   = "juicio", "En juicio (etapa probatoria)"
    SENTENCIA                = "sentencia", "Sentencia emitida"
    APELACION                = "apelacion", "Apelación / recursos"
    CERRADO                  = "cerrado", "Cerrado / archivado"
