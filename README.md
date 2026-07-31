# JurisIA

Plataforma de gestión de casos legales para estudios de abogacía en Bolivia, con un motor de recomendación de artículos jurídicos aplicables a cada caso, construido sobre similitud semántica, filtrado por rama del derecho y clasificación de tipo de delito.

---

## Tabla de contenidos

- [Descripción general](#descripción-general)
- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Modelo de datos](#modelo-de-datos)
- [Pipeline de análisis de casos](#pipeline-de-análisis-de-casos)
- [Motor de ranking de artículos](#motor-de-ranking-de-artículos)
- [API — Endpoints principales](#api--endpoints-principales)
- [Frontend — Módulos principales](#frontend--módulos-principales)
- [Instalación y puesta en marcha](#instalación-y-puesta-en-marcha)
- [Variables de entorno relevantes](#variables-de-entorno-relevantes)
- [Roles y permisos](#roles-y-permisos)
- [Seguridad y cifrado de datos](#seguridad-y-cifrado-de-datos)
- [Estado actual y limitaciones conocidas](#estado-actual-y-limitaciones-conocidas)
- [Roadmap](#roadmap)

---

## Descripción general

JurisIA permite a un despacho de abogados:

- Registrar clientes y casos, ya sea redactando una descripción de los hechos o adjuntando un PDF.
- Ejecutar un pipeline de análisis que **fragmenta el texto del caso, lo vectoriza, lo compara contra un catálogo de artículos jurídicos (Código Penal, Constitución Política del Estado, y potencialmente otras normas) y genera un ranking de los artículos más aplicables**, con un desglose transparente de por qué cada artículo fue seleccionado.
- Consultar el detalle de cada caso: cliente asociado, descripción, hechos, petitorios, resultado del análisis y el listado de artículos recomendados con su score de relevancia.
- Administrar el catálogo de normas, ramas del derecho, artículos y entidades jurídicas.
- Gestionar usuarios con distintos roles (abogado, administrador) y mantener un registro de auditoría de las acciones sobre casos y clientes.

---

## Arquitectura

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│        Frontend          │  HTTP   │           Backend              │
│   React + Vite (SPA)     │ ◄─────► │   Django + Django REST Framework│
│   React Router           │  JSON   │   PostgreSQL + pgvector          │
└─────────────────────────┘         └──────────────────────────────┘
                                                    │
                                                    ▼
                                     ┌──────────────────────────────┐
                                     │     Pipeline de análisis IA    │
                                     │  Chunking → Embeddings →       │
                                     │  Detección de entidades →      │
                                     │  Ranking de artículos          │
                                     └──────────────────────────────┘
```

El backend expone una API REST modular (un módulo Django por dominio: casos, clientes, usuarios, catálogo, documentos, auditoría, IA). El frontend es una SPA en React que consume esa API, con rutas protegidas según el rol del usuario autenticado.

El pipeline de análisis corre actualmente **de forma síncrona dentro del mismo proceso de Django** (sin cola de tareas en segundo plano), pero está preparado para desacoplarse a un worker asíncrono en el futuro.

---

## Stack tecnológico

### Backend
- **Python 3.10**
- **Django 5.2** + **Django REST Framework**
- **PostgreSQL** con la extensión **pgvector** (búsqueda vectorial por similitud de coseno, indexada con HNSW)
- **sentence-transformers** para la generación de embeddings de texto (modelo multilingüe, compatible con español)
- **pypdf** para extracción de texto de documentos PDF adjuntos
- **drf-spectacular** para documentación OpenAPI/Swagger
- Cifrado simétrico (AES) para datos sensibles de clientes (nombres, apellidos, teléfono, fecha de nacimiento)

### Frontend
- **React** (Vite como bundler/dev server)
- **React Router** para el ruteo, con carga diferida (`React.lazy`) de páginas
- **Axios** como cliente HTTP
- CSS Modules para estilos por componente
- Iconos Tabler Icons (`ti ti-*`)

---

## Estructura del proyecto

### Backend (`/backend`)

```
backend/
├── config/                    # Settings y urls raíz del proyecto Django
├── core/
│   ├── encryption/             # Utilidades de cifrado/descifrado (AES)
│   └── permissions/             # Mixins de auditoría y permisos por rol
├── modulo_usuarios/             # Autenticación, usuarios, roles
├── modulo_clientes/              # CRUD de clientes, búsqueda por nombre
├── modulo_casos/                # CRUD de casos, hechos, petitorios, resultados
├── modulo_catalogo/               # Ramas del derecho, normas, artículos, entidades jurídicas
├── modulo_documentos/              # Documentos adjuntos (PDF) asociados a casos
├── modulo_ia/                     # Pipeline de análisis: chunking, embeddings, ranking
└── modulo_auditoria/                # Registro de auditoría de acciones (crear/editar/eliminar/analizar)
```

### Frontend (`/frontend` o `/src`)

```
src/
├── api/                         # Clientes Axios por módulo (casosApi, clientesApi, catalogoApi, ...)
├── components/
│   └── layout/                  # AppLayout, PrivateRoute
├── modules/
│   ├── auth/                    # Login
│   ├── dashboard/                 # Panel principal
│   ├── casos/
│   │   ├── pages/                # Listado, creación y detalle de casos
│   │   └── hooks/                 # useCasos, useCrearCaso, useCasoDetail
│   ├── clientes/
│   │   ├── pages/                 # Listado, creación y detalle (casos del cliente)
│   │   └── hooks/                  # useClientes, useClienteCasos
│   ├── catalogo/                    # Gestión de artículos y carga masiva
│   └── usuarios/                     # Gestión de usuarios
└── routes/
    └── AppRouter.jsx               # Definición de rutas, protegidas por PrivateRoute
```

---

## Modelo de datos

### Entidades principales

| Modelo | Descripción |
|---|---|
| `Cliente` | Datos de contacto del cliente. Campos sensibles (nombres, apellidos, teléfono, fecha de nacimiento) se almacenan cifrados. |
| `Caso` | Caso legal: título, descripción, cliente asociado, abogado (`usuario`) responsable, rama del derecho detectada/asignada, código único autogenerado. |
| `Hecho` / `Petitorio` | Hechos y petitorios asociados a un caso (relación N:M vía tablas intermedias con orden). |
| `ResultadoCaso` | Resultado del análisis de un caso: resumen, fortalezas, debilidades, estrategias, observaciones (relación 1:1 con `Caso`). |
| `RamaDerecho` | Rama del derecho (ej. Penal, Derecho Constitucional). |
| `Norma` | Norma jurídica (ej. Código Penal, Constitución Política del Estado), con sigla. |
| `Articulo` | Artículo de una norma: número, título, contenido, jerarquía normativa (escala 0–1), frecuencia histórica de uso, rama y norma asociadas. |
| `EntidadJuridica` | Catálogo de entidades jurídicas relevantes (ej. "Víctima", "Menor de edad", "Servidor Público"), usadas para enriquecer el ranking. |
| `ArticuloEntidad` | Relación N:M entre artículos y entidades jurídicas. |
| `ChunkCaso` | Fragmento de texto de un caso, generado durante el chunking previo al análisis. |
| `EmbeddingChunk` / `EmbeddingArticulo` | Vectores de embedding (768 dimensiones) de cada chunk de caso y de cada artículo, almacenados con `pgvector`. |
| `EntidadDetectadaCaso` | Entidades jurídicas detectadas en el texto de un caso durante el análisis. |
| `ResultadoArticulo` | Fila del ranking: artículo, caso, posición, score total y desglose de sub-scores. |
| `Documento` | Documento adjunto a un caso (PDF), con su tipo. |

### Jerarquía normativa

`Articulo.jerarquia_normativa` usa una escala fija de 0 a 1, donde el valor más alto corresponde a la norma de mayor rango:

| Valor | Nivel |
|---|---|
| 1.0 | Constitución Política del Estado |
| 0.9 | Ley Orgánica |
| 0.8 | Código (Penal, Civil, etc.) |
| 0.7 | Ley Ordinaria |
| 0.6 | Decreto Supremo |
| 0.5 | Resolución Ministerial |
| 0.4 | Ordenanza Municipal |

---

## Pipeline de análisis de casos

Al disparar el análisis de un caso (`POST /api/casos/{id}/analizar/`), se ejecutan los siguientes pasos de forma secuencial:

1. **Chunking** — El texto del caso (la descripción redactada, o el texto extraído del PDF adjunto si existe) se divide en fragmentos de ~800 caracteres con solapamiento de 150 caracteres entre fragmentos consecutivos, respetando límites de párrafo cuando es posible.

2. **Embeddings** — Cada fragmento se vectoriza con un modelo de `sentence-transformers` multilingüe (768 dimensiones), normalizado para comparación por similitud de coseno.

3. **Detección de entidades jurídicas** — Se identifica qué entidades del catálogo (`EntidadJuridica`) aparecen mencionadas en el texto del caso, mediante coincidencia de texto contra el catálogo cargado.

4. **Ranking de artículos** — Ver sección siguiente.

5. **Generación de resultado** — Se crea o actualiza el `ResultadoCaso` asociado. Los campos de resumen, fortalezas, debilidades y estrategias quedan disponibles como estructura de datos para completarse en una etapa posterior del proyecto; su generación automática no forma parte del alcance actual.

El análisis es **idempotente**: volver a analizar un caso reemplaza los chunks, embeddings y ranking previos, permitiendo reanalizar después de editar la descripción o adjuntar un nuevo PDF.

---

## Motor de ranking de artículos

El componente central del sistema es el `RankingService`, que para cada caso:

1. Compara los embeddings de sus chunks contra los embeddings de los artículos del catálogo, usando `pgvector` con índice HNSW para eficiencia en la búsqueda de vecinos más cercanos.
2. Si el caso tiene una **rama del derecho** asignada (manual o detectada), acota la comparación solo a los artículos de esa rama, evitando que normas de otras materias contaminen el resultado.
3. Combina el score semántico con otros cuatro sub-scores, según una fórmula ponderada:

| Sub-score | Peso | Descripción |
|---|---|---|
| **Semántico** | 60% | Similitud de coseno entre el embedding del caso y el del artículo. |
| **Delito** | 15% | Clasificación del tipo de delito descrito en el caso (por coincidencia de palabras clave contra categorías definidas por rama), comparado contra la categoría del artículo (extraída de su título). |
| **Entidades** | 10% | Proporción de entidades jurídicas detectadas en el caso que también están asociadas al artículo. |
| **Jerarquía** | 10% | Jerarquía normativa del artículo (escala 0–1 descrita arriba). |
| **Frecuencia** | 5% | Frecuencia histórica de uso del artículo, normalizada contra el máximo del conjunto de candidatos. |

4. Selecciona los `TOP_N` artículos con mayor score total usando una cola de prioridad de tamaño fijo (evita ordenar el universo completo de candidatos), y aplica un **umbral mínimo de score** para no forzar una lista completa cuando no hay suficientes artículos realmente relevantes.
5. Persiste el resultado en `ResultadoArticulo`, con el desglose completo de cada sub-score para trazabilidad.

### Clasificador de delito

Como paso intermedio (sin dependencia de modelos de lenguaje generativos), el sistema clasifica el texto del caso contra grupos de delitos definidos por palabras clave específicas del ámbito penal (ej. "ROBO", "HURTO", "HOMICIDIO", "LESIONES", "VIOLACIÓN", "SECUESTRO", "ESTAFA", "AMENAZAS"), y extrae la categoría de cada artículo a partir de su título (ej. "(ROBO AGRAVADO)"). Esta lógica vive en un servicio separado del ranking, pensado para escalar a otras ramas del derecho agregando nuevos diccionarios de clasificación sin modificar la lógica central.

---

## API — Endpoints principales

### Casos (`/api/casos/`)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/casos/` | Lista de casos, con filtros (`rama_id`, `cliente_id`, `fecha_desde`, `fecha_hasta`, `tiene_pdf`, `search`). Un abogado solo ve sus propios casos; un administrador ve todos. |
| `POST` | `/api/casos/` | Crea un caso para un cliente ya existente. Acepta texto y/o PDF. |
| `POST` | `/api/casos/crear_con_cliente/` | Crea cliente y caso en una sola transacción atómica. |
| `GET` | `/api/casos/{id}/` | Detalle completo del caso (incluye cliente, hechos, petitorios, resultado). |
| `PATCH` | `/api/casos/{id}/` | Edita título, descripción, estado o rama del caso. |
| `DELETE` | `/api/casos/{id}/` | Soft-delete (solo administrador). |
| `POST` | `/api/casos/{id}/subir_pdf/` | Adjunta o reemplaza el PDF del caso. |
| `GET` | `/api/casos/{id}/hechos/` | Hechos del caso. |
| `GET` | `/api/casos/{id}/petitorios/` | Petitorios del caso. |
| `GET` | `/api/casos/{id}/resultado/` | Resultado del análisis. |
| `GET` | `/api/casos/{id}/articulos/` | Ranking de artículos aplicables, con desglose de scores. |
| `POST` | `/api/casos/{id}/analizar/` | Dispara el pipeline de análisis completo. |
| `GET` | `/api/casos/mis_casos/` | Casos del usuario autenticado. |

### Clientes (`/api/clientes/`)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/clientes/` | Lista de clientes activos. |
| `POST` | `/api/clientes/` | Crea un cliente. |
| `GET` | `/api/clientes/{id}/` | Detalle del cliente (datos descifrados). |
| `PATCH` | `/api/clientes/{id}/` | Actualiza un cliente. |
| `DELETE` | `/api/clientes/{id}/` | Soft-delete (solo si no tiene casos activos; solo administrador). |
| `GET` | `/api/clientes/lista/` | Listado compacto (`id`, `nombre_completo`) para selects. |
| `GET` | `/api/clientes/{id}/casos/` | Casos asociados al cliente. |
| `GET` | `/api/clientes/buscar/?q=` | Búsqueda por nombre/apellido descifrado (mínimo 2 caracteres). |

### Catálogo (`/api/catalogo/`)

Gestión de ramas del derecho, normas, artículos y carga masiva de artículos desde fuentes externas.

### Usuarios (`/api/usuarios/`)

Autenticación (login, refresh de token) y gestión de usuarios del sistema.

### Documentación interactiva

La API expone documentación OpenAPI en `/api/schema/` y una interfaz Swagger en `/api/docs/`.

---

## Frontend — Módulos principales

- **`modules/casos`** — Listado de casos con filtros y paginación, formulario de creación (con selección de cliente nuevo o existente, y rama del derecho), y página de detalle que muestra el caso completo junto con el resultado del análisis y el ranking de artículos aplicables.
- **`modules/clientes`** — Listado de clientes con búsqueda, formulario de creación, y página de detalle que muestra los casos asociados a ese cliente (con navegación directa al detalle de cada caso).
- **`modules/catalogo`** — Visualización y carga de artículos del catálogo jurídico.
- **`modules/usuarios`** — Gestión de usuarios del sistema (crear, editar, ver perfil), reservado a administradores.
- **`modules/dashboard`** — Panel principal con resumen de actividad.

Las rutas administrativas (usuarios, catálogo, auditoría) están protegidas mediante un `PrivateRoute` con la prop `adminOnly`, que restringe el acceso según el rol del usuario autenticado.

---

## Instalación y puesta en marcha

### Backend

```bash
cd backend
python -m venv env
env\Scripts\activate          # Windows
# source env/bin/activate     # Linux/macOS

pip install -r requirements.txt

# Configurar la base de datos PostgreSQL con la extensión pgvector habilitada
python manage.py migrate

python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

La aplicación queda disponible en `http://localhost:5173`, consumiendo la API en `http://localhost:8000`.

---

## Variables de entorno relevantes

| Variable | Descripción |
|---|---|
| `SENTENCE_TRANSFORMER_MODEL` | Modelo de `sentence-transformers` usado para generar embeddings. Debe ser un modelo multilingüe compatible con español para un desempeño adecuado del ranking. |
| Configuración de base de datos | Host, puerto, usuario, contraseña y nombre de la base PostgreSQL (debe tener la extensión `pgvector` instalada). |
| Claves de cifrado | Clave usada por `core.encryption` para cifrar/descifrar los campos sensibles de `Cliente`. |

> Si se cambia `SENTENCE_TRANSFORMER_MODEL` después de tener artículos ya cargados, es necesario **regenerar los embeddings de todo el catálogo de artículos**, ya que vectores generados por modelos distintos no son comparables entre sí.

---

## Roles y permisos

| Rol | Permisos |
|---|---|
| **Abogado** | Crear, ver y editar sus propios casos y clientes. Analizar casos. Sin acceso a gestión de usuarios, catálogo ni auditoría. |
| **Administrador** | Todo lo anterior, más: ver y gestionar los casos de todos los abogados, eliminar clientes y casos, gestionar usuarios, cargar/editar el catálogo de artículos, y consultar el registro de auditoría. |

Los permisos se aplican a nivel de `ViewSet` (mixins `EsAbogado`, `EsAdmin`) y también filtran el `queryset` según el usuario autenticado (un abogado solo ve sus propios casos en los listados).

---

## Seguridad y cifrado de datos

- Los campos sensibles del cliente (nombres, apellidos, teléfono, fecha de nacimiento) se almacenan **cifrados en la base de datos** (`core.encryption.aes_encryption`), y se descifran únicamente al servirlos a través de los serializers de lectura.
- Toda acción relevante sobre casos y clientes (creación, edición, eliminación, análisis) queda registrada en el módulo de **auditoría**, con el usuario responsable, la acción, el registro afectado y metadata adicional.
- El acceso a la API requiere autenticación mediante tokens, con endpoint de refresh de sesión.

---

## Estado actual y limitaciones conocidas

- El pipeline de análisis corre **de forma síncrona** dentro del proceso de Django (no hay un worker asíncrono en producción todavía), por lo que el tiempo de respuesta de `POST /api/casos/{id}/analizar/` depende directamente del tiempo que tome el pipeline completo.
- El catálogo de artículos actualmente cubre principalmente el **Código Penal** y la **Constitución Política del Estado**. El sistema está preparado para incorporar más normas y ramas del derecho sin cambios estructurales.
- El clasificador de tipo de delito funciona por coincidencia de palabras clave, no por un modelo entrenado; su cobertura depende de mantener actualizado el diccionario de términos por categoría de delito.
- La generación automática de resumen, fortalezas, debilidades y estrategias del caso (campos de `ResultadoCaso`) está definida a nivel de modelo y API, pero su contenido no se genera automáticamente en la versión actual; queda como estructura lista para completarse en una fase posterior del proyecto.
- La detección de entidades jurídicas usa coincidencia de texto simple contra el catálogo (`EntidadJuridica`), no reconocimiento de entidades nombradas (NER) propiamente dicho.

---

## Roadmap

- [ ] Mover el pipeline de análisis a ejecución asíncrona (cola de tareas en segundo plano).
- [ ] Ampliar el catálogo a otras ramas del derecho (Civil, Familia, Laboral) y sus respectivos clasificadores de delito/materia.
- [ ] Completar la generación automática de resumen jurídico, fortalezas, debilidades y estrategias del caso.
- [ ] Mejorar la detección de entidades jurídicas más allá de coincidencia de texto exacto.
- [ ] Exportación de resultados de análisis a documentos generados (Word/PDF).