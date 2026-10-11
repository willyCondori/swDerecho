# Revisión del software — 10 de octubre de 2026

La revisión comenzó en `codex/auditoria-pruebas-tema-dia`. Durante el trabajo hubo un cambio externo de rama a `feature/test-finales`; se respetó ese cambio. Las modificaciones permanecen en el árbol de trabajo, sin commit de esta revisión. Se conservaron los cambios anteriores. No se eliminaron tablas, registros, archivos de usuarios ni versiones de embeddings.

## Alcance y límites de la revisión

Se revisaron los módulos de autenticación y usuarios, roles, clientes, casos, documentos, catálogo normativo, vigencia, análisis semántico, jurisprudencia, notificaciones, auditoría, dashboard y configuración Docker. Se contrastaron modelos, migraciones, rutas, servicios, pantallas y pruebas con la base local.

Las pruebas automatizadas comprueban comportamiento y regresiones. No sustituyen una evaluación de pertinencia jurídica por abogados ni acreditan precisión del modelo, mejora frente a búsqueda manual o tiempos de respuesta en producción. Las integraciones externas y los modelos pesados se simulan en parte de la suite; no se realizó una nueva importación completa del TSJ ni un entrenamiento durante esta revisión.

## Correcciones realizadas

1. **Descubrimiento de pruebas del backend.** Faltaban marcadores `__init__.py` en ocho paquetes. El comando general encontraba solo 23 pruebas, aunque existían muchas más. Se añadieron los marcadores para descubrir la suite completa sin indicar aplicaciones manualmente.
2. **Protección de roles.** La eliminación del Administrador estaba protegida, pero un `PATCH` podía desactivarlo o cambiar su nombre. El serializer ahora impide ambas acciones y la desactivación de roles con usuarios activos asignados.
3. **Búsqueda de clientes.** Una petición lenta anterior podía sobrescribir una búsqueda más reciente. El hook acepta únicamente la respuesta de la última petición e invalida respuestas al desmontarse.
4. **Notificaciones.** Marcar otra vez una notificación leída podía reducir indebidamente el contador. Se evitan operaciones repetidas y solicitudes simultáneas para el mismo registro; un identificador fuera del listado provoca una actualización del contador.
5. **Estado del análisis en el dashboard.** La presencia de un PDF se interpretaba como análisis en curso. La API de listado ahora expone `estado_analisis`; la interfaz usa los estados persistidos y distingue pendientes, errores, procesos y resultados completos.
6. **Modelo en Docker.** Se alinearon la ruta, la versión registrada y el uso de prefijos con `sw-derecho-embeddings-v1-final`. Antes se podía cargar ese modelo y etiquetar los vectores como `e5_base`. Se corrigió también la sustitución de la versión en el script de preparación para evitar sufijos repetidos. No se reescribieron embeddings anteriores.
7. **Tema de día y noche.** Las paletas están separadas en `frontend/src/styles/theme-day.css` y `theme-night.css`. Tipografía, distribución y estilos de componentes siguen compartidos. Se reforzaron los textos secundarios y tenues, se completaron variables ausentes y se distinguió el texto blanco sobre botones de color. Se ajustaron selección, tablas, visor, indicadores y superficies de lectura.
8. **Pruebas independientes de los datos iniciales.** Las pruebas de compilaciones y disposiciones suponían que la base conservaba las normas y jerarquías de las migraciones. Fallaban al repetir la suite con `--keepdb`. Ahora preparan explícitamente sus datos; los 25 casos afectados pasaron en una ejecución dirigida sobre la base reutilizada.

