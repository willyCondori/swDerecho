# Utilidad de artículos para el caso

- Elegir «Útil» o «No útil» envía y guarda la decisión. Si falla el envío, la selección anterior se conserva y se informa el error.
- La vista presenta dos bloques: «Artículos seleccionados» contiene solo los útiles y «Artículos sin valorar» contiene los pendientes, justo antes de la jurisprudencia. Cambiar la valoración mueve el artículo al bloque correspondiente cuando el servidor confirma el envío.
- Las selecciones útiles se recuperan del historial aunque un nuevo ranking ya no incluya el artículo. No se añaden puntuaciones artificiales al ranking. Si cambian la descripción, los fragmentos o el contenido normativo, se muestra un aviso de valoración en contexto anterior. Tras reanalizar, el usuario puede confirmar la utilidad para el contexto actual; el aviso desaparece únicamente después de guardar esa nueva decisión.
- Tras guardar «No útil», el artículo desaparece inmediatamente de la lista de artículos seleccionados. Los descartados del análisis actual se pueden consultar por separado para corregir una decisión antes de reanalizar.
- Al reanalizar el mismo caso se excluyen los descartados antes del límite de candidatos y también de las sugerencias complementarias. La última decisión del caso es compartida por los usuarios con acceso autorizado; cambiar descripción, PDF o modelo no la revoca.
- «Útil» o «Sin valorar» revocan la exclusión. El historial permanece en la base; no se eliminan artículos del catálogo ni se cambia su vigencia.
- Otros casos no se modifican en esta implementación.

## Ampliación futura solicitada

Para futuros casos similares se conservaron los envíos, el texto del caso, los fragmentos, el texto del artículo, la versión del modelo y el autor de la decisión. La exportación existente permite obtener esas muestras.

**Todavía no se implementa la exclusión automática entre casos similares.** Esa ampliación requiere definir y evaluar la similitud y cuándo trasladar una decisión a otro caso. El historial de «No útil» se guarda para esa finalidad; no modifica por sí solo el modelo ni aplica una prohibición global sobre la normativa.

Migración necesaria: `modulo_ia/0009_excluir_articulos_no_utiles.py`. Añade un índice para consultar decisiones por caso/artículo y actualiza la función SQL de recuperación; dispone de reversión.
