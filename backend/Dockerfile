FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 tesseract-ocr tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-docker.txt ./
# CPU: evita descargar las bibliotecas CUDA en instalaciones sin GPU.
RUN python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.12.1 \
    && python -m pip install -r requirements-docker.txt
RUN useradd --create-home jurisia && mkdir -p /app/media /app/modelos /app/logs /app/cache /app/staticfiles \
    && chown -R jurisia:jurisia /app
COPY --chown=jurisia:jurisia . .
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh
USER jurisia
EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--worker-class", "gthread", "--threads", "4", "--timeout", "240", "--graceful-timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
