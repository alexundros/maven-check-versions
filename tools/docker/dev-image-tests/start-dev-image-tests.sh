#!/bin/bash
cd "$(dirname "$0")" || exit 1

test() {
  nm="tests-maven-check-versions_$(date +%Y-%m-%d_%H%M%S)"
  docker run "$1" --rm --name "$nm" maven-check-versions:dev "$2"
}

cn="maven_check_versions.cfg"

# test find artifact
fa="org.apache.maven.plugins:maven-compiler-plugin:3.8.1"
test "-v $(pwd)/data/$cn:/app/$cn:ro" "-fa $fa -ci -co"

# test process pom
test "-v $(pwd)/data/$cn:/app/$cn:ro" "-v $(pwd)/data/pom.xml:/app/pom.xml" "-ci -co"
