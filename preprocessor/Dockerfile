FROM pytorch/pytorch:2.9.1-cuda12.6-cudnn9-devel

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    NVIDIA_DRIVER_CAPABILITIES=all \
    HF_HOME=/models/huggingface \
    TRANSFORMERS_CACHE=/models/huggingface \
    TORCH_HOME=/models/torch \
    WHISPER_CACHE=/models/whisper \
    LD_LIBRARY_PATH="/usr/local/lib:/opt/conda/lib/python3.12/site-packages/nvidia/cublas/lib:/opt/conda/lib/python3.12/site-packages/nvidia/cudnn/lib:/opt/conda/lib/python3.12/site-packages/ctranslate2.libs:${LD_LIBRARY_PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget curl ca-certificates build-essential \
    libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libasound2 libxshmfence1 libglib2.0-0 libgomp1 \
    && wget -q https://github.com/jellyfin/jellyfin-ffmpeg/releases/download/v7.1.3-1/jellyfin-ffmpeg7_7.1.3-1-jammy_amd64.deb \
    && apt-get install -y ./jellyfin-ffmpeg7_7.1.3-1-jammy_amd64.deb \
    && rm jellyfin-ffmpeg7_7.1.3-1-jammy_amd64.deb \
    && ln -sf /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg \
    && ln -sf /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY preprocessor/requirements.txt /app/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        playwright \
        torchvision \
        accelerate \
        nvidia-cublas-cu12 \
        nvidia-cudnn-cu12 \
        -r /app/requirements.txt \
    && playwright install chromium \
    && playwright install-deps chromium

RUN mkdir -p /models/huggingface /models/torch /models/whisper \
    && python3 -c "from transnetv2_pytorch import TransNetV2; model = TransNetV2(); print('TransNetV2 weights downloaded')"

COPY preprocessor/entrypoint.sh preprocessor/run_preprocessor.sh /app/
COPY preprocessor/scripts/download_models.py /app/download_models.py
RUN chmod +x /app/entrypoint.sh /app/run_preprocessor.sh

COPY bot /app/bot
COPY preprocessor /app/preprocessor

RUN mkdir -p /app/output_data/{transcoded_videos,transcriptions,embeddings,scene_timestamps}

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/app/run_preprocessor.sh"]