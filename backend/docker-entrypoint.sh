#!/bin/sh
set -eu
if [ "${1:-}" = "gunicorn" ] || [ "${1:-}" = "uvicorn" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
fi
exec "$@"
