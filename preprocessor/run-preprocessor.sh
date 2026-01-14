#!/bin/bash

cd "$(dirname "$0")"

docker compose -f docker-compose.yml run --rm --remove-orphans preprocessor "$@"
