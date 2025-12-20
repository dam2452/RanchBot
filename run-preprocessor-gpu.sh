#!/bin/bash

cd "$(dirname "$0")"

docker run --rm \
    --gpus all \
    --runtime=nvidia \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -e NVIDIA_DRIVER_CAPABILITIES=all \
    -e CUDA_VISIBLE_DEVICES=0 \
    -e PULL_EXTRA_MODELS=true \
    -e DOCKER_CONTAINER=true \
    -e PYTHONUNBUFFERED=1 \
    -e HF_HOME=/models/huggingface \
    -e TRANSFORMERS_CACHE=/models/huggingface \
    -e TORCH_HOME=/models/torch \
    -e WHISPER_CACHE=/models/whisper \
    -e OLLAMA_MODELS=/models/ollama \
    -e OLLAMA_MAX_LOADED_MODELS=1 \
    -e OLLAMA_HOST=0.0.0.0 \
    --env-file preprocessor/.env \
    -v "$(pwd)/preprocessor/input_data:/input_data:ro" \
    -v "$(pwd)/preprocessor/output_data:/app/output_data" \
    -v ranchbot-ai-models:/models \
    -p 11434:11434 \
    ranczo-preprocessor:latest \
    "$@"
