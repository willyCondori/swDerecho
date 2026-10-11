# Bitácora de casos especiales del modelo

## Acuerdo de trabajo — 10 de octubre de 2026

Registrar los casos especiales que Willy identifique durante el uso del sistema,
sus resultados y las correcciones esperadas para una futura evaluación y un nuevo
entrenamiento. Esta bitácora constituye la memoria del proyecto. No ejecuta un
entrenamiento ni modifica automáticamente los pesos a partir de valoraciones.

Las etiquetas propuestas requieren revisión profesional antes de incorporarse
como ejemplos supervisados. Conservar separados los conjuntos de entrenamiento
y evaluación. No registrar nombres, identificadores de clientes ni documentos
confidenciales en este archivo versionado.

## CE-001 — Robo con cuchillo e intento de secuestro

- Relato de ejemplo: «Me robaron con cuchillo, más intento de secuestro».
- Corrección solicitada: conservar los artículos de robo como candidatos
  principales; presentar el artículo de secuestro como recomendación
  complementaria con una advertencia sobre la tentativa, sin asumir consumación.
- Una valoración «Útil» conserva el artículo para revisión; no significa
  «jurídicamente aplicable». Mantener las selecciones y su contexto previo.
- Revisar la confusión entre secuestro de personas y secuestro procesal de objetos.
  El intento de secuestro por sí solo tampoco demuestra trata de personas.
- Comparar con relatos de secuestro consumado, tentativa negada y tentativa de
  otro delito para evitar generalizar esta regla a todos los artículos.
- Estado: corrección funcional con reglas explícitas; ejemplo pendiente de
  validación jurídica y de preparación para entrenamiento.

El ejemplo estructurado está en `datasets/casos_especiales.jsonl`. Al registrar
otros casos, indicar el resultado observado, la corrección solicitada y el estado
de revisión; no presentar etiquetas pendientes como resultados validados.

## CE-002 — Falsas coincidencias de jurisprudencia en robo y secuestro

- Un pasaje que dice «podría ... ser asaltada» como amenaza futura no debe
  identificarse como un asalto efectivamente relatado.
- La devolución de «dólares americanos, secuestrados» es una referencia a dinero;
  no debe generar la etiqueta de secuestro de personas. Si el mismo pasaje trata
  sobre robo agravado, puede conservarse por esa relación específica.
- Un fundamento genérico sobre revisión de sentencia sin relación identificable
  con los delitos del caso se descarta aunque su similitud semántica sea alta.
- Evaluar el fragmento que se muestra y resalta, evitando sostener la relación
  únicamente en una carátula retirada de la presentación.
- Estado: reglas y pruebas de regresión implementadas. Pendiente de revisión
  profesional para convertirlo en un ejemplo de entrenamiento validado.
