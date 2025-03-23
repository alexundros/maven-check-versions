@echo off
cd /d "%~dp0../.." || exit 1
python -m pytest --cov="src" --cov-config=tests/.coveragerc --cov-report xml:tests/coverage.xml ^
--cov-report html:tests/coverage --cov-report term-missing tests
