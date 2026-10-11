# Seguridad de API y despliegue

El entorno local conserva `http://localhost:8080`. HTTPS se activa con un archivo Compose adicional; no se debe activar `DEPLOY_HTTPS` usando el proxy HTTP local.

## API

- Una contraseña temporal permite consultar la sesión, cambiar la contraseña y cerrar sesión. Las demás API autenticadas responden 403 con `code=password_change_required`. La renovación permite completar ese flujo; no habilita módulos. Usuarios inactivos tampoco pueden renovar ni utilizar su access token.
- Administrador, abogado y asistente pueden leer casos activos y sus documentos, fragmentos y resultados. Se conserva la política del listado de casos. El asistente sigue sin permiso de escritura. Documentos de casos eliminados dejan de ser consultables, incluso mediante sus identificadores; los archivos no se exponen en `/media/`.
- `/api/schema/` y `/api/docs/` requieren un JWT de administrador activo que ya haya cambiado su contraseña. Para Swagger se debe enviar `Authorization: Bearer <access_token>`; abrir la URL sin esa cabecera devuelve 401.
- Límites configurables: `RATE_LOGIN=10/min`, `RATE_RECOVERY=5/hour`, `RATE_RECOVERY_CONFIRM=10/min`, `RATE_ANALYSIS_BURST=2/min`, `RATE_ANALYSIS_DAILY=50/day`. Login y recuperación se limitan por IP; los dos endpoints de análisis comparten límites por usuario. DRF responde 429 con `Retry-After`. Sigue vigente el bloqueo por intentos fallidos de cada cuenta.
- Los contadores DRF se comparten en PostgreSQL mediante la tabla `security_throttle_cache`, creada por una migración. DRF usa contadores aproximados ante peticiones simultáneas; Nginx añade un límite de autenticación por IP en memoria compartida. El backend debe permanecer sin puerto publicado: solo Nginx puede suministrar la cabecera de IP y protocolo confiables.

## HTTPS

1. Obtener un certificado válido para el dominio de despliegue. Guardar `fullchain.pem` y `privkey.pem` en una carpeta fuera del repositorio y limitar el acceso a la clave privada. El certificado no se genera ni renueva automáticamente.
2. En el entorno de despliegue, configurar `DEPLOY_DOMAIN` (solo el dominio), `TLS_CERT_DIR` (ruta absoluta de esa carpeta) y `HTTPS_BIND_IP=0.0.0.0` para publicar el servicio. Mantener secretos y datos de conexión en `.env.docker`, fuera de Git.
3. Ejecutar:

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.https.yaml up -d --build
```

Si se utiliza la base externa del entorno actual, añadir `-f compose.actual.yaml` **antes** de `-f compose.https.yaml`.

El proxy redirige HTTP a HTTPS, acepta TLS 1.2/1.3 y utiliza WSS para notificaciones. La configuración activa cookies Secure para refresh, CSRF y sesión; refresh mantiene HttpOnly y SameSite=Lax. Django reconoce el protocolo del proxy, exige HTTPS y añade HSTS durante un año, sin incluir otros subdominios. Nginx añade nosniff, prohibición de enmarcado, política de referentes, restricciones de cámara/micrófono/geolocalización y CSP para impedir objetos y enmarcado externos. Esta CSP es una base compatible con los visores y estilos existentes, no una protección completa frente a XSS.

## Comprobación después del despliegue

Comprobar la redirección HTTP, la validez del certificado sin omitir su verificación, las cabeceras HTTPS, cookies Secure al iniciar sesión, conexiones WSS y el rechazo de schema/docs sin credenciales. Renovar el certificado antes de su vencimiento y recargar Nginx. `/health/` permanece disponible para las comprobaciones internas.
