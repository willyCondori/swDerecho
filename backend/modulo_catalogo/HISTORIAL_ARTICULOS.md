# Historial de cambios

La pestaña Catálogo → Historial de cambios consulta un historial de solo lectura con los textos anterior y posterior, parte afectada, responsable, fuente y fecha de efecto.

Al confirmar una derogación parcial vigente, se retira solamente el fragmento identificado del texto activo. Se conservan el PDF original, las versiones y la evidencia del efecto. El texto, el historial, los embeddings y las entidades se actualizan en una transacción; si falla, se revierte la confirmación.

Las derogaciones totales y abrogaciones conservan el texto histórico completo y actualizan la vigencia. Las notas informativas y detecciones pendientes no retiran texto.

Después de actualizar:

```
python manage.py migrate
python manage.py aplicar_derogaciones_confirmadas
```

El segundo comando incorpora al historial los efectos ya confirmados. Es idempotente. Los fragmentos ambiguos se reportan y no se borran.

Para efectos con fecha futura, el texto queda intacto hasta su vigencia. Programar el comando `aplicar_derogaciones_confirmadas` diariamente en el servidor para materializarlos al llegar la fecha. La ficha del historial indica si el efecto está aplicado o programado.


## Restaurar confirmaciones

Catálogo → Restaurar cambios permite a un administrador revisar la vista previa y confirmar la restauración de una derogación o abrogación registrada por error. Es una corrección del catálogo, no una modificación de la ley de origen.

La restauración revierte el efecto completo, conserva el historial y registra usuario y fecha. Para una retirada parcial aplicada exige que el contenido activo coincida con el texto posterior guardado; si hubo cambios posteriores bloquea la restauración automática. Las otras afectaciones se mantienen. Los efectos restaurados no se reaplican al recargar el mismo PDF.
