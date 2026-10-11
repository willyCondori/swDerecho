# Caché de consultas

La caché del navegador vive únicamente en la memoria de la pestaña. No guarda
respuestas en localStorage, sessionStorage ni disco. Solo se aplica a endpoints
elegidos expresamente; los demás conservan su comportamiento.

- Ramas, jerarquías, normas de los selectores, roles y etapas: 60 segundos.
- Texto y metadatos de una resolución del TSJ: 120 segundos.
- Consultas simultáneas al mismo endpoint comparten una petición. Cada consumidor
  recibe su propia copia de los datos y puede cancelar su lectura independientemente.
- Máximo de 60 entradas por pestaña; al superar el límite se elimina la más antigua.
- Un cambio exitoso mediante POST, PUT, PATCH o DELETE invalida la caché de la
  pestaña. Login, logout, renovación del token y cambio de sesión también la limpian.
- Los errores no se almacenan. Una respuesta iniciada antes de una invalidación
  no puede volver a poblar la caché. `cachedGet(url, { cache: false })` fuerza la lectura.
- Los cambios realizados desde otra pestaña, otro usuario o una importación en
  segundo plano se reflejan al vencer el plazo o recargar la página.

El resumen del corpus de jurisprudencia se almacena en la caché de Django durante
15 segundos, con una clave por versión del modelo. Un resultado reutilizado evita
las cinco consultas del resumen. DRF comprueba la autenticación y los permisos
antes de consultar esta caché. Solo contiene contadores, salas y departamentos del
corpus compartido; no incluye datos de clientes ni descripciones de casos.

Esta caché utiliza el backend predeterminado de Django, actualmente LocMemCache.
Cada proceso web mantiene su propia copia; los contadores pueden llevar hasta
15 segundos de retraso respecto a una importación. No se limpia la caché completa
del servidor para preservar las tareas y revisiones normativas en curso.

La pantalla de jurisprudencia consulta el resumen al entrar y al pulsar
«Actualizar listado», para cargar las opciones de sala y departamento y el total
de resoluciones guardadas. Se retiraron los indicadores técnicos de embeddings
y disponibilidad para IA, su aviso de importación y el sondeo cada 20 segundos.

Se mantienen fuera de estas nuevas cachés los clientes, casos, valoraciones,
permisos efectivos, notificaciones, progreso del análisis, búsquedas filtradas,
PDF y resultados jurídicos. La extracción de texto PDF ya dispone de una caché
persistente propia y no se duplica. Las notificaciones conservan WebSockets.

La caché no constituye un control de autorización. Los controles del servidor
siguen siendo obligatorios; un catálogo visible ya cargado puede permanecer en
pantalla hasta la siguiente lectura o cambio de sesión.

Validación: pruebas de caducidad, deduplicación, copias independientes, límites,
cancelación, errores, invalidación por escritura/sesión, aislamiento de permisos
del servidor, separación por versión del modelo y número de consultas SQL.
