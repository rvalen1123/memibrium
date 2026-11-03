FROM python:3.11-slim AS base

WORKDIR /app

# System deps for asyncpg (libpq) and PyMuPDF (optional)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Every module server.py imports at startup. ct_ranker.py and ct_scoring.py were missing, so the image only
# worked when docker-compose bind-mounted the repo over /app (MED-252).
COPY server.py .
COPY ingest_engine.py .
COPY knowledge_taxonomy.py .
COPY hybrid_retrieval.py .
COPY memory_hierarchy.py .
COPY ct_ranker.py .
COPY ct_scoring.py .
COPY skills/ ./skills/

EXPOSE 9999

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9999/health')"

CMD ["python", "server.py"]
