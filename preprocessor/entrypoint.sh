#!/bin/bash
set -e

echo "Ensuring output directories exist..."
mkdir -p /app/output_data/transcoded_videos
mkdir -p /app/output_data/transcriptions
mkdir -p /app/output_data/embeddings
mkdir -p /app/output_data/scene_timestamps

echo "Starting application..."
exec python -m preprocessor.cli "$@"
