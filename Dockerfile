# syntax=docker/dockerfile:1.7
# ─────────────────────────────────────────────────────────────
# Finnie Dockerfile — multi-stage build for production-ready image.
#
# Stage 1 (builder): install dependencies via uv into a venv.
# Stage 2 (runtime): copy the venv + app code into a slim base.
#
# Why multi-stage: keeps the final image small. The builder has
# compilers and caches we don't need at runtime.
# ─────────────────────────────────────────────────────────────

# ============= STAGE 1: BUILDER =============
FROM python:3.12-slim AS builder

# Copy uv binary from the official uv image — fast, no install dance.
COPY --from=ghcr.io/astral-sh/uv:0.5.18 /uv /uvx /bin/

# Optimization flags for uv inside Docker.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/python

WORKDIR /app

# Copy ONLY dependency manifests first. This is the caching trick:
# as long as pyproject.toml + uv.lock don't change, Docker reuses
# the cached layer for the heavy `uv sync` step — even when your
# src/ code changes.
COPY pyproject.toml uv.lock ./

# Install dependencies (but NOT the project itself yet — we don't
# have src/ in the image yet).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# NOW copy the application code. Anything below this line invalidates
# only when source code changes, not when deps change.
COPY src ./src
COPY config.yaml README.md ./
COPY chroma_db ./chroma_db

# Install the project itself (this is fast — just links src/ into the venv).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Pre-download spaCy model required by Presidio for PII detection.
# Without this, Presidio tries to download at runtime; the slim runtime
# stage has no pip/uv and the non-root user can't write to site-packages.
RUN .venv/bin/python -m spacy download en_core_web_sm


# ============= STAGE 2: RUNTIME =============
FROM python:3.12-slim

# Security: never run as root in production. Create a non-privileged user.
RUN groupadd --system finnie && useradd --system --gid finnie finnie

WORKDIR /app

# Copy the built venv + app code from the builder stage.
# --chown ensures the finnie user owns these files.
COPY --from=builder --chown=finnie:finnie /app /app

# Ensure /app itself is finnie-owned (COPY --chown only sets ownership of *contents*).
# Without this, finnie can't create new files/dirs at /app root (e.g. chroma DB locks).
RUN chown finnie:finnie /app

# Put the venv's bin on PATH so `uvicorn` is callable without `uv run`.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Switch to non-root user.
USER finnie

# Document that the container listens on port 8000.
# (EXPOSE is metadata — it doesn't actually publish the port.)
EXPOSE 8000

# Container-level health check. Docker pings /health every 30 seconds;
# if it ever fails, the container is marked "unhealthy" and load
# balancers (or docker compose) can react.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"

# The command that runs when a container starts.
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]