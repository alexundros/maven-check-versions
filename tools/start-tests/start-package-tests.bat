@echo off
cd /d "%~dp0../.." || exit 1
python -m pytest --cov="src" --cov-report xml:tests/coverage.xml --cov-config=tests/.coveragerc tests
