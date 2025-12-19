#!/bin/bash
set -e

if [ "$#" -eq 0 ]; then
    echo "Usage: docker-compose run preprocessor <command> [args...]"
    echo ""
    echo "Available commands:"
    python -m preprocessor --help
    exit 0
fi

exec python -m preprocessor "$@"