Las pruebas de paleta comprueban al menos 4,5:1 para los textos principales, secundarios y tenues sobre las cinco superficies definidas, además de botones principales y selección. Este umbral corresponde al texto normal de [WCAG 2.2: contraste mínimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Esto no constituye una certificación de accesibilidad de todas las combinaciones de la aplicación.

## Pruebas añadidas

- **Roles, backend:** acceso anónimo, restricciones de escritura, protección del Administrador, roles asignados, nombres únicos sin distinguir mayúsculas y ciclo de eliminación/restauración.
- **Listado de casos, backend:** representación del estado real del análisis en el serializer.
- **Clientes, frontend:** paginación, búsqueda, respuesta fuera de orden, error y recuperación.
- **Roles, frontend:** carga, error y respuesta vacía.
- **Auditoría, frontend:** filtros, paginación, reinicio y error.
- **Dashboard, frontend:** uso de estadísticas globales, recuperación de errores y representación de los cuatro estados del análisis.
- **Notificaciones, frontend:** carga diferida, contador, lectura idempotente, doble clic, recuperación de errores y limpieza del temporizador.
- **Temas, frontend:** contraste de paletas, persistencia de preferencia y funcionamiento cuando el almacenamiento del navegador está bloqueado.

Los módulos de autenticación, catálogo, documentos, casos, jurisprudencia, ranking y embeddings ya tenían pruebas, incluidas en las ejecuciones generales. Añadir pruebas a un módulo no significa cobertura del 100 % de sus líneas o flujos.

## Base de datos: qué se puede depurar

El inventario de solo lectura está en `docs/auditoria/inventario-bd-2026-10-10.json`. Incluye 50 modelos con sus tablas, contando la relación automática de grupos y permisos. Todas esas tablas existen. La única tabla sin modelo es `django_migrations`, que es necesaria para el historial de migraciones.

**Candidatas a retirada por pertenecer a funcionalidades antiguas o excluidas del alcance:**

- `hechos`: 0 registros.
- `hechos_casos`: 0 registros.
- `petitorios`: 0 registros.
- `petitorios_casos`: 0 registros.
- `plantillas_documento`: 0 registros.
- `documentos_generados`: 0 registros.

No están completamente desvinculadas del código. Hechos y petitorios conservan modelos, serializers, consultas y presentación condicional; no se producen como extracción estructurada en el análisis actual. Plantillas y documentos generados conservan rutas de API. Para retirarlas corresponde primero retirar consumidores y rutas, después generar una migración y verificar dependencias con una copia de seguridad. No se recomienda borrarlas directamente desde PostgreSQL.

**Tablas vacías que se deben conservar:** `documentos_caso`, `textos_documentos_caso` y `tipo_doc` participan en los documentos de casos; `password_reset_tokens` en recuperación de acceso; `entidades_detectadas_caso` en identificación de entidades; `jurisprudencia_resultados` en resultados relacionados; `modulo_ia_valoracionarticulo` en valoraciones. Las tablas de grupos, sesiones y administración pertenecen a Django. La ausencia de registros en esta instalación no demuestra que sean innecesarias.

**Tablas con datos que no son sobrantes:** catálogo e historial normativo, auditoría, búsquedas de clientes y embeddings versionados. Hay 9.671 resoluciones, 195.441 fragmentos y 207.713 embeddings de jurisprudencia. Que haya más embeddings que fragmentos no demuestra duplicación indebida: debe comprobarse su versión de modelo. `resultados_caso` está en uso; sus campos antiguos de resumen, estrategias, fortalezas y debilidades requieren revisión individual, no eliminación de la tabla.

El inventario muestra cero resultados de jurisprudencia asociados a casos en esta base. Por tanto, la colección cargada no acredita por sí sola que se haya completado y evaluado ese flujo con los casos existentes.

## Mejoras pendientes, por prioridad

1. **Retirar o delimitar generación de documentos.** La acción `DocumentoGeneradoViewSet.generar` importa `modulo_documentos.services.generador_docx_service`, que no existe. Una solicitud válida llega a una funcionalidad incompleta y puede devolver 500. Es una función ajena al alcance final; conviene retirarla de la API activa o declarar explícitamente su indisponibilidad, junto con plantillas y las tablas candidatas.
2. **Evitar pantallas de carga indefinidas.** `/plantillas/*`, `/ia/*` y `/configuracion/*` presentan directamente `PageLoader`. Deben retirarse o mostrar una página de funcionalidad no disponible. No deben contarse como módulos terminados en el documento académico.
3. **Evaluar recuperación de jurisprudencia de extremo a extremo.** Ejecutar casos controlados, comprobar persistencia y visualización de resultados y obtener valoraciones profesionales. Medir pertinencia, recuperación y latencia; no atribuir métricas todavía inexistentes al modelo final.
4. **Medir la búsqueda vectorial con el corpus real.** Se consultó `pg_indexes`: `jurisprudencia_embeddings` y `embeddings_articulos` tienen índices B-tree; no tienen índices ANN HNSW/IVFFlat instalados. Revisar planes `EXPLAIN` antes de elegir un índice vectorial. Cualquier aproximación debe comprobar pérdida de recuperación y consumo de memoria con las más de 200.000 representaciones actuales. Además, `embeddings_articulos_articulo_id_56063b23` e `idx_emb_art_articulo` indexan la misma columna `articulo_id`: son candidatos a consolidación mediante migración tras comprobar dependencias; no se eliminaron durante esta revisión.
5. **Persistir tareas largas y su progreso.** Los procesos en hilos y estados en memoria no ofrecen recuperación completa ante reinicios. Para importaciones y análisis largos, guardar estado/checkpoints y usar trabajadores independientes. No considerar la presencia de un archivo de Celery como prueba de que el servicio ya esté desplegado.
6. **Precisar el alcance de roles.** Los permisos dependen de los roles operativos definidos en código. Crear un nuevo nombre de rol no configura una matriz dinámica de permisos. Documentar esta restricción o implementar esa matriz como una ampliación explícita.
7. **Consolidar configuración y código heredado.** Revisar archivos alternativos de settings, configuración de tareas y vistas antiguas que no usa el router activo. Retirarlos solo tras verificar sus importaciones y scripts.
8. **Resolver advertencias de lint.** La comprobación devuelve 0 errores y 16 advertencias, entre ellas variables sin usar y dependencias de hooks. Quedan registradas para depuración; no bloquean la compilación, pero el código aún no está libre de advertencias.

## Verificación reproducible

Resultado final tras las correcciones: **686 pruebas del backend aprobadas** en 189,748 segundos y **241 pruebas del frontend aprobadas**, distribuidas en 46 archivos, en 45,23 segundos. La ejecución del backend se repitió sobre la base reutilizada después de corregir los datos de preparación, sin errores. Compilación correcta, comprobación Django sin incidencias y migraciones coherentes. Lint: 0 errores y 16 advertencias pendientes.

Desde `backend`, con las dependencias y una base de pruebas disponibles:

```text
python manage.py test --noinput --keepdb
python manage.py check
python manage.py makemigrations --check --dry-run
```

Desde `frontend`:

```text
npm test -- --maxWorkers=2
npm run lint
npm run build
```

Inventario sin valores personales ni credenciales, desde `backend`:

```text
python manage.py shell -c "exec(open('../scripts/inventario_bd.py').read())"
```

El inventario hace conteos exactos de todas las tablas; ejecutarlo bajo demanda, no en cada petición web. En Docker se puede copiar el script al contenedor y ejecutarlo mediante `manage.py shell`.

Se reconstruyeron únicamente backend y frontend. Ambos contenedores están saludables; la base de datos y sus volúmenes se conservaron. Se aplicaron las migraciones aditivas pendientes que ya estaban en el trabajo anterior. La compilación del frontend terminó correctamente y Django no detecta cambios de modelo sin migración.

Se verificaron visualmente la pantalla de documentos en tema claro y la lectura de un PDF de nueve páginas dentro del sistema. Captura: `docs/auditoria/tema-dia-documentos.jpg`.
