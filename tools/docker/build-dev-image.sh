#!/bin/bash
cd "$(dirname "$0")/../.." || exit 1
docker rmi maven-check-versions:dev
docker build --progress=plain --tag maven-check-versions:dev .
