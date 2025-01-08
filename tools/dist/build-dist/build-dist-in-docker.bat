@echo off
set nm=build_maven_check_versions
docker buildx build --tag %nm% -f "%~dp0Dockerfile" "%~dp0..\..\.."
docker run --name %nm% -d %nm%:latest
docker cp %nm%:/build/dist "%~dp0..\..\.." & docker rm -f %nm%