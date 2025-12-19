#!/bin/bash
set -e

# =============================================================================
# UNIFIED ENTRYPOINT - Handles Ollama + ML models with intelligent caching
# =============================================================================

MARKER_FILE="/app/.cache/.models_initialized"
OLLAMA_MARKER="/root/.ollama/.ollama_models_ready"

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

wait_for_ollama() {
    log "Waiting for Ollama to be ready..."
    local max_attempts=30
    local attempt=0
    while ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            log "ERROR: Ollama failed to start after ${max_attempts} attempts"
            return 1
        fi
        sleep 1
    done
    log "Ollama is ready!"
}

# -----------------------------------------------------------------------------
# Setup NVENC (create symlinks for CUDA libraries if needed)
# -----------------------------------------------------------------------------
setup_nvenc() {
    # Prefer WSL drivers (real GPU driver), fallback to CUDA compat libs
    CUDA_LIB=""

    # Try WSL drivers first (version 1.1)
    CUDA_LIB=$(ls /usr/lib/wsl/drivers/*/libcuda.so.1.1 2>/dev/null | head -1)

    # Fallback to version 1
    if [ -z "$CUDA_LIB" ]; then
        CUDA_LIB=$(ls /usr/lib/wsl/drivers/*/libcuda.so.1 2>/dev/null | head -1)
    fi

    # Last resort: find anywhere (will get compat lib)
    if [ -z "$CUDA_LIB" ]; then
        CUDA_LIB=$(find /usr -name "libcuda.so.1*" 2>/dev/null | grep -v "compat" | head -1)
    fi

    # If still nothing, use compat
    if [ -z "$CUDA_LIB" ]; then
        CUDA_LIB=$(find /usr -name "libcuda.so.1*" 2>/dev/null | head -1)
    fi

    if [ -n "$CUDA_LIB" ]; then
        log "Setting up NVENC support with: $CUDA_LIB"
        # Always recreate symlink (force overwrite)
        rm -f /usr/lib/x86_64-linux-gnu/libcuda.so.1
        ln -sf "$CUDA_LIB" /usr/lib/x86_64-linux-gnu/libcuda.so.1
        # Verify symlink
        ACTUAL_TARGET=$(readlink -f /usr/lib/x86_64-linux-gnu/libcuda.so.1)
        log "✓ NVENC configured -> $ACTUAL_TARGET"
    else
        log "⚠ CUDA library not found, NVENC may not work"
    fi
}

setup_nvenc

# -----------------------------------------------------------------------------
# Start Ollama service
# -----------------------------------------------------------------------------
log "Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!

wait_for_ollama

# -----------------------------------------------------------------------------
# Download Ollama models (only if not cached)
# -----------------------------------------------------------------------------
setup_ollama_models() {
    local MODEL_NAME="qwen3-coder:30b-a3b-q4_K_M"
    local CUSTOM_MODEL="qwen3-coder-50k"

    # Check if custom model already exists
    if ollama list 2>/dev/null | grep -q "$CUSTOM_MODEL"; then
        log "✓ Ollama model '$CUSTOM_MODEL' already cached"
        return 0
    fi

    log "⬇ Downloading Ollama model: $MODEL_NAME"
    if ! ollama pull "$MODEL_NAME"; then
        log "⚠ Failed to pull $MODEL_NAME, will retry on first use"
        return 1
    fi

    log "Creating custom model with 50k context..."
    cat > /tmp/Modelfile-qwen3-50k <<EOF
FROM ${MODEL_NAME}
PARAMETER num_ctx 50000
EOF

    if ollama create "$CUSTOM_MODEL" -f /tmp/Modelfile-qwen3-50k; then
        log "✓ Custom model '$CUSTOM_MODEL' created"
    else
        log "⚠ Custom model creation failed"
    fi

    rm -f /tmp/Modelfile-qwen3-50k
}

# Only setup if PULL_EXTRA_MODELS is not explicitly false
if [ "${PULL_EXTRA_MODELS}" != "false" ]; then
    setup_ollama_models
else
    log "Skipping Ollama model pull (PULL_EXTRA_MODELS=false)"
fi

# -----------------------------------------------------------------------------
# Download ML models (HuggingFace, Whisper, TransNet) - only if not cached
# -----------------------------------------------------------------------------
setup_ml_models() {
    if [ -f "$MARKER_FILE" ]; then
        log "✓ ML models already initialized (marker exists)"
        return 0
    fi

    log "Checking/downloading ML models..."

    if [ -f "/app/download_models.py" ]; then
        python /app/download_models.py

        # Create marker
        mkdir -p "$(dirname "$MARKER_FILE")"
        date > "$MARKER_FILE"
        log "✓ ML models initialized"
    else
        log "⚠ download_models.py not found, skipping ML model setup"
    fi
}

setup_ml_models

# -----------------------------------------------------------------------------
# Status report
# -----------------------------------------------------------------------------
log "============================================"
log "Initialization complete!"
log "Ollama running on: http://localhost:11434"
log "Available Ollama models:"
ollama list 2>/dev/null || echo "  (none yet)"
log "============================================"

# -----------------------------------------------------------------------------
# Execute main command
# -----------------------------------------------------------------------------
exec "$@"