#!/bin/bash
cd "$(dirname "$0")/../.." || exit 1
docker rmi maven-check-versions:dev
docker rmi maven-check-versions:dev_pypy
docker build --tag maven-check-versions:dev .
docker build --tag maven-check-versions:dev_pypy -f pypy.Dockerfile .
