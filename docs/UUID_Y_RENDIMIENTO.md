# UUID públicos y rendimiento del análisis

## Identificadores

Se añade `public_id` UUID v4, único e inmutable desde la API, a casos, clientes,
usuarios, perfiles, documentos de casos, documentos generados y notificaciones.
La API conserva el nombre `id`, pero devuelve el UUID. Las rutas de detalle,
acciones y relaciones de esas entidades requieren UUID; los números antiguos
no tienen una ruta alternativa. Los filtros `caso_id`, `cliente_id` y
`usuario_id` de auditoría usan las referencias públicas.

Las claves primarias y las claves foráneas internas siguen siendo enteras.
Esto conserva relaciones, SQL del ranking, historial y tokens existentes sin
convertir innecesariamente todas las tablas. Los identificadores de catálogos
públicos (normas, artículos, ramas, tipos de documento y resoluciones) conservan
su formato. Los registros técnicos de auditoría conservan la clave interna del
registro auditado. UUID evita la enumeración secuencial de enlaces; no sustituye
la autenticación ni los permisos. Los archivos nuevos de casos tienen nombres
aleatorios para evitar sobrescritura y referencias internas en su nombre.

Las migraciones añaden una columna nullable, asignan un UUID distinto por fila
y después aplican unicidad y NOT NULL. No se borran ni recrean entidades.
La copia anterior a la migración se encuentra fuera del repositorio, en
`C:/Users/willy/.codex/backups/sw-derecho-20261010-antes-uuid.dump`.
Los enlaces antiguos a `/casos/1`, etc., deben reemplazarse desde el listado
actual. No se mantiene una redirección numérica que permita enumerar registros.

## Recuperación y progreso

El corpus medido contiene 207 713 embeddings de jurisprudencia. Se incorpora
IVFFlat coseno (200 listas, 30 probes) y un índice GIN de texto en español sobre
una columna generada. La vía semántica obtiene candidatos con el índice vectorial;
la vía léxica materializa los fragmentos que coinciden y los ordena por distancia
exacta. Se conservan las reglas de figuras jurídicas, fragmentos sustantivos y
recomendaciones de menor confianza. IVFFlat aproxima la selección de candidatos:
no garantiza el mismo resultado que una búsqueda exhaustiva para todos los casos.

En el caso de prueba, las cinco resoluciones y su orden coinciden con la búsqueda
exhaustiva anterior. La evaluación de otros hechos debe continuar; esta medición
no representa una validación jurídica del corpus.

Medición local del 10 de octubre de 2026, mismo caso y modelo cargado:

- Recuperación exhaustiva anterior: 6,204 s.
- Recuperación optimizada: 0,341 s.
- Pipeline anterior: 7,327 s.
- Pipeline optimizado: 1,659 s y 1,874 s.

La medición se hizo con `scripts/medir_analisis_uuid.py` dentro de transacciones
revertidas: no reemplazó el análisis existente ni persistió auditorías o avisos.
El calentamiento inicial del proceso separado de medición tardó 11,563 s; el
servidor tiene precarga de embeddings antes de aceptar peticiones.
Los tiempos dependen del tamaño del caso, OCR, carga y almacenamiento.

La UI consulta un endpoint de estado ligero cada segundo solo durante el
análisis, evita peticiones solapadas y carga el detalle completo al terminar.
Esto elimina el intervalo de cuatro segundos y las consultas del detalle
completo que retrasaban la presentación del resultado.

Referencia técnica: [documentación oficial de pgvector](https://github.com/pgvector/pgvector#ivfflat).
