FROM pytorch/pytorch:2.9.1-cuda12.6-cudnn9-devel

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \

    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,video,utility \
    HF_HOME=/models/huggingface \
    TRANSFORMERS_CACHE=/models/huggingface \
    TORCH_HOME=/models/torch \
    WHISPER_CACHE=/models/whisper

RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget curl ca-certificates build-essential xz-utils gnupg2 \
    libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libasound2 libxshmfence1 libglib2.0-0 libgomp1 \
    && wget -q https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n7.1-latest-linux64-gpl-shared-7.1.tar.xz \
    && tar -xf ffmpeg-n7.1-latest-linux64-gpl-shared-7.1.tar.xz \
    && cp -r ffmpeg-n7.1-latest-linux64-gpl-shared-7.1/bin/* /usr/local/bin/ \
    && cp -r ffmpeg-n7.1-latest-linux64-gpl-shared-7.1/lib/* /usr/local/lib/ \
    && rm -rf ffmpeg-n7.1-latest-linux64-gpl-shared-7.1* \
    && ldconfig \
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

RUN mkdir -p /models/huggingface /models/torch /models/whisper \
    /app/output_data/{transcoded_videos,transcriptions,embeddings,scene_timestamps}

COPY preprocessor/entrypoint.sh preprocessor/run_preprocessor.sh /app/
COPY preprocessor/scripts/download_models.py /app/download_models.py
RUN chmod +x /app/entrypoint.sh /app/run_preprocessor.sh

COPY bot /app/bot
COPY preprocessor /app/preprocessor

# Ponowne uruchomienie ldconfig na końcu, by upewnić się, że wszystko jest widoczne
RUN ldconfig

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/app/run_preprocessor.sh"]