#!/bin/bash

cd "$(dirname "$0")"

if [ "$1" = "bash" ] || [ "$1" = "sh" ]; then
    docker compose -f docker-compose.yml run --rm --remove-orphans --entrypoint "$1" preprocessor
else
    docker compose -f docker-compose.yml run --rm --remove-orphans preprocessor "$@"
fi
