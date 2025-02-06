@echo off
cd /d "%~dp0../.." || exit 1
set dir=tools/start-tests
python -m pytest --cov="src" --cov-report xml:%dir%/coverage.xml --cov-config=%dir%/.coveragerc tests
