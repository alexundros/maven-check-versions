@echo off
cd /d "%~dp0../.."
if "%SONAR_LOGIN%"=="" set SONAR_LOGIN=admin
if "%SONAR_PASSWORD%"=="" set SONAR_PASSWORD=sonar
if "%SONAR_HOST_URL%"=="" set SONAR_HOST_URL=http://host.docker.internal:9000
docker run --rm -v "%cd%:/usr/src" -e SONAR_HOST_URL="%SONAR_HOST_URL%" ^
 --name sonar-scanner-maven_check_versions sonarsource/sonar-scanner-cli ^
 -Dsonar.login="%SONAR_LOGIN%" -Dsonar.password="%SONAR_PASSWORD%" ^
 -Dsonar.sourceEncoding=UTF-8 -Dsonar.projectBaseDir=src -Dsonar.inclusions=**/*.py ^
 -Dsonar.exclusions=**/__main__.py -Dsonar.python.coverage.reportPaths=tests/start-tests/coverage.xml ^
 -Dsonar.projectKey=maven_check_versions -Dsonar.projectName="Maven Check Versions"
