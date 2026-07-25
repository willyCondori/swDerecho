# JurisIA — Sistema de Gestión y Análisis Jurídico Asistido por IA

JurisIA es una plataforma para estudios de abogados que permite gestionar clientes y casos, y analizar automáticamente los hechos de un caso para recomendar los artículos legales más aplicables, mediante un pipeline de procesamiento de lenguaje natural (chunking, embeddings, clasificación de delitos y ranking jurídico ponderado).

---

## Tabla de contenidos

- [Visión general](#visión-general)
- [Stack tecnológico](#stack-tecnológico)
- [Arquitectura general](#arquitectura-general)
- [Estructura del backend](#estructura-del-backend)
- [Estructura del frontend](#estructura-del-frontend)
- [Pipeline de Análisis IA](#pipeline-de-análisis-ia)
- [Modelo de datos (resumen)](#modelo-de-datos-resumen)
- [Instalación y puesta en marcha](#instalación-y-puesta-en-marcha)
- [Variables de entorno](#variables-de-entorno)
- [Flujos principales](#flujos-principales)
- [Limitaciones conocidas / roadmap](#limitaciones-conocidas--roadmap)
- [Convenciones del proyecto](#convenciones-del-proyecto)

---

## Visión general

El sistema permite a un abogado (o administrador):

1. Registrar **clientes** (con datos cifrados en reposo: nombres, apellidos, teléfono, fecha de nacimiento).
2. Crear un **caso**, ya sea redactando el relato de los hechos como texto libre o adjuntando un **PDF**.
3. Disparar un **análisis con IA** sobre el caso, que:
   - Divide el texto en fragmentos (*chunks*).
   - Genera *embeddings* vectoriales de cada fragmento.
   - Detecta entidades jurídicas relevantes (víctima, menor de edad, cónyuge, etc.).
   - Clasifica el tipo de delito por coincidencia de palabras clave (sin LLM, por ahora).
   - Compara contra los artículos del catálogo normativo cargado (Constitución, Código Penal, etc.) usando búsqueda vectorial (pgvector + HNSW).
   - Genera un **ranking ponderado** de los artículos más aplicables al caso.
5. Revisar el historial de **casos por cliente**, y la **auditoría** de acciones sensibles (creación, edición, eliminación, análisis).

---

## Stack tecnológico

### Backend
- **Python 3.10** + **Django 5.2** + **Django REST Framework**
- **PostgreSQL** con extensión **pgvector** (búsqueda de similitud vectorial, índice HNSW)
- **Celery** (tareas asíncronas) — *actualmente el pipeline corre en modo síncrono porque no hay Redis/broker configurado en desarrollo*
- **sentence-transformers** (`paraphrase-multilingual-mpnet-base-v2`, 768 dimensiones) para generación de embeddings
- **pypdf** para extracción de texto de documentos PDF
- **drf-spectacular** para documentación OpenAPI/Swagger (`/api/docs/`)
- Cifrado simétrico (AES) para campos sensibles de clientes (`core/encryption/aes_encryption.py`)

### Frontend
- **React** + **Vite**
- **React Router** (rutas protegidas, lazy loading con `React.lazy` + `Suspense`)
- **Axios** para consumo de la API
- CSS Modules por página/componente
- Iconos [Tabler Icons](https://tabler.io/icons) (`ti ti-*`)

---

## Arquitectura general

```
┌─────────────────────┐        ┌──────────────────────────┐
│   Frontend (React)   │ <----> │   Backend (Django REST)   │
│  localhost:5173       │  HTTP  │   localhost:8000           │
└─────────────────────┘        └──────────────────────────┘
                                          │
                                          ▼
                                ┌──────────────────┐
                                │   PostgreSQL       │
                                │   + pgvector        │
                                └──────────────────┘
                                          │
                                          ▼
                                ┌──────────────────┐
                                │  Modelo de          │
                                │  embeddings          │
                                │  (sentence-           │
                                │  transformers)       │
                                └──────────────────┘
```

El backend está organizado en **módulos Django independientes** (apps), cada uno con su propio conjunto de modelos, serializers, vistas y URLs, registrados bajo un prefijo propio en `config/urls.py`.

---

## Estructura del backend

```
backend/
├── config/
│   ├── settings.py          # Configuración global, incluye SENTENCE_TRANSFORMER_MODEL
│   └── urls.py               # Registro de todos los módulos bajo /api/<modulo>/
│
├── core/
│   ├── encryption/            # Cifrado/descifrado AES de campos sensibles
│   └── permissions/            # Roles (EsAbogado, EsAdmin) y mixin de auditoría
│
├── modulo_usuarios/            # Autenticación, roles, perfiles de usuario
├── modulo_clientes/
│   ├── models/cliente.py       # Cliente (nombres/apellidos/teléfono cifrados)
│   ├── serializers/            # ClienteReadSerializer, ClienteWriteSerializer, ClienteListSerializer
│   └── views/cliente_view.py   # CRUD + /buscar/ + /lista/ + /{id}/casos/
│
├── modulo_casos/
│   ├── models/
│   │   ├── caso.py
│   │   ├── hecho.py
│   │   ├── petitorio.py
│   │   └── resultado_caso.py    # Resultado del análisis IA (resumen, fortalezas, etc.)
│   ├── serializers/
│   │   ├── caso_serializer.py         # Create/Read/Update/List + Hecho/Petitorio/Resultado
│   │   └── caso_con_cliente_serializer.py  # Crea cliente + caso en una transacción
│   └── views/caso_view.py       # CRUD + /crear_con_cliente/ + /subir_pdf/ + /analizar/ + ...
│
├── modulo_catalogo/
│   ├── models/
│   │   ├── rama.py               # RamaDerecho (ej. Penal, Derecho Constitucional)
│   │   ├── norma.py               # Norma (ej. CP, CPE) con sigla
│   │   ├── articulo.py            # Articulo + ArticuloEntidad (relación M2M con entidades)
│   │   └── entidad.py              # EntidadJuridica (catálogo: Víctima, Imputado, etc.)
│   └── serializers/catalogo_serializer.py
│
├── modulo_ia/
│   ├── models/
│   │   ├── chunk.py                # ChunkCaso (fragmentos de texto del caso)
│   │   ├── embedding.py            # EmbeddingChunk, EmbeddingArticulo, EntidadDetectadaCaso
│   │   └── resultado.py            # ResultadoArticulo (ranking con sub-scores)
│   ├── services/
│   │   ├── chunking_service.py            # Parte el texto/PDF en fragmentos
│   │   ├── embedding_service.py            # Genera embeddings vía sentence-transformers
│   │   ├── entidad_service.py               # Detecta entidades jurídicas por matching de texto
│   │   ├── clasificador_delito_service.py   # Clasifica el tipo de delito por palabras clave
│   │   └── ranking_service.py               # Orquesta el ranking ponderado final
│   ├── tasks/analisis_task.py       # Tarea Celery: pipeline completo del análisis
│   └── serializers/ia_serializer.py
│
├── modulo_documentos/          # Documentos adjuntos a un caso (PDF), generación de docx
└── modulo_auditoria/             # Registro de auditoría (quién hizo qué y cuándo)
```

### Convención de rutas (routers)

Cada módulo registra su `ViewSet` con un `DefaultRouter` **en la raíz** (`""`), y es `config/urls.py` quien antepone el prefijo real (`api/casos/`, `api/clientes/`, etc.). Esto evita duplicar el prefijo (ej. `api/casos/casos/`).

```python
# modulo_casos/urls.py
router = DefaultRouter()
router.register(r"", CasoViewSet, basename="casos")

urlpatterns = [path("", include(router.urls))]
```

```python
# config/urls.py
path("api/casos/", include("modulo_casos.urls")),
```

---

## Estructura del frontend

```
frontend/
├── src/
│   ├── api/                      # Wrappers de axios por módulo (casosApi, clientesApi, catalogoApi...)
│   ├── routes/AppRouter.jsx       # Definición de rutas, lazy loading, rutas protegidas/admin-only
│   ├── components/layout/         # AppLayout, PrivateRoute
│   └── modules/
│       ├── auth/pages/LoginPage.jsx
│       ├── dashboard/pages/DashboardPage.jsx
│       ├── casos/
│       │   ├── hooks/
│       │   │   ├── useCasos.js         # Listado con filtros y paginación
│       │   │   ├── useCrearCaso.js      # Creación (cliente nuevo o existente + rama + texto/PDF)
│       │   │   └── useCasoDetail.js     # Detalle, subir PDF, disparar análisis
│       │   └── pages/
│       │       ├── CasosPage.jsx
│       │       ├── NuevoCasoPage.jsx
│       │       └── CasoDetailPage.jsx
│       ├── clientes/
│       │   ├── hooks/useClientes.js, useClienteCasos.js
│       │   └── pages/ClientesPage.jsx, CrearClientePage.jsx, ClienteCasosPage.jsx
│       ├── catalogo/pages/articulos/    # Ver y cargar artículos del catálogo normativo
│       └── usuarios/pages/               # CRUD de usuarios (solo admin)
```

### Patrón hook + página

Cada página compleja delega su estado y lógica de red a un **hook custom** (`useXxx.js`), manteniendo el componente de página enfocado solo en el render. Los hooks manejan: carga de datos, validación de formularios, estados de error/loading, y llamadas a la API.

---

## Pipeline de Análisis IA

El análisis de un caso corre la función `ejecutar_analisis_caso(caso_id)` (`modulo_ia/tasks/analisis_task.py`), disparada desde `POST /api/casos/{id}/analizar/`. Actualmente se ejecuta **de forma síncrona** dentro del propio request HTTP (no hay Celery worker ni broker configurado en desarrollo).

```
Caso
 │
 ├─▶ 1. Chunking (ChunkingService)
 │      - Prioriza el texto extraído del PDF adjunto (vía pypdf); si no hay
 │        PDF con texto extraíble, usa la descripción redactada.
 │      - Parte el texto en fragmentos (~800 caracteres, con 150 de solapamiento).
 │
 ├─▶ 2. Embeddings (EmbeddingService)
 │      - Vectoriza cada chunk con sentence-transformers
 │        (paraphrase-multilingual-mpnet-base-v2, 768 dimensiones).
 │      - Persiste en EmbeddingChunk (OneToOne con ChunkCaso).
 │
 ├─▶ 3. Detección de entidades (EntidadDetectionService)
 │      - Matching de texto simple contra el catálogo EntidadJuridica
 │        (Víctima, Menor de edad, Cónyuge, Servidor Público, etc.).
 │      - Alimenta el score_entidades del ranking.
 │
 ├─▶ 4. Ranking jurídico (RankingService)
 │      - Compara los embeddings del caso contra EmbeddingArticulo
 │        usando pgvector + CosineDistance (índice HNSW).
 │      - Si el caso tiene rama_detectada asignada, filtra candidatos
 │        solo de esa rama (evita ruido de otras normas).
 │      - Clasifica el delito del caso por palabras clave
 │        (ClasificadorDelitoService) y bonifica artículos cuyo título
 │        entre paréntesis (ej. "(ROBO AGRAVADO)") coincide con la
 │        categoría detectada.
 │      - Combina 5 sub-scores con pesos fijos y aplica un umbral
 │        mínimo de relevancia antes de quedarse con el TOP_N.
 │      - Persiste en ResultadoArticulo.
 │
 └─▶ 6. Se crea/actualiza ResultadoCaso (marca el caso como "analizado").
```

### Fórmula de ranking (`RankingService`)

```
score_total = 0.60 × score_semantico
            + 0.15 × score_delito
            + 0.10 × score_entidades
            + 0.10 × score_jerarquia
            + 0.05 × score_frecuencia
```

| Sub-score | Fuente | Descripción |
|---|---|---|
| `score_semantico` | pgvector (CosineDistance) | Similitud del embedding del chunk contra el embedding del artículo. |
| `score_delito` | `ClasificadorDelitoService` | Coincidencia entre el delito detectado por palabras clave en el caso y el título del artículo (ej. "ROBO", "HOMICIDIO"). |
| `score_entidades` | `EntidadDetectionService` | Proporción de entidades jurídicas del caso que también están asociadas al artículo. |
| `score_jerarquia` | Campo `jerarquia_normativa` del artículo | Constitución = 1.0, Código = 0.8, Ley Ordinaria = 0.7, etc. |
| `score_frecuencia` | Campo `frecuencia_historica` del artículo | Normalizado contra el máximo del conjunto de candidatos. |

Además:

- **`CANDIDATOS_POR_CHUNK = 50`**: cuántos vecinos más cercanos se piden a la base por cada chunk.
- **`TOP_N_ARTICULOS = 15`**: máximo de artículos en el resultado final.
- **`UMBRAL_MINIMO_SCORE_TOTAL`**: corta la lista antes de forzar 15 resultados si no hay suficientes artículos realmente relevantes (evita relleno con artículos genéricos de responsabilidad civil, fijación de la pena, etc.).
- Se usa una **cola de prioridad (heap) de tamaño fijo** para quedarse con el top-N sin ordenar el universo completo de candidatos.

### Clasificador de delito (`ClasificadorDelitoService`)

Vive en un archivo separado del `RankingService` para poder escalar a otras ramas del derecho sin tocar la lógica de ranking:

```python
GRUPOS_POR_RAMA = {
    "Penal": GRUPOS_PENAL,
    # "Civil": GRUPOS_CIVIL,   ← agregar aquí cuando se sumen más normas
}
```

Cada grupo de delito define:
- `titulos`: variantes del título del artículo tal como aparece entre paréntesis en el texto legal (ej. `["ROBO", "ROBO AGRAVADO"]`).
- `keywords`: palabras/fragmentos coloquiales y jurídicos que suelen aparecer en el relato de hechos de ese tipo de caso.

Es un clasificador de reglas (sin LLM ni modelo entrenado), pensado como solución intermedia hasta integrar un clasificador real o el LLM planeado.

---

## Modelo de datos (resumen)

```
Cliente ──┐
          │ 1
          │
          ▼ N
        Caso ──────┬─── Hecho (M2M vía HechoCaso, con orden)
          │          ├─── Petitorio (M2M vía PetitorioCaso)
          │          ├─── ResultadoCaso (1:1 — resumen IA)
          │          ├─── ChunkCaso (1:N — fragmentos)
          │          │       └─ EmbeddingChunk (1:1)
          │          │       └─ EntidadDetectadaCaso (1:N)
          │          ├─── ResultadoArticulo (1:N — ranking)
          │          ├─── Documento (PDF adjunto)
          │          └─── rama_detectada → RamaDerecho
          │
          ▼
       Usuario (abogado a cargo)

Articulo ──┬── Norma (ej. CP, CPE)
           ├── RamaDerecho (ej. Penal, Constitucional)
           ├── ArticuloEntidad (M2M) → EntidadJuridica
           └── EmbeddingArticulo (1:1)
```

**Nota de seguridad:** `Cliente.nombres`, `apellidos`, `telefono` y `fecha_nacimiento` se almacenan **cifrados** (`core/encryption/aes_encryption.py`) y se descifran únicamente al serializar la respuesta (`safe_decrypt`).

---

## Instalación y puesta en marcha

### Backend

```bash
cd backend
python -m venv env
env\Scripts\activate          # Windows
# source env/bin/activate     # Linux/Mac

pip install -r requirements.txt

# Variables de entorno (ver sección siguiente)

python manage.py migrate
python manage.py runserver
```

El servidor queda disponible en `http://127.0.0.1:8000/`. Documentación interactiva de la API en `http://127.0.0.1:8000/api/docs/`.

**Primera carga de datos necesaria:**
1. Cargar ramas del derecho (`RamaDerecho`) y normas (`Norma`) vía el panel de administración o fixtures.
2. Cargar el catálogo de artículos (`Articulo`) — hay una sección "Cargar Documentos" en el frontend para esto.
3. Poblar `ArticuloEntidad` (relación artículo ↔ entidad jurídica) para que `score_entidades` no quede siempre en 0. Ver script de población en la sección de mantenimiento del pipeline IA.
4. Generar embeddings de todos los artículos activos (`EmbeddingArticulo`) tras cualquier cambio del modelo de `sentence-transformers` configurado.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Disponible en `http://localhost:5173/`.

### Notas para desarrollo en Windows

- El pipeline de IA corre **en modo síncrono** (sin `.delay()`) porque no hay Redis/broker configurado. Si se instala Celery + Redis más adelante, hay que volver a usar `ejecutar_analisis_caso.delay(caso.pk)` en `CasoViewSet.analizar()` y correr un worker aparte:
  ```bash
  celery -A config worker -l info --pool=solo
  ```
  (`--pool=solo` es necesario en Windows).
- El análisis puede tardar más de 30 segundos (carga del modelo de embeddings + comparación vectorial). El método `casosApi.analizar()` en el frontend debe usar un timeout extendido (`timeout: 300000` o similar) en vez del timeout global de axios.

---

## Variables de entorno

Configurar en `.env` o directamente en `config/settings.py` según el entorno:

| Variable | Descripción |
|---|---|
| `SENTENCE_TRANSFORMER_MODEL` | Modelo de embeddings. Debe ser **multilingüe** para textos en español (ej. `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, 768 dimensiones). |
| `DATABASE_URL` / config de `DATABASES` | Conexión a PostgreSQL con extensión `pgvector` habilitada. |
| `CELERY_BROKER_URL` | Solo necesario si se activa el modo asíncrono con Celery + Redis. |
| Claves de cifrado (AES) | Usadas por `core/encryption/aes_encryption.py` para cifrar campos sensibles de `Cliente`. |

**Importante:** si se cambia `SENTENCE_TRANSFORMER_MODEL`, hay que **regenerar todos los embeddings existentes** (tanto de artículos como de casos ya analizados), porque vectores generados con modelos distintos no son comparables entre sí.

---

## Flujos principales

### 1. Crear un caso

`NuevoCasoPage` → `useCrearCaso` permite:
- Elegir **cliente nuevo** (crea el cliente primero vía `POST /api/clientes/clientes/`) o **cliente existente** (buscador con autocompletado vía `GET /api/clientes/buscar/`).
- Seleccionar la **rama del derecho** (o dejar en blanco para detección automática futura).
- Redactar el caso como **texto** o adjuntar un **PDF**.
- Al enviar, crea el caso vía `POST /api/casos/` con `cliente_id`, `rama_detectada_id` (opcional), `titulo`, `descripcion` y/o `archivo_pdf`.

### 2. Analizar un caso

`CasoDetailPage` → botón "Analizar caso con IA" → `POST /api/casos/{id}/analizar/` → corre el pipeline completo (ver sección anterior) → al finalizar, se recarga el caso (`reload()`) para mostrar el ranking de artículos actualizado.

### 3. Ver casos de un cliente

`ClientesPage` → clic en una fila → `/clientes/:id` (`ClienteCasosPage`) → lista los casos de ese cliente vía `GET /api/clientes/{id}/casos/` → clic en un caso → `/casos/:id` (detalle completo).

---

## Limitaciones conocidas / roadmap

- [ ] El **modo síncrono** del análisis bloquea el request HTTP mientras corre todo el pipeline; migrar a Celery + Redis para no depender de timeouts largos en el frontend.
- [ ] El **clasificador de delito** (`ClasificadorDelitoService`) es basado en reglas/palabras clave; cubre bien Robo, Hurto, Homicidio, Lesiones, Violación, Secuestro, Estafa y Amenazas para la rama Penal, pero debe extenderse (o reemplazarse por un clasificador entrenado / LLM) a medida que se agreguen más ramas del derecho.
- [ ] Confirmar si la **Ley 348** (violencia hacia la mujer, Bolivia) está cargada como norma separada del Código Penal genérico, para priorizarla correctamente en casos de violencia intrafamiliar.
- [ ] El **umbral de corte del ranking** (`UMBRAL_MINIMO_SCORE_TOTAL`) está calibrado de forma manual con casos de prueba; conviene revisarlo con más ejemplos reales de distintos tipos de delito.
- [ ] Poblar y mantener actualizado `ArticuloEntidad` cada vez que se cargan artículos nuevos al catálogo.

---

## Convenciones del proyecto

- **Nombres de campos en API**: los serializers de creación (`CasoCreateSerializer`, `ClienteWriteSerializer`) suelen exponer el campo como `<relacion>_id` (ej. `cliente_id`, `rama_detectada_id`) aunque el modelo tenga el FK con otro nombre (`source=`). Confirmar siempre el nombre exacto del campo contra el serializer antes de armar el payload del frontend.
- **Soft-delete**: los modelos con campo `estado` (booleano) usan soft-delete — `destroy()` marca `estado=False` en vez de eliminar el registro.
- **Auditoría**: las acciones sensibles (crear, editar, eliminar, analizar) se registran vía `AuditoriaMixin._auditar()` o `registrar_auditoria()`, en la tabla de auditoría del módulo correspondiente.
- **Patrón hook + página** en el frontend: la lógica de red/estado vive en `hooks/useXxx.js`; las páginas (`pages/XxxPage.jsx`) solo consumen el hook y renderizan.
- **CSS Modules**: cada página tiene su propio `Xxx.module.css`; los estilos no se comparten entre páginas salvo variables CSS globales (`--c-text-muted`, `--c-border-strong`, `--c-purple-500`, etc.).