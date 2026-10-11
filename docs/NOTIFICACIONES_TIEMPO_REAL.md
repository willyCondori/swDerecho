# Notificaciones en tiempo real y lector de casos

Las resoluciones relacionadas se abren con el lector existente en una ventana
del caso, sin navegar al catálogo. Se mantiene el enlace a la fuente oficial.

La campana usa `/ws/notificaciones/`. Envía el JWT de acceso en el primer
mensaje, nunca en la URL. El servidor valida el origen, el token y el usuario,
y cierra la conexión cuando vence el token. El cliente usa la renovación de
sesión existente, reconecta con espera progresiva y limpia la conexión al
desmontar. En HTTPS usa WSS automáticamente.

Una función y un trigger PostgreSQL publican únicamente el identificador del
destinatario después del commit. Cada proceso ASGI escucha una conexión LISTEN
compartida entre sus sockets y envía contadores a las suscripciones de ese
usuario. No transmite títulos ni datos de casos por el canal de base de datos.
También recoge cambios masivos de lectura. El rollback no publica eventos.

Se consulta una vez el contador al abrir la sesión; luego se actualiza por
eventos. La lista solo se consulta al abrir la campana o recibir cambios con
el panel abierto. Si el canal falla, se conserva una consulta de respaldo
cada 60 segundos mientras se reconecta; no se sondea durante una conexión sana.

Docker usa Uvicorn/ASGI y Nginx reenvía Upgrade en `/ws/`. Para desarrollo local:

```sh
pip install -r requirements-realtime.txt
python manage.py migrate
uvicorn config.asgi:application --host 0.0.0.0 --port 8000
```

`manage.py runserver` sin servidor ASGI conserva HTTP, pero no este WebSocket.
Migración: `modulo_notificaciones/0003_eventos_tiempo_real.py`.
# Recuperación tras reinicios de Docker

El proxy Nginx resuelve `backend` mediante el DNS interno de Docker cada cinco
segundos, también para `/api/` y `/health/`, para recuperar su dirección si se
recrea el contenedor. Durante el arranque del servidor puede haber respuestas
502 y avisos de WebSocket fallido en la consola del navegador; la conexión se
reintenta automáticamente con espera creciente hasta 30 segundos.

El cliente también reintenta ante errores de construcción o de renovación de
sesión. Si una conexión no recibe un contador válido en diez segundos, la cierra
para reintentar. Los temporizadores se cancelan al salir de la sesión y el sondeo
HTTP de respaldo se detiene cuando vuelven a recibirse eventos válidos.

