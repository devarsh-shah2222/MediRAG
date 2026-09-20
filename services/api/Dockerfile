FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Render (and most Docker PaaS hosts) inject PORT and route traffic there;
# default to 8000 for local `docker run` / docker-compose where it's unset.
#
# seed and ingest_real_sources are both idempotent (existence/content-hash
# checked, safe to re-run every boot). ingest_real_sources makes live calls
# to openFDA/MedlinePlus with no retry/error handling around them, so it's
# `|| true`'d -- a transient network failure there should never prevent the
# API itself from starting; the next successful boot fills in the content.
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed && (python -m scripts.ingest_real_sources || true) && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
