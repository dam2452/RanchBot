# =============================================================================
# OPTIMIZED DOCKERFILE - All models cached in external volumes
# =============================================================================
#
# CACHE STRATEGY:
#   /app/.cache/          → model_cache volume (HuggingFace, Torch, Whisper)
#   /root/.ollama/        → ollama_models volume (Ollama models)
#
# USAGE:
#   docker-compose build
#   docker-compose up -d
#   # First run auto-downloads all models to volumes
#   # Subsequent runs/rebuilds use cached models
#
# =============================================================================

FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# -----------------------------------------------------------------------------
# Layer 1: System dependencies (changes rarely)
# -----------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    python3.11-dev \
    ffmpeg \
    git \
    wget \
    curl \
    build-essential \
    libnspr4 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3

# -----------------------------------------------------------------------------
# Layer 2: Ollama binary (changes rarely)
# -----------------------------------------------------------------------------
RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app

# -----------------------------------------------------------------------------
# Layer 3: Python requirements (changes occasionally)
# -----------------------------------------------------------------------------
COPY preprocessor/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir accelerate playwright && \
    playwright install chromium && \
    playwright install-deps chromium

# -----------------------------------------------------------------------------
# Layer 4: Environment configuration
# -----------------------------------------------------------------------------
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface
ENV TORCH_HOME=/app/.cache/torch
ENV WHISPER_CACHE=/app/.cache/whisper
ENV OLLAMA_MODELS=/root/.ollama/models
ENV LD_LIBRARY_PATH="/usr/local/lib/python3.11/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.11/dist-packages/ctranslate2.libs:${LD_LIBRARY_PATH}"

# Create cache directories (will be overlaid by volumes)
RUN mkdir -p /app/.cache/huggingface \
             /app/.cache/torch \
             /app/.cache/whisper \
             /root/.ollama/models

# -----------------------------------------------------------------------------
# Layer 5: Scripts (changes rarely)
# -----------------------------------------------------------------------------
COPY preprocessor/entrypoint.sh /app/entrypoint.sh
COPY preprocessor/download_models.py /app/download_models.py
RUN chmod +x /app/entrypoint.sh /app/download_models.py

# -----------------------------------------------------------------------------
# Layer 6: Application code (changes frequently - LAST!)
# -----------------------------------------------------------------------------
COPY bot /app/bot
COPY preprocessor /app/preprocessor

# Create working directories
RUN mkdir -p /app/preprocessed/transcoded_videos \
             /app/preprocessed/transcriptions \
             /app/preprocessed/embeddings \
             /app/preprocessed/scene_timestamps

EXPOSE 11434

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["bash"]