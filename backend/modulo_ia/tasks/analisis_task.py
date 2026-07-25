from celery import shared_task

from core.permissions.auditoria_mixin import registrar_auditoria


@shared_task(bind=True)
def ejecutar_analisis_caso(self, caso_id: int):
    """
    Pipeline IA completo para un caso:
      1. Chunking: parte el texto del caso en fragmentos.
      2. Embeddings: vectoriza cada fragmento.
      3. Entidades: detecta qué entidades jurídicas del catálogo
         (EntidadJuridica) aparecen en el texto del caso, vía matching
         simple de texto. Alimenta el score_entidades del ranking, que
         hasta ahora siempre daba 0 por falta de este paso.
      4. Ranking: compara contra los embeddings de artículos y
         selecciona los TOP_N más relevantes con la fórmula ponderada
         (cola de prioridad de tamaño fijo, ver RankingService).
      5. Análisis IA (GPT4All): genera resumen jurídico, fortalezas,
         debilidades y estrategias. PENDIENTE de integrar — por ahora
         se guardan los campos en None como placeholder.
      6. Guarda/actualiza el ResultadoCaso asociado.

    Reporta progreso vía self.update_state para que
    EstadoTareaView pueda mostrarlo.
    """
    from modulo_casos.models.caso import Caso
    from modulo_casos.models.resultado_caso import ResultadoCaso
    from modulo_ia.services.chunking_service import ChunkingService
    from modulo_ia.services.embedding_service import EmbeddingService
    from modulo_ia.services.entidad_service import EntidadDetectionService
    from modulo_ia.services.ranking_service import RankingService

    caso = Caso.objects.get(pk=caso_id)

    try:
        self.update_state(state="STARTED", meta={"paso": "chunking", "progreso": 10})
        chunks = ChunkingService.crear_chunks(caso)

        self.update_state(state="STARTED", meta={"paso": "embeddings", "progreso": 30})
        embeddings = EmbeddingService.generar_para_caso(chunks)

        self.update_state(state="STARTED", meta={"paso": "entidades", "progreso": 45})
        entidades = EntidadDetectionService.detectar_para_caso(chunks)

        self.update_state(state="STARTED", meta={"paso": "ranking", "progreso": 65})
        resultados = RankingService.calcular_ranking(caso)

        self.update_state(state="STARTED", meta={"paso": "analisis_ia", "progreso": 85})
        # PENDIENTE: integrar GPT4All. Por ahora se guarda sin contenido
        # generado; el caso ya queda marcado como "analizado" porque
        # existe el ResultadoCaso asociado (ver CasoDetailPage/frontend).
        resumen_ia      = None
        fortalezas_ia   = None
        debilidades_ia  = None
        estrategias_ia  = None
        observaciones_ia = None

        resultado_caso, _creado = ResultadoCaso.objects.update_or_create(
            caso=caso,
            defaults={
                "resumen"       : resumen_ia,
                "fortalezas"    : fortalezas_ia,
                "debilidades"   : debilidades_ia,
                "estrategias"   : estrategias_ia,
                "observaciones" : observaciones_ia,
            },
        )

        registrar_auditoria(
            usuario=caso.usuario,
            tabla="casos",
            accion="ANALYZE",
            registro_id=caso.pk,
            metadata={
                "chunks": len(chunks),
                "embeddings": len(embeddings),
                "entidades_detectadas": len(entidades),
                "articulos_rankeados": len(resultados),
                "resultado_caso_id": resultado_caso.pk,
            },
        )

        self.update_state(state="SUCCESS", meta={"paso": "completado", "progreso": 100})

        return {
            "caso_id": caso_id,
            "chunks": len(chunks),
            "entidades_detectadas": len(entidades),
            "articulos_rankeados": len(resultados),
            "resultado_caso_id": resultado_caso.pk,
        }

    except ValueError as e:
        # Errores esperados (ej. caso sin texto) -> no reintentar
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise