@echo off
cd /d "%~dp0../.."
python -m pytest --cov=src "tests" --cov-report xml:tests/coverage.xml
