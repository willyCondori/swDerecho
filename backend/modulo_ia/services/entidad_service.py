# modulo_ia/services/entidad_service.py
from modulo_catalogo.models.entidad import EntidadJuridica
from modulo_ia.models.embedding import EntidadDetectadaCaso


class EntidadDetectionService:
    """
    Detecta qué entidades jurídicas del catálogo (EntidadJuridica)
    aparecen mencionadas en los chunks de un caso, usando matching de
    texto simple (substring, case-insensitive). No requiere NER ni
    modelos nuevos: reutiliza el catálogo de entidades ya cargado y
    conecta directamente con el score_entidades que ya existe en
    RankingService pero que hasta ahora nunca recibía datos.
    """

    @classmethod
    def detectar_para_caso(cls, chunks):
        EntidadDetectadaCaso.objects.filter(chunk__in=chunks).delete()

        entidades_catalogo = list(
            EntidadJuridica.objects.filter(estado=True).values("id", "nombre")
        )

        detectadas = []
        for chunk in chunks:
            texto = chunk.contenido.lower()
            for entidad in entidades_catalogo:
                nombre = entidad["nombre"].strip().lower()
                if nombre and nombre in texto:
                    detectadas.append(
                        EntidadDetectadaCaso(
                            chunk=chunk,
                            valor_detectado=entidad["nombre"],
                            score=1.0,  # match exacto de catálogo, no hay grado parcial
                        )
                    )

        return EntidadDetectadaCaso.objects.bulk_create(detectadas)