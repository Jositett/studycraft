FROM python:3.12-slim-bookworm

WORKDIR /app

# System deps + uv + setuptools (merged to reduce layers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    libcairo2-dev libpango1.0-dev pkg-config \
    gcc python3-dev \
    ffmpeg \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv "setuptools<81"

# Copy project files
COPY pyproject.toml uv.lock .python-version README.md ./
COPY src/ src/

# CPU-only PyTorch — must be set BEFORE uv sync so it's respected during resolution
ENV UV_TORCH_BACKEND=cpu
ENV UV_NO_BUILD_ISOLATION=0

# Install deps, Playwright, setuptools pin, and create runtime dirs (merged to reduce layers)
RUN uv sync --no-dev --extra pdf --extra tts --extra video \
    && uv run playwright install chromium \
    && uv run pip install --no-cache-dir "setuptools<81" "Pillow>=10.0" \
    && mkdir -p /app/output /app/uploads /app/rag_index \
    && chmod -R 777 /app/output /app/uploads /app/rag_index

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# Accept HF_TOKEN and other secrets as build/runtime args
ARG HF_TOKEN=""
ENV HF_TOKEN=${HF_TOKEN}

# OPENROUTER_API_KEY and STUDYCRAFT_WEB_TOKEN should be set at runtime via docker run -e
# or in docker-compose.yml environment section

VOLUME ["/app/output", "/app/uploads", "/app/rag_index"]
ENV PORT=8000
EXPOSE ${PORT}

# rebuild trigger: faadedb
CMD ["studycraft-web", "--port", "8000"]
