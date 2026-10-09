# Sistema en Docker

Requiere Docker con Compose 2.24.4 o posterior. Se incluyen React compilado en
Nginx, Django con Gunicorn, PostgreSQL 17 con pgvector, Ollama/Qwen y Tesseract
con español. Ollama queda fijado por digest a la imagen verificada (0.40.1).
No requiere Node, Python, Ollama ni Tesseract instalados en el host
para ejecutar el sistema. El script inicial requiere Python, o se puede preparar
el archivo de entorno manualmente.

## Preparación

Desde la raíz del repositorio:

```powershell
backend/env/Scripts/python.exe scripts/preparar_docker.py
```

El script crea `.env.docker` con claves aleatorias y conserva la clave de cifrado
y la versión de embeddings de `backend/.env` cuando existen. Nunca sobrescribe
un `.env.docker` previo. En otro equipo se puede usar `python scripts/preparar_docker.py`.
Alternativamente, copiar `.env.docker.example` y reemplazar todas sus claves.
`ENCRYPTION_KEY` debe contener 64 caracteres hexadecimales. Para importar datos,
debe ser exactamente la clave con la que fueron cifrados originalmente.

El modelo afinado completo debe estar en
`backend/modelos/sw-derecho-embeddings-v1-final`, incluido `modules.json` y los
pesos. Se monta en modo lectura; no se sustituye por otro modelo al iniciar.
Los modelos y archivos privados se excluyen del contexto de construcción.

## Conservar la base de datos actual

Con `asistenciaabo-db` funcionando en el puerto 5433 y `backend/.env` existente:

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.actual.yaml up -d --build
```

La variante usa las credenciales y la clave de cifrado de `backend/.env`.
No inicia otro PostgreSQL, ni copia o borra los datos. Aplica las migraciones
pendientes del proyecto a esa misma base. Conserva los archivos de `backend/media`.
Una migración normaliza los separadores de las rutas de PDF normativos guardadas
en Windows (`\\` a `/`) para que también funcionen en Linux, sin mover archivos.
Para otro puerto, ajustar `DB_PORT` en `compose.actual.yaml`.

## Instalación independiente

```powershell
docker compose --env-file .env.docker up -d --build
docker compose --env-file .env.docker exec backend python manage.py createsuperuser
```

Esta modalidad crea una base vacía en un volumen propio. No importa los datos
de `asistenciaabo-db` automáticamente. El usuario inicial se crea de forma
interactiva, sin contraseñas incluidas en las imágenes.

Abrir **http://localhost:8080**. Frontend y API comparten origen, incluido el
lector PDF y la cookie de sesión. `WEB_PORT` cambia el puerto; actualizar también
`FRONTEND_URL` y `CSRF_TRUSTED_ORIGINS`. El puerto se publica solo en la máquina local.

Ollama descarga Qwen la primera vez mediante el servicio `ollama-modelo`; el
frontend puede estar disponible antes de que termine esa descarga. Consultar:

```powershell
docker compose --env-file .env.docker logs -f ollama-modelo
docker compose --env-file .env.docker exec ollama ollama list
```

Los pesos descargados se conservan en el volumen de Ollama. La configuración es
de CPU y un modelo a la vez. Tesseract español ya está instalado en la imagen
del backend; no necesita instalación adicional en Windows.

## Operación

Usar los mismos argumentos `-f` del arranque para los comandos de la variante
con base actual. Ejemplos para la instalación independiente:

```powershell
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs -f backend
docker compose --env-file .env.docker exec backend python manage.py check
docker compose --env-file .env.docker exec backend tesseract --list-langs
docker compose --env-file .env.docker stop
docker compose --env-file .env.docker start
docker compose --env-file .env.docker down
```

`down` conserva los volúmenes. `down -v` elimina permanentemente los datos de los
volúmenes de esta instalación: no usarlo para una parada normal. PostgreSQL y
Ollama no publican puertos al host en la instalación independiente.

Persistencia: PostgreSQL y Ollama usan volúmenes; los PDF siguen en
`backend/media`; el modelo afinado permanece en `backend/modelos`; los estáticos
y la caché Hugging Face tienen volúmenes propios. En Linux, los directorios
montados que requieren escritura deben ser accesibles al UID del usuario
`sw-derecho` del contenedor. Los logs se envían a `docker compose logs`.

El backend tiene un solo worker con cuatro hilos. Las tareas actuales usan hilos
y caché en memoria: aumentar workers o réplicas puede perder la visibilidad del
progreso. Redis/Celery no están conectados al flujo actual y no se añaden servicios
inactivos. Los reinicios interrumpen las tareas en curso; detener cuando terminen.

Para HTTPS, configurar el proxy frontal y `COOKIE_SECURE=True`, el dominio en
`ALLOWED_HOSTS` y el origen HTTPS en `CSRF_TRUSTED_ORIGINS`. Esta configuración
por defecto está destinada al uso local por HTTP.

## Verificación realizada

Se construyeron las imágenes y se levantó la variante con la base existente:
frontend, backend y Ollama saludables; el inicializador del modelo termina con
código 0. Se comprobaron la ruta SPA `/documentos`, `/health/`, el rechazo de
consulta de documentos sin autenticación, OCR real de un PDF escaneado, el modelo
afinado de 768 dimensiones y una inferencia real de Qwen. Dentro de Docker pasaron
49 pruebas de disponibilidad, rutas, gestión de PDF, extracción y ranking, y
`pip check` no detectó incompatibilidades.

La revisión del entorno actual encontró 7 registros normativos cuyos archivos
ya faltaban en Windows: Docker y Windows encuentran los mismos 21 de 28 registros.
Esos PDF deben recuperarse de sus fuentes originales; Docker conserva los
registros y los archivos disponibles.
