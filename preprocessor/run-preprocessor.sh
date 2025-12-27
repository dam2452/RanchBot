#!/bin/bash

cd "$(dirname "$0")"

docker-compose -f preprocessor/docker-compose.yml run --rm preprocessor "$@"
