#!/bin/bash
cd "$(dirname "$0")/../.."
python -m pytest --cov=src "tests" --cov-report xml:tests/coverage.xml
