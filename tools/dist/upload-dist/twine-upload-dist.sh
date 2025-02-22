#!/bin/bash
cd "$(dirname "$0")/../.." || exit 1
[ -z "$PYPI_TOKEN" ] && echo "PYPI_TOKEN ERROR" && exit 1
python -m twine upload dist/* -u __token__ -p "$PYPI_TOKEN"
