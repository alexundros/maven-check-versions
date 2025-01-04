@echo off
cd /d "%~dp0.."
docker run --rm -v "%cd%:/usr/src" ^
 -e SONAR_HOST_URL=%SONAR_HOST_URL:http://host.docker.internal:9000% ^
 --name sonar-scanner-maven_check_versions sonarsource/sonar-scanner-cli ^
 -Dsonar.login=%SONAR_LOGIN:admin% ^
 -Dsonar.password=%SONAR_PASSWORD:sonar% ^
 -Dsonar.sourceEncoding=UTF-8 ^
 -Dsonar.projectBaseDir=. -Dsonar.inclusions=**/*.py ^
 -Dsonar.projectKey=maven_check_versions ^
 -Dsonar.projectName="Maven Check Versions"
