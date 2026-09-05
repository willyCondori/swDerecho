# modulo_ia/services/entidad_service.py
from modulo_catalogo.models.entidad import EntidadJuridica
from modulo_catalogo.services.entidad_matching import detectar_entidades_en_texto
from modulo_ia.models.embedding import EntidadDetectadaCaso


class EntidadDetectionService:
    """
    Detecta qué entidades jurídicas del catálogo (EntidadJuridica)
    aparecen mencionadas en los chunks de un caso, usando matching de
    texto simple (substring, case-insensitive) vía
    modulo_catalogo.services.entidad_matching.detectar_entidades_en_texto
    — la misma función que usa ArticuloEntidadService para detectar
    entidades en artículos, así ambos flujos quedan sincronizados con
    un solo criterio de detección.

    No requiere NER ni modelos nuevos: reutiliza el catálogo de
    entidades ya cargado y conecta directamente con el score_entidades
    que ya existe en RankingService pero que hasta ahora nunca recibía
    datos.
    """

    @classmethod
    def detectar_para_caso(cls, chunks):
        EntidadDetectadaCaso.objects.filter(chunk__in=chunks).delete()

        entidades_catalogo = list(
            EntidadJuridica.objects.filter(estado=True).values("id", "nombre")
        )

        detectadas = []
        for chunk in chunks:
            for entidad in detectar_entidades_en_texto(chunk.contenido, entidades_catalogo):
                detectadas.append(
                    EntidadDetectadaCaso(
                        chunk=chunk,
                        valor_detectado=entidad["nombre"],
                        score=1.0,  # match exacto de catálogo, no hay grado parcial
                    )
                )

        return EntidadDetectadaCaso.objects.bulk_create(detectadas)