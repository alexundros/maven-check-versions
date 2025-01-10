#!/bin/bash
cd "$(dirname "$0")/../.."
python -m pytest --cov=src/maven_check_versions "tests" --cov-report xml:tests/coverage.xml
