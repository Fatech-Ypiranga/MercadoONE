FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    RUN_MIGRATIONS=1 \
    UVICORN_WORKERS=1

WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.lock backend/requirements.txt ./
# pip/setuptools/wheel só são necessários no build: são removidos ao final
# porque o pip embute cópias próprias (vendored) de urllib3/msgpack que
# acumulam CVEs e não são usadas pela aplicação em runtime.
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.lock \
    && pip uninstall -y pip setuptools wheel

COPY backend/ .

RUN chmod +x /app/scripts/docker-entrypoint.sh /app/scripts/migrate-only.sh \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/livez' % __import__('os').environ.get('PORT','8000'))"

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
