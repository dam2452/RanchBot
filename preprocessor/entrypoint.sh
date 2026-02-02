#!/bin/bash
set -e

echo "Ensuring global output directories exist..."
mkdir -p /app/output_data/characters
mkdir -p /app/output_data/scraped_pages
mkdir -p /app/output_data/processing_metadata

echo "Starting application..."
exec python -m preprocessor.cli "$@"
