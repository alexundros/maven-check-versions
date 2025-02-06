#!/bin/bash
cd "$(dirname "$0")/../.." || exit 1
dir="tools/start-tests"
python -m pytest --cov="src" --cov-report xml:${dir}/coverage.xml --cov-config=${dir}/.coveragerc tests
