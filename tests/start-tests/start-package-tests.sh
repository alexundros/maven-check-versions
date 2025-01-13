#!/bin/bash
cd "$(dirname "$0")/../.."
python -m pytest --cov="src" --cov-report xml:tests/coverage.xml tests
