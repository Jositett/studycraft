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
RUN uv sync --no-dev

# Install Playwright Chromium for PDF export
RUN uv run playwright install chromium

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

VOLUME ["/app/output", "/app/uploads", "/app/rag_index"]
EXPOSE 8000

CMD ["studycraft-web"]
