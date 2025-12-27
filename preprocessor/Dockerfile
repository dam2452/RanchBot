FROM pytorch/pytorch:2.9.1-cuda12.6-cudnn9-devel

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,video,utility \
    HF_HOME=/models/huggingface \
    TORCH_HOME=/models/torch \
    WHISPER_CACHE=/models/whisper \
    INSIGHTFACE_HOME=/models/insightface \
    CUBLAS_WORKSPACE_CONFIG=:4096:8 \
    TOKENIZERS_PARALLELISM=false

RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget curl ca-certificates build-essential gnupg2 \
    libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libasound2 libxshmfence1 libglib2.0-0 libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q https://github.com/jellyfin/jellyfin-ffmpeg/releases/download/v7.1.3-1/jellyfin-ffmpeg7_7.1.3-1-jammy_amd64.deb \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ./jellyfin-ffmpeg7_7.1.3-1-jammy_amd64.deb \
    && rm jellyfin-ffmpeg7_7.1.3-1-jammy_amd64.deb \
    && ln -sf /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg \
    && ln -sf /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY preprocessor/requirements.txt /app/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install \
        playwright \
        torchvision \
        accelerate \
        nvidia-cublas-cu12 \
        nvidia-cudnn-cu12 \
        -r /app/requirements.txt

RUN playwright install chromium \
    && playwright install-deps chromium

RUN mkdir -p /models/huggingface /models/torch /models/whisper /models/insightface \
    /app/output_data/{transcoded_videos,transcriptions,embeddings,scene_timestamps}

COPY preprocessor/entrypoint.sh preprocessor/run_preprocessor.sh /app/
COPY preprocessor/scripts/download_models.py /app/download_models.py
RUN chmod +x /app/entrypoint.sh /app/run_preprocessor.sh

COPY bot /app/bot
COPY preprocessor /app/preprocessor

ENV LD_LIBRARY_PATH=/usr/lib/jellyfin-ffmpeg/lib:/opt/conda/lib/python3.11/site-packages/nvidia/cublas/lib:/opt/conda/lib/python3.11/site-packages/nvidia/cudnn/lib:/opt/conda/lib/python3.11/site-packages/ctranslate2.libs:${LD_LIBRARY_PATH}

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/app/run_preprocessor.sh"]