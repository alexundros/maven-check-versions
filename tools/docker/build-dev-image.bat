@echo off
@chcp 1251 > nul
cd /d "%~dp0../.." || exit 1
docker rmi maven-check-versions:dev
docker rmi maven-check-versions:dev_pypy
docker build --tag maven-check-versions:dev .
docker build --tag maven-check-versions:dev_pypy -f pypy.Dockerfile .
