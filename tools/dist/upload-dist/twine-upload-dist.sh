#!/bin/bash
cd "$(dirname "$0")/../.." || exit 1
[ -z "$PYPY_TOKEN" ] && echo "PYPY_TOKEN ERROR" && exit 1
python -m twine upload dist/* --username __token__ --password "$PYPY_TOKEN"
