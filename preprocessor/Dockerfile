# =============================================================================
# OPTIMIZED DOCKERFILE - All models cached in single volume
# =============================================================================

FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_DRIVER_CAPABILITIES=all

# -----------------------------------------------------------------------------
# Layer 1: System dependencies (changes rarely)
# -----------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    python3.11-dev \
    git \
    wget \
    build-essential \
    pkg-config \
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
# Layer 1.5: Jellyfin FFmpeg (NVENC Support) - auto-detect distro
# -----------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    ca-certificates \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://repo.jellyfin.org/jellyfin_team.gpg.key | gpg --dearmor -o /etc/apt/keyrings/jellyfin.gpg && \
    export VERSION_CODENAME=$(grep VERSION_CODENAME /etc/os-release | cut -d= -f2) && \
    export ID=$(grep "^ID=" /etc/os-release | cut -d= -f2 | tr -d '"') && \
    if [ -z "$VERSION_CODENAME" ]; then export VERSION_CODENAME="jammy"; fi && \
    echo "deb [signed-by=/etc/apt/keyrings/jellyfin.gpg] https://repo.jellyfin.org/${ID} ${VERSION_CODENAME} main" > /etc/apt/sources.list.d/jellyfin.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends jellyfin-ffmpeg7 && \
    rm -rf /var/lib/apt/lists/* && \
    ln -s /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg && \
    ln -s /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe

# -----------------------------------------------------------------------------
# Layer 2: Python and Playwright
# -----------------------------------------------------------------------------
WORKDIR /app

COPY preprocessor/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir playwright && \
    playwright install chromium && \
    playwright install-deps chromium

# -----------------------------------------------------------------------------
# Layer 3: Ollama binary (changes rarely)
# -----------------------------------------------------------------------------
RUN curl -fsSL https://ollama.com/install.sh | sh

# -----------------------------------------------------------------------------
# Layer 4: Python ML requirements (changes occasionally)
# -----------------------------------------------------------------------------
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir accelerate && \
    pip install --no-cache-dir nvidia-cublas-cu12 nvidia-cudnn-cu12

# -----------------------------------------------------------------------------
# Layer 4.5: Initialize TransNetV2 model weights (download during build)
# -----------------------------------------------------------------------------
RUN python3 -c "from transnetv2_pytorch import TransNetV2; model = TransNetV2(); print('TransNetV2 weights downloaded')"

# -----------------------------------------------------------------------------
# Layer 5: Environment configuration
# -----------------------------------------------------------------------------
ENV HF_HOME=/models/huggingface
ENV TRANSFORMERS_CACHE=/models/huggingface
ENV TORCH_HOME=/models/torch
ENV WHISPER_CACHE=/models/whisper
ENV OLLAMA_MODELS=/models/ollama
ENV OLLAMA_MAX_LOADED_MODELS=1
ENV OLLAMA_HOST=0.0.0.0
ENV LD_LIBRARY_PATH="/usr/local/lib/python3.11/dist-packages/nvidia/cublas/lib:/usr/local/lib/python3.11/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.11/dist-packages/ctranslate2.libs:${LD_LIBRARY_PATH}"

# Create model directories (will be overlaid by volume)
RUN mkdir -p /models/huggingface \
             /models/torch \
             /models/whisper \
             /models/ollama

# -----------------------------------------------------------------------------
# Layer 6: Scripts (changes rarely)
# -----------------------------------------------------------------------------
COPY preprocessor/entrypoint.sh /app/entrypoint.sh
COPY preprocessor/scripts/download_models.py /app/download_models.py
COPY preprocessor/run_preprocessor.sh /app/run_preprocessor.sh
RUN chmod +x /app/entrypoint.sh /app/run_preprocessor.sh

# -----------------------------------------------------------------------------
# Layer 7: Application code (changes frequently - LAST!)
# -----------------------------------------------------------------------------
COPY bot /app/bot
COPY preprocessor /app/preprocessor

# Create working directories
RUN mkdir -p /app/output_data/transcoded_videos \
             /app/output_data/transcriptions \
             /app/output_data/embeddings \
             /app/output_data/scene_timestamps

EXPOSE 11434

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/app/run_preprocessor.sh"]