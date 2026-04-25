FROM python:3.12-slim-bookworm

WORKDIR /app

# System deps: Playwright Chromium + Manim (Cairo, Pango, ffmpeg) + build tools for pycairo
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    libcairo2-dev libpango1.0-dev pkg-config \
    gcc python3-dev \
    ffmpeg \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install uv + pin setuptools to silence pkg_resources deprecation (perth/chatterbox)
RUN pip install --no-cache-dir uv "setuptools<81"

# Copy project files
COPY pyproject.toml uv.lock .python-version README.md ./
COPY src/ src/

# CPU-only PyTorch — must be set BEFORE uv sync so it's respected during resolution
ENV UV_TORCH_BACKEND=cpu
ENV UV_NO_BUILD_ISOLATION=0

# Install all deps including all optional extras for full feature set
RUN uv sync --no-dev --extra pdf --extra tts --extra video

# Install Playwright Chromium for PDF export
RUN uv run playwright install chromium

# Pin setuptools inside the venv too (chatterbox pulls it in)
RUN uv run pip install --no-cache-dir "setuptools<81" "Pillow>=10.0"

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
