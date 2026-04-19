FROM python:3.12-slim-bookworm

WORKDIR /app

# System deps for weasyprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev libcairo2 && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy project
COPY pyproject.toml .python-version README.md ./
COPY src/ src/

# CPU-only PyTorch — skips ~2GB of NVIDIA CUDA packages
ENV UV_TORCH_BACKEND=cpu
RUN uv sync --extra web --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

VOLUME ["/app/output", "/app/uploads", "/app/rag_index"]
EXPOSE 8000

CMD ["studycraft-web"]
