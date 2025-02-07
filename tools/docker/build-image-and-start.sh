#!/bin/bash
cd "$(dirname "$0")/../.." || exit 1
bash ./build-dev-image.sh
nm="maven-check-versions_$(date +%Y-%m-%d_%H%M%S)"
docker run --rm --name "$nm" maven-check-versions:dev -ci
