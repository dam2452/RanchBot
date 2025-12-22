# =============================================================================
# BUILDER STAGE - Decord with GPU support
# =============================================================================
FROM nvidia/cuda:12.1.0-devel-ubuntu22.04 AS decord-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    wget \
    yasm \
    nasm \
    pkg-config \
    ca-certificates \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    && rm -rf /var/lib/apt/lists/* && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.11 /usr/bin/python

ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

WORKDIR /tmp/nv-codec-headers
RUN git clone --branch n12.1.14.0 https://git.videolan.org/git/ffmpeg/nv-codec-headers.git . && \
    make && \
    make install

RUN ln -sf /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1 && \
    echo "void nv_dummy() {}" > /tmp/nv_stub.c && \
    gcc -shared -o /usr/local/cuda/lib64/stubs/libnvcuvid.so /tmp/nv_stub.c && \
    ln -sf /usr/local/cuda/lib64/stubs/libnvcuvid.so /usr/local/cuda/lib64/stubs/libnvcuvid.so.1 && \
    ldconfig

WORKDIR /tmp/ffmpeg
RUN wget -q https://github.com/FFmpeg/FFmpeg/archive/refs/tags/n4.4.2.tar.gz && \
    tar -xf n4.4.2.tar.gz --strip-components=1

RUN LD_LIBRARY_PATH=/usr/local/cuda/lib64/stubs:$LD_LIBRARY_PATH \
    PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH \
    ./configure \
    --prefix=/usr/local \
    --enable-nonfree \
    --enable-cuda-nvcc \
    --enable-libnpp \
    --nvcc=nvcc \
    --enable-shared \
    --enable-gpl \
    --enable-cuvid \
    --enable-nvdec \
    --extra-cflags="-I/usr/local/cuda/include -I/usr/local/include" \
    --extra-ldflags="-L/usr/local/cuda/lib64/stubs -L/usr/local/cuda/lib64" \
    --nvccflags="-gencode arch=compute_75,code=sm_75 -O2" \
    --disable-static \
    --disable-doc \
    --disable-ffplay \
    --disable-ffprobe

RUN LD_LIBRARY_PATH=/usr/local/cuda/lib64/stubs:$LD_LIBRARY_PATH make -j$(nproc) && make install

WORKDIR /tmp/decord
RUN git clone --recursive https://github.com/dmlc/decord.git .

WORKDIR /tmp/decord/build
RUN cmake .. \
    -DUSE_CUDA=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/usr/local \
    && make -j$(nproc) \
    && make install

WORKDIR /tmp/decord/python
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install numpy && \
    python3 setup.py bdist_wheel

# =============================================================================
# MAIN RUNTIME STAGE - Optimized with all models cached
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
    libgomp1 \
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
# Layer 1.6: Copy Decord GPU libraries from builder
# -----------------------------------------------------------------------------
COPY --from=decord-builder /usr/local/lib/libavcodec.so* /usr/local/lib/
COPY --from=decord-builder /usr/local/lib/libavdevice.so* /usr/local/lib/
COPY --from=decord-builder /usr/local/lib/libavfilter.so* /usr/local/lib/
COPY --from=decord-builder /usr/local/lib/libavformat.so* /usr/local/lib/
COPY --from=decord-builder /usr/local/lib/libavutil.so* /usr/local/lib/
COPY --from=decord-builder /usr/local/lib/libswresample.so* /usr/local/lib/
COPY --from=decord-builder /usr/local/lib/libswscale.so* /usr/local/lib/
COPY --from=decord-builder /usr/local/lib/libpostproc.so* /usr/local/lib/
COPY --from=decord-builder /usr/local/lib/libdecord.so /usr/local/lib/

RUN ldconfig

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
# Layer 4.3: Install Decord GPU wheel from builder
# -----------------------------------------------------------------------------
COPY --from=decord-builder /tmp/decord/python/dist/*.whl /tmp/
RUN pip install --no-cache-dir numpy && \
    pip install --no-cache-dir /tmp/*.whl && \
    rm /tmp/*.whl

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
ENV LD_LIBRARY_PATH="/usr/local/lib:/usr/local/lib/python3.11/dist-packages/nvidia/cublas/lib:/usr/local/lib/python3.11/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.11/dist-packages/ctranslate2.libs:${LD_LIBRARY_PATH}"

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

RUN mkdir -p /app/output_data/transcoded_videos \
             /app/output_data/transcriptions \
             /app/output_data/embeddings \
             /app/output_data/scene_timestamps

EXPOSE 11434

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/app/run_preprocessor.sh"]
