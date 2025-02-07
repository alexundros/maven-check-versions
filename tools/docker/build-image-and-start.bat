@echo off
@chcp 1251 > nul
@setlocal enabledelayedexpansion
call %~dp0build-dev-image.bat
set nm="maven-check-versions %date% %time:~0,8%"
(set nm=!nm: =_!) & (set nm=!nm:.=!) & (set nm=!nm::=!)
docker run --rm --name %nm% maven-check-versions:dev -ci
