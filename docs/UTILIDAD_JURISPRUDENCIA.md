# Valoración de jurisprudencia por caso

La jurisprudencia utiliza «Útil», «No útil» y «Sin valorar», como los artículos.
Las útiles se muestran en «Jurisprudencia seleccionada» y las pendientes en
«Jurisprudencia sin valorar». Las descartadas permanecen en un bloque plegado
desde el que se puede corregir la decisión. Las recomendaciones complementarias
mantienen esa condición aun cuando el usuario las marque como útiles.

`ValoracionJurisprudencia` guarda un historial independiente del ranking: caso,
resolución, usuario, decisión, contexto, huella de la fuente y copia del fragmento
valorado. Regenerar resultados no elimina el historial ni las selecciones.
Las útiles que salen del ranking se siguen mostrando como selecciones históricas.
Las descartadas también se conservan para permitir su restauración.

La última decisión se comparte entre los usuarios autorizados del mismo caso.
«No útil» excluye esa resolución de las búsquedas semántica y léxica de ese caso
antes de seleccionar los candidatos. No se aplica a otros casos ni cambia el
modelo automáticamente. El historial queda disponible para una futura preparación
de datos de evaluación o entrenamiento; contiene el relato privado del caso y no
debe copiarse sin anonimizar a los datasets versionados del repositorio.

La comparación de contexto reutiliza las reglas de los artículos: ampliar un
relato conservando los hechos anteriores mantiene la valoración; reemplazarlo,
rectificarlo, modificar el documento o cambiar la fuente genera un aviso.
El usuario puede confirmar una selección histórica para el contexto actual tras
un análisis terminado. Una fuente cambiada requiere obtener un fragmento actualizado.

La API permite valorar un resultado actual (`resultado_id`) o la última selección
histórica (`valoracion_id`), con uno solo de esos identificadores. Comprueba acceso
al caso, permisos de escritura y pertenencia de la referencia. Rechaza valoraciones
durante el análisis y no admite confirmar resultados de otro contexto o fuente.
Los resultados anteriores a la migración se pueden valorar si el caso tiene un
análisis completo y la fuente conserva la misma huella.

El lector de la resolución sigue resaltando el fragmento presentado en el caso.
Marcar «Útil» significa conservarlo para revisión y no confirmar su aplicación jurídica.

Migración `0012_valoracion_jurisprudencia`: nueva tabla de historial y campo JSON
de contexto en resultados. No elimina resoluciones, fragmentos, embeddings,
artículos ni valoraciones existentes.
