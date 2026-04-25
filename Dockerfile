FROM python:3.12-slim-bookworm

WORKDIR /app

# System deps for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libxshmfence1 && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml uv.lock .python-version README.md ./
COPY src/ src/

# CPU-only PyTorch — skips ~2GB of NVIDIA CUDA packages
ENV UV_TORCH_BACKEND=cpu
# Install all deps including all optional extras for full feature set
RUN uv sync --no-dev --extra pdf --extra tts --extra video

# Install Playwright Chromium for PDF export
RUN uv run playwright install chromium

# HF Spaces runs as non-root — ensure runtime dirs are writable
RUN mkdir -p /app/output /app/uploads /app/rag_index && \
    chmod -R 777 /app/output /app/uploads /app/rag_index

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

VOLUME ["/app/output", "/app/uploads", "/app/rag_index"]
ENV PORT=8000
EXPOSE ${PORT}

CMD studycraft-web --port ${PORT}
