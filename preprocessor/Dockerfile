FROM pytorch/pytorch:2.9.0-cuda12.8-cudnn9-devel

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,video,utility \
    HF_HOME=/models/huggingface \
    TORCH_HOME=/models/torch \
    WHISPER_CACHE=/models/whisper \
    INSIGHTFACE_HOME=/models/insightface \
    YOLO_CONFIG_DIR=/models/ultralytics \
    CUBLAS_WORKSPACE_CONFIG=:4096:8 \
    TOKENIZERS_PARALLELISM=false \
    VLLM_WORKER_MULTIPROC_METHOD=spawn

RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget curl ca-certificates gnupg2 \
    libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libasound2 libxshmfence1 libglib2.0-0 libgomp1 \
    ninja-build \
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

COPY preprocessor/requirements.txt /app/

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip setuptools wheel

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
    -r /app/requirements.txt \
    --extra-index-url https://pypi.nvidia.com \
    --extra-index-url https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
    vllm==0.13.0 \
    onnxruntime-gpu==1.21.0

RUN patchright install chromium \
    && patchright install-deps chromium

RUN playwright install chromium \
    && playwright install-deps chromium

RUN mkdir -p /models/huggingface /models/torch /models/whisper /models/insightface /models/ultralytics \
    /app/output_data/{transcoded_videos,transcriptions,embeddings,scene_timestamps}

COPY bot /app/bot
COPY preprocessor /app/preprocessor

ENV LD_LIBRARY_PATH=/usr/lib/jellyfin-ffmpeg/lib:/opt/conda/lib/python3.11/site-packages/nvidia/cublas/lib:/opt/conda/lib/python3.11/site-packages/nvidia/cudnn/lib:/opt/conda/lib/python3.11/site-packages/onnxruntime/capi:/opt/conda/lib/python3.11/site-packages/ctranslate2.libs:${LD_LIBRARY_PATH}

WORKDIR /app

ENTRYPOINT ["python", "-m", "preprocessor.cli"]
CMD ["--help"]
