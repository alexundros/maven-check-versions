@echo off
cd /d "%~dp0..\..\.."
if "%PYPY_TOKEN%"=="" echo PYPY_TOKEN ERROR & exit /b 1
python -m twine upload dist/* --username __token__ --password "%PYPY_TOKEN%"
