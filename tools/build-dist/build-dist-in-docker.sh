#!/bin/bash
nm=build_maven_check_versions
dir="$(dirname "$0")"
docker buildx build --tag $nm -f "$dir/Dockerfile" "$dir/../.."
docker run --name "$nm" -d $nm:latest
docker cp "$nm:/build/dist" "$dir/../.." & docker rm -f $nm