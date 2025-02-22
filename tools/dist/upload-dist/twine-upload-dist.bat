@echo off
cd /d "%~dp0..\..\.." || exit 1
if "%PYPI_TOKEN%"=="" echo PYPI_TOKEN ERROR & exit /b 1
python -m twine upload dist/* -u __token__ -p "%PYPI_TOKEN%"
