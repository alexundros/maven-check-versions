#!/bin/bash
cd "$(dirname "$0")/../.."
docker build --progress=plain --tag maven_check_versions .
docker run --name maven_check_versions -d maven_check_versions:latest
