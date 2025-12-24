#!/bin/bash
set -e

export LD_LIBRARY_PATH="/usr/local/nvidia/lib:/usr/local/lib:${LD_LIBRARY_PATH}"

MARKER_FILE="/models/.models_initialized"

log() {
    echo "[ENTRYPOINT] [$(date '+%Y-%m-%d %H:%M:%S')] $1" >&2
}

setup_ml_models() {
    if [ -f "$MARKER_FILE" ]; then
        log "✓ ML models already initialized (marker exists)"
        return 0
    fi

    log "Checking/downloading ML models..."

    if [ -f "/app/download_models.py" ]; then
        python /app/download_models.py
        date > "$MARKER_FILE"
        log "✓ ML models initialized"
    else
        log "⚠ download_models.py not found, skipping ML model setup"
    fi
}

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
    log "Skipping ML model checks (GPU reserved for scene detection)"
fi

log "============================================"
log "Initialization complete!"
log "============================================"

exec /app/run_preprocessor.sh "$@"
