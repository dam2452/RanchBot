#!/bin/bash
set -e

echo "Starting application..."
exec python -m preprocessor.cli "$@"
