@echo off
@setlocal enabledelayedexpansion
cd /d "%~dp0../.." || exit 1
docker build --progress=plain --tag maven-check-versions:dev .
set nm="maven-check-versions %date% %time:~0,8%"
(set nm=!nm: =_!) & (set nm=!nm:.=!) & (set nm=!nm::=!)
docker run --name %nm% maven-check-versions:dev
