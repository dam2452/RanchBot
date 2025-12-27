#!/bin/bash
set -e

export LD_LIBRARY_PATH="/usr/local/nvidia/lib:/usr/local/lib:${LD_LIBRARY_PATH}"

log() {
    echo "[ENTRYPOINT] [$(date '+%Y-%m-%d %H:%M:%S')] $1" >&2
}

log "============================================"
log "Initialization complete!"
log "============================================"

exec /app/run_preprocessor.sh "$@"
