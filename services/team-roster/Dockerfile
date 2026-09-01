# =====================================================================
# team-roster - Dockerfile (FastAPI)
# =====================================================================

# --- Stage 1: risolve le dipendenze con uv, da pyproject.toml + uv.lock.
#     requirements.txt non e' committato: viene generato qui a ogni build
#     (equivalente a `uv export --no-hashes --no-dev`), cosi' resta sempre
#     allineato al lock file senza un passaggio manuale. ---
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS deps
WORKDIR /src
COPY pyproject.toml uv.lock ./
RUN uv export --no-hashes --no-dev --format requirements.txt -o requirements.txt

# --- Stage 2: immagine runtime, solo pip (uv resta nello stage di build) ---
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY --from=deps /src/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
