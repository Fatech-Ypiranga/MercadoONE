FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    RUN_MIGRATIONS=1 \
    UVICORN_WORKERS=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.lock

COPY . .

RUN chmod +x /app/scripts/docker-entrypoint.sh /app/scripts/migrate-only.sh \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
