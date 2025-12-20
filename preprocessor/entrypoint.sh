#!/bin/bash
set -e

# =============================================================================
# UNIFIED ENTRYPOINT - Handles Ollama + ML models with intelligent caching
# =============================================================================

MARKER_FILE="/models/.models_initialized"
OLLAMA_MARKER="/root/.ollama/.ollama_models_ready"

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
log() {
    echo "[ENTRYPOINT] [$(date '+%Y-%m-%d %H:%M:%S')] $1" >&2
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
# Determine if Ollama is needed
# -----------------------------------------------------------------------------
NEEDS_OLLAMA=false
for arg in "$@"; do
    if [[ "$arg" == "scrape-episodes" ]] || [[ "$arg" == "--scrape-urls" ]]; then
        NEEDS_OLLAMA=true
        break
    fi
done

# -----------------------------------------------------------------------------
# Start Ollama service (only if needed)
# -----------------------------------------------------------------------------
if [ "$NEEDS_OLLAMA" = true ]; then
    log "Starting Ollama service..."
    ollama serve &
    OLLAMA_PID=$!
    wait_for_ollama
else
    log "Skipping Ollama (not needed for this command)"
    OLLAMA_PID=""
fi

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

    log "Creating custom model with 50k context (GPU-only)..."
    cat > /tmp/Modelfile-qwen3-50k <<EOF
FROM ${MODEL_NAME}
PARAMETER num_ctx 50000
PARAMETER num_gpu 999
EOF

    if ollama create "$CUSTOM_MODEL" -f /tmp/Modelfile-qwen3-50k; then
        log "✓ Custom model '$CUSTOM_MODEL' created"
    else
        log "⚠ Custom model creation failed"
    fi

    rm -f /tmp/Modelfile-qwen3-50k
}

# Only setup if PULL_EXTRA_MODELS is not explicitly false AND Ollama is needed
if [ "$NEEDS_OLLAMA" = true ] && [ "${PULL_EXTRA_MODELS}" != "false" ]; then
    setup_ollama_models
else
    if [ "$NEEDS_OLLAMA" = false ]; then
        log "Skipping Ollama model pull (not needed for this command)"
    else
        log "Skipping Ollama model pull (PULL_EXTRA_MODELS=false)"
    fi
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

        # Create marker in persistent volume
        date > "$MARKER_FILE"
        log "✓ ML models initialized"
    else
        log "⚠ download_models.py not found, skipping ML model setup"
    fi
}

# Skip ML model setup for commands that don't need it (avoid GPU conflicts)
SKIP_ML_SETUP=false
for arg in "$@"; do
    if [[ "$arg" == "detect-scenes" ]]; then
        SKIP_ML_SETUP=true
        break
    fi
done

if [ "$SKIP_ML_SETUP" = false ]; then
    setup_ml_models
else
    log "Skipping ALL ML model checks (GPU reserved for scene detection)"
fi

# -----------------------------------------------------------------------------
# Status report
# -----------------------------------------------------------------------------
log "============================================"
log "Initialization complete!"
if [ "$NEEDS_OLLAMA" = true ]; then
    log "Ollama running on: http://localhost:11434"
    log "Available Ollama models:"
    ollama list 2>/dev/null || echo "  (none yet)"
else
    log "Ollama: NOT RUNNING (GPU available for other tasks)"
fi
log "============================================"

# -----------------------------------------------------------------------------
# Execute main command
# -----------------------------------------------------------------------------
exec /app/run_preprocessor.sh "$@"