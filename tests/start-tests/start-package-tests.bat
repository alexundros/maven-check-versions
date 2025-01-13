@echo off
cd /d "%~dp0../.."
python -m pytest --cov="src" --cov-report xml:tests/coverage.xml tests
