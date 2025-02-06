#!/bin/bash
cd "$(dirname "$0")/../.." || exit 1
docker build --progress=plain --tag maven-check-versions:dev .
nm="maven-check-versions_$(date +%Y-%m-%d_%H%M%S)"
docker run --rm --name "$nm" maven-check-versions:dev -ci 1
