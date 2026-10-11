# Recuperación híbrida de jurisprudencia

La recuperación usa exclusivamente embeddings del modelo activo y resoluciones
activas. Une hasta 100 fragmentos semánticos y 100 fragmentos con términos por
fragmento de caso, y ordena por 75 % similitud, 20 % coincidencia de delitos y
5 % figuras transversales. Deduplica resoluciones y conserva un fragmento
sustantivo; descarta carátulas y presentaciones sin explicación jurídica.

Las reglas distinguen secuestro de personas de incautación de objetos mediante
el contexto próximo. La tentativa se contrasta con el secuestro mencionado;
su presencia en otro delito no aporta automáticamente el mismo refuerzo.
Estas reglas explicables no sustituyen una evaluación jurídica ni garantizan
comprensión completa de la resolución.

## Umbrales y validación pendiente

- `JURISPRUDENCIA_UMBRAL=0.65`: nivel de similitud de mayor confianza.
- `JURISPRUDENCIA_UMBRAL_RECOMENDACION=0.50`: mínimo provisional para
  recomendaciones. Exige además coincidencia de delito y contenido sustantivo.
- Resultados inferiores a 0.65 se identifican como recomendaciones; el contraste
  de tentativa también se advierte. Ningún puntaje representa aplicabilidad ni
  probabilidad de éxito judicial.

Para comparar sin modificar los rankings:

```sh
python manage.py evaluar_recuperacion_jurisprudencia --caso 1 --salida /app/cache/evaluacion-jurisprudencia-1.json
```

La exportación compara 0.50, 0.55, 0.60 y 0.65 y deja en cada candidato campos
de pertinencia, observaciones y estado de revisión. Un profesional debe revisar
el fragmento y la resolución completa, indicar relación con hechos, figuras y
criterio relevante, y justificar los descartes. Repetir con casos distintos,
incluidos casos negativos y secuestro de objetos, antes de ajustar el umbral.
No hay métricas de precisión o exhaustividad validadas hasta completar esas
etiquetas y un conjunto de evaluación independiente.

## Despliegue

Aplicar `modulo_ia/0010_jurisprudencia_hibrida.py`. Conserva la similitud original
y añade puntuación híbrida, coincidencias, clasificación y explicación.
Reanalizar los casos para regenerar sus resultados con las nuevas reglas.
