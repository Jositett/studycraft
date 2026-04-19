# ── Build stage ───────────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Install system deps for weasyprint (PDF export)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev libcairo2 && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .python-version README.md ./
COPY src/ src/

# Install all deps including web extras
RUN uv sync --extra web --no-dev

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm

WORKDIR /app

# System deps for weasyprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libcairo2 && \
    rm -rf /var/lib/apt/lists/*

# Copy venv and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/README.md ./

# Put venv on PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Volumes for persistent data
VOLUME ["/app/output", "/app/uploads", "/app/rag_index"]

EXPOSE 8000

# Default: run the web UI. Override with CLI commands:
#   docker run studycraft studycraft generate /app/uploads/doc.pdf
CMD ["studycraft-web"]
