@echo off
@chcp 1251 > nul
@setlocal enabledelayedexpansion
cd /d "%~dp0" || exit 1
goto :start

:test
  set nm="tests-maven-check-versions %date% %time:~0,8%"
  (set nm=!nm: =_!) & (set nm=!nm:.=!) & (set nm=!nm::=!)
  docker run %~1 --rm --name %nm% maven-check-versions:dev %~2
  docker run %~1 --rm --name "%nm%_pypy" maven-check-versions:dev_pypy %~2
exit /b

:start
set cn=maven_check_versions.yml

:: test find artifact
set fa=org.apache.maven.plugins:maven-compiler-plugin:3.8.1
call :test "-v "%cd%\data\%cn%:/app/%cn%:ro"" "-fa %fa% -ci -co"

:: test process pom
call :test "-v "%cd%\data\%cn%:/app/%cn%:ro" -v "%cd%\data\pom.xml:/app/pom.xml"" "-ci -co"
