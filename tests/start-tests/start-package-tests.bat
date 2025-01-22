@echo off
cd /d "%~dp0../.."
python -m pytest --cov="src" --cov-report xml:tests/start-tests/coverage.xml --cov-config=tests/start-tests/.coveragerc tests
