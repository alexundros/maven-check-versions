<p>
  <img alt="Sonar Coverage" src="https://img.shields.io/sonar/coverage/alexundros_maven-check-versions?server=https%3A%2F%2Fsonarcloud.io"> 
  <img alt="Sonar Quality Gate" src="https://img.shields.io/sonar/quality_gate/alexundros_maven-check-versions?server=https%3A%2F%2Fsonarcloud.io">
  <img alt="Sonar Tech Debt" src="https://img.shields.io/sonar/tech_debt/alexundros_maven-check-versions?server=https%3A%2F%2Fsonarcloud.io">
  <img alt="Sonar Violations" src="https://img.shields.io/sonar/violations/alexundros_maven-check-versions?server=https%3A%2F%2Fsonarcloud.io">
  <!-- Sonar Violations Details:
  <img alt="Blocker Violations" src="https://img.shields.io/sonar/blocker_violations/alexundros_maven-check-versions?server=https%3A%2F%2Fsonarcloud.io">
  <img alt="Critical Violations" src="https://img.shields.io/sonar/critical_violations/alexundros_maven-check-versions?server=https%3A%2F%2Fsonarcloud.io">
  <img alt="Major Violations" src="https://img.shields.io/sonar/major_violations/alexundros_maven-check-versions?server=https%3A%2F%2Fsonarcloud.io">
  <img alt="Minor Violations" src="https://img.shields.io/sonar/minor_violations/alexundros_maven-check-versions?server=https%3A%2F%2Fsonarcloud.io">
  <img alt="Info Violations" src="https://img.shields.io/sonar/info_violations/alexundros_maven-check-versions?server=https%3A%2F%2Fsonarcloud.io">
  -->
</p>

---

# Maven Check Versions

This is a Python package designed for analyzing Maven POM files and managing dependencies.
It checks the versions of dependencies in a project and identifies the latest available versions in Maven repositories.
Developed for developers, this package simplifies dependency management in Maven-based projects.
It is especially useful in CI/CD environments, where maintaining consistency and up-to-date dependencies is critical.

See https://pypi.org/project/maven-check-versions for more details.

---

## Features

- **Dependency Analysis:** Parses Maven POM files to analyze dependencies and plugins.
- **Version Checking:** Identifies outdated dependencies and checks versions against customizable thresholds.
- **Artifact Search:** Finds specific artifacts using `groupId:artifactId:version` format.
- **Repository Support:** Integrates with HTTP-based Maven repositories, including REST services.
- **Module Processing:** Processes nested modules in Maven projects.
- **Caching:** Caches results for faster rechecks with multiple cache backends.
- **Logging:** Provides configurable logging for detailed analysis.
- **Command-Line Interface:** Easily integrates into CI/CD pipelines.
- **Vulnerability Checking:** Checks dependencies for known vulnerabilities using OSS Index.

---

## Installation

System requirements: Python 3.10 or higher

You can install the tool via pip: `pip install maven_check_versions`

---

## Usage

- Analyze a specific pom file:

```bash
maven_check_versions --pom_file path/to/pom.xml
```

- Search for a specific artifact:

```bash
maven_check_versions --find_artifact com.example:my-lib:1.0
```

- Enable CI mode to suppress prompts:

```bash
maven_check_versions --ci_mode
```

### Docker images

#### Pull images from GitHub:

Base image: `docker pull ghcr.io/alexundros/maven-check-versions`

Image based on pypy: `docker pull ghcr.io/alexundros/maven-check-versions:pypy`

#### Pull images from DockerHub:

Base image: `docker pull alexundros/maven-check-versions`

Image based on pypy: `docker pull alexundros/maven-check-versions:pypy`

#### Usage

- Analyze a specific pom file:

```bash
docker run --rm -v 'path/to/pom.xml:/app/pom.xml' alexundros/maven_check_versions -pf /app/pom.xml
```

- Search for a specific artifact:

```bash
docker run --rm alexundros/maven_check_versions -fa com.example:my-lib:1.0
```

- Enable CI mode to suppress prompts:

```bash
docker run --rm alexundros/maven_check_versions -ci
```

---

## Command-Line Arguments

### General Options

| Parameter         | Short  | Description                                                                                    | Example                               |
|-------------------|--------|------------------------------------------------------------------------------------------------|---------------------------------------|
| `--ci_mode`       | `-ci`  | Enables CI (Continuous Integration) mode. Suppresses prompts and waits for user input.         | `--ci_mode`                           |
| `--pom_file`      | `-pf`  | Specifies the path to the Maven POM file to process.                                           | `--pom_file path/to/pom.xml`          |
| `--find_artifact` | `-fa`  | Searches for a specific artifact. Provide the artifact in `groupId:artifactId:version` format. | `--find_artifact com.example:lib:1.0` |
| `--config_file`   | `-cfg` | Specifies a custom configuration file for the script.                                          | `--config_file config.yml`            |
| `--log_level`     | `-ll`  | Specifies log level.                                                                           | `--log_level debug`                   |

### Cache Control

| Parameter         | Short | Description                                                             | Example                   |
|-------------------|-------|-------------------------------------------------------------------------|---------------------------|
| `--cache_off`     | `-co` | Disables caching to force fresh dependency checks.                      | `--cache_off`             |
| `--cache_file`    | `-cf` | Specifies a custom path for the cache file (only for JSON backend).     | `--cache_file cache.json` |
| `--cache_time`    | `-ct` | Specifies the cache expiration time in seconds.                         | `--cache_time 1800`       |
| `--cache_backend` | `-cb` | Specifies the cache backend to use (json, redis, tarantool, memcached). | `--cache_backend redis`   |

Depending on the selected cache backend, additional command-line arguments may be required:

#### Redis Cache Backend

| Parameter          | Short   | Description                                      | Example                 |
|--------------------|---------|--------------------------------------------------|-------------------------|
| `--redis_host`     | `-rsh`  | Redis host (default: localhost).                 | `--redis_host redis`    |
| `--redis_port`     | `-rsp`  | Redis port (default: 6379).                      | `--redis_port 6379`     |
| `--redis_key`      | `-rsk`  | Redis key (default: maven_check_versions_cache). | `--redis_key mycache`   |
| `--redis_user`     | `-rsu`  | Redis username (optional).                       | `--redis_user user`     |
| `--redis_password` | `-rsup` | Redis password (optional).                       | `--redis_password pass` |

#### Tarantool Cache Backend

| Parameter              | Short   | Description                                            | Example                      |
|------------------------|---------|--------------------------------------------------------|------------------------------|
| `--tarantool_host`     | `-tlh`  | Tarantool host (default: localhost).                   | `--tarantool_host tarantool` |
| `--tarantool_port`     | `-tlp`  | Tarantool port (default: 3301).                        | `--tarantool_port 3301`      |
| `--tarantool_space`    | `-tls`  | Tarantool space (default: maven_check_versions_cache). | `--tarantool_space myspace`  |
| `--tarantool_user`     | `-tlu`  | Tarantool username (optional).                         | `--tarantool_user user`      |
| `--tarantool_password` | `-tlup` | Tarantool password (optional).                         | `--tarantool_password pass`  |

#### Memcached Cache Backend

| Parameter          | Short  | Description                                          | Example                      |
|--------------------|--------|------------------------------------------------------|------------------------------|
| `--memcached_host` | `-mch` | Memcached host (default: localhost).                 | `--memcached_host memcached` |
| `--memcached_port` | `-mcp` | Memcached port (default: 11211).                     | `--memcached_port 11211`     |
| `--memcached_key`  | `-mck` | Memcached key (default: maven_check_versions_cache). | `--memcached_key mycache`    |

### Logging Options

| Parameter       | Short  | Description                                                          | Example                 |
|-----------------|--------|----------------------------------------------------------------------|-------------------------|
| `--logfile_off` | `-lfo` | Disables logging to a file. Logs will only be shown in the terminal. | `--logfile_off`         |
| `--log_file`    | `-lf`  | Specifies the path to a custom log file.                             | `--log_file my_log.log` |

### Error Handling and Validation

| Parameter      | Short  | Description                                                                                        | Example          |
|----------------|--------|----------------------------------------------------------------------------------------------------|------------------|
| `--fail_mode`  | `-fm`  | Enables "fail mode." The script will terminate if dependency versions exceed specified thresholds. | `--fail_mode`    |
| `--fail_major` | `-mjv` | Specifies the major version difference threshold for failure.                                      | `--fail_major 1` |
| `--fail_minor` | `-mnv` | Specifies the minor version difference threshold for failure.                                      | `--fail_minor 2` |

### Dependency Search and Processing

| Parameter           | Short | Description                                                    | Example             |
|---------------------|-------|----------------------------------------------------------------|---------------------|
| `--search_plugins`  | `-sp` | Includes Maven plugins in the dependency search process.       | `--search_plugins`  |
| `--process_modules` | `-sm` | Processes modules listed in the POM file.                      | `--process_modules` |
| `--show_skip`       | `-sk` | Logs dependencies that are skipped.                            | `--show_skip`       |
| `--show_search`     | `-ss` | Logs information about search actions.                         | `--show_search`     |
| `--empty_version`   | `-ev` | Allows processing of dependencies without a version specified. | `--empty_version`   |
| `--show_invalid`    | `-si` | Logs information about invalid dependencies.                   | `--show_invalid`    |

### Performance Options

| Parameter       | Short | Description                                                               | Example           |
|-----------------|-------|---------------------------------------------------------------------------|-------------------|
| `--threading`   | `-th` | Enables multi-threading to process dependencies and modules concurrently. | `--threading`     |
| `--max_threads` | `-mt` | Specifies the maximum number of threads to use when threading is enabled. | `--max_threads 8` |

### Authentication

| Parameter    | Short | Description                                                                | Example                  |
|--------------|-------|----------------------------------------------------------------------------|--------------------------|
| `--user`     | `-un` | Specifies a username for basic authentication when accessing repositories. | `--user my_username`     |
| `--password` | `-up` | Specifies a password for basic authentication when accessing repositories. | `--password my_password` |

---

## Configuration

You can customize the tool’s behavior using a configuration file `maven_check_versions.yml`.
The following settings can be adjusted:

- **SSL Verification:** Enable or disable SSL verification for HTTP requests.
- **Cache Preferences:** Control cache duration and behavior.
- **Repository Settings:** Define base URLs, authentication, and paths for repositories.
- **Logging Preferences:** Specify log levels and file paths.
- **Vulnerability Checking:** Configure checks for known vulnerabilities in dependencies.

### Cache Configuration

The tool supports multiple cache backends:

- **JSON** (default): Stores cache data in a local JSON file specified by `cache_file`.
- **Redis**: Uses a Redis server for caching.
- **Tarantool**: Uses a Tarantool server for caching.
- **Memcached**: Uses a Memcached server for caching.

### Vulnerability Checking Configuration

To enable vulnerability checking, set `oss_index_enabled` to `true` in the `vulnerability` section of the configuration
file.
This feature uses the OSS Index service to identify known vulnerabilities in your dependencies.
You will need to provide your OSS Index username and API token, which you can obtain by signing up for a free account at
[https://ossindex.sonatype.org/](https://ossindex.sonatype.org/).

Example configuration:

Vulnerability scanning will:

1. Check all dependencies against OSS Index
2. Fail build if any vulnerability with CVSS ≥7.0 found
3. Skip checks for test components

```yaml
vulnerability:
  oss_index_enabled: true
  oss_index_url: "https://ossindex.sonatype.org/api/v3/component-report"
  oss_index_user: "OSS_INDEX_USER"
  oss_index_token: "OSS_INDEX_TOKEN"
  oss_index_batch_size: 128
  oss_index_keep_safe: false
  fail_score: 7
  skip_no_versions: false
  skip_checks: [ "junit:junit:*" ]
  cache_backend: "json"
```

### Configuration file

maven_check_versions.yml:

```
base:
  cache_off: false        # Disables caching of version check results
  cache_time: 600         # Cache expiration time in seconds (0 to disable expiration)
  cache_backend: "json"   # Cache backend to use: json, redis, tarantool, memcached

  # Redis cache backend settings
  redis_host: "localhost"                           # Redis host
  redis_port: 6379                                  # Redis port
  redis_key: "maven_check_versions_artifacts"       # Key for storing data in Redis
  redis_user: null                                  # Redis username (optional)
  redis_password: null                              # Redis password (optional)

  # Tarantool cache backend settings
  tarantool_host: "localhost"                       # Tarantool host
  tarantool_port: 3301                              # Tarantool port
  tarantool_space: "maven_check_versions_artifacts" # Tarantool space
  tarantool_user: null                              # Tarantool username (optional)
  tarantool_password: null                          # Tarantool password (optional)

  # Memcached cache backend settings
  memcached_host: "localhost"                       # Memcached host
  memcached_port: 11211                             # Memcached port
  memcached_key: "maven_check_versions_artifacts"   # Key for storing data in Memcached

  fail_mode: false        # Enables fail mode, terminating the script if version thresholds are exceeded
  fail_major: 0           # Major version difference threshold for failure
  fail_minor: 0           # Minor version difference threshold for failure

  search_plugins: false   # Includes Maven plugins in the dependency search process
  process_modules: false  # Processes modules listed in the POM file

  show_skip: false        # Logs dependencies that are skipped during processing
  show_search: false      # Logs information about search actions for dependencies

  empty_version: false    # Allows processing of dependencies without a specified version
  show_invalid: false     # Logs information about invalid dependencies
  skip_version: true      # Skips version checks for dependencies matching the current version

  threading: false        # Enables multi-threading for concurrent processing
  max_threads: 8          # Maximum number of threads to use when threading is enabled

  user: "USER"            # Username for basic authentication in repositories
  password: "PASSWORD"    # Password for basic authentication in repositories

# Configuration for vulnerability checks
vulnerability:
  oss_index_enabled: true                           # Enables OSS Index vulnerability checks
  oss_index_url: "https://ossindex.sonatype.org/api/v3/component-report"  # OSS Index API URL
  oss_index_user: "OSS_INDEX_USER"                  # OSS Index username
  oss_index_token: "OSS_INDEX_TOKEN"                # OSS Index API token
  oss_index_batch_size: 128                         # Batch size for OSS Index requests
  oss_index_keep_safe: false                        # Keeps safe dependencies in the cache

  fail_score: 0                                     # Fail if CVSS score exceeds this value
  cve_reference: false                              # Logs link for detailed information
  skip_no_versions: false                           # Skips dependencies without versions in vulnerability checks
  skip_checks: []                                   # List of dependencies to skip in vulnerability checks
                                                    # (e.g., ["group:artifact:version"])

  cache_backend: "json"                             # Cache backend to use: json, redis, tarantool, memcached

  # Redis cache backend settings for the vulnerability
  redis_host: "localhost"                                 # Redis host
  redis_port: 6379                                        # Redis port
  redis_key: "maven_check_versions_vulnerabilities"       # Key for storing data in Redis
  redis_user: null                                        # Redis username (optional)
  redis_password: null                                    # Redis password (optional)

  # Tarantool cache backend settings for the vulnerability
  tarantool_host: "localhost"                             # Tarantool host
  tarantool_port: 3301                                    # Tarantool port
  tarantool_space: "maven_check_versions_vulnerabilities" # Tarantool space
  tarantool_user: null                                    # Tarantool username (optional)
  tarantool_password: null                                # Tarantool password (optional)

  # Memcached cache backend settings for the vulnerability
  memcached_host: "localhost"                             # Memcached host
  memcached_port: 11211                                   # Memcached port
  memcached_key: "maven_check_versions_vulnerabilities"   # Key for storing data in Memcached

# Configuration for HTTP-based POM file access
pom_http:
  auth: true                                  # Enables authentication for HTTP-based POM file access

# Configuration for urllib3 library
urllib3:
  warnings: true                              # Enables or disables urllib3 warnings

# Configuration for requests library
requests:
  verify: true                                # Enables or disables SSL verification for requests

# List of POM files to process
pom_files:
  pom-name: "path/to/pom.xml"                 # Path to a POM file to process

# Repository configurations
repositories:
  "Central (repo1.maven.org)": "repo1_maven"  # Example repository mapping

# Configuration for repo1.maven repository
repo1_maven:
  base: "https://repo1.maven.org"             # Base URL of the repository
  path: "maven2"                              # Path suffix for the repository
  auth: false                                 # Enables authentication for this repository
  repo: "maven2"                              # Repository name
  service_rest: false                         # Enables REST service for this repository
```

---

## Environment Variables

The tool supports environment variables to override configuration settings or provide credentials for external services.
Below is a list of supported environment variables:

### Configuration Overrides

These variables override settings from the `maven_check_versions.yml` file or command-line arguments. The format is
`CV_<KEY>` where `<KEY>` corresponds to a configuration key in the `base` section.

| Variable             | Description                                                          | Example Value |
|----------------------|----------------------------------------------------------------------|---------------|
| `CV_CACHE_OFF`       | Disables caching if set to `true`.                                   | `true`        |
| `CV_CACHE_TIME`      | Sets cache expiration time in seconds.                               | `3600`        |
| `CV_FAIL_MODE`       | Enables fail mode if set to `true`.                                  | `true`        |
| `CV_FAIL_MAJOR`      | Sets the major version threshold for failure.                        | `1`           |
| `CV_FAIL_MINOR`      | Sets the minor version threshold for failure.                        | `2`           |
| `CV_SEARCH_PLUGINS`  | Enables searching plugins if set to `true`.                          | `true`        |
| `CV_PROCESS_MODULES` | Enables processing of modules if set to `true`.                      | `true`        |
| `CV_SHOW_SKIP`       | Logs skipped dependencies if set to `true`.                          | `true`        |
| `CV_SHOW_SEARCH`     | Logs search actions if set to `true`.                                | `true`        |
| `CV_EMPTY_VERSION`   | Allows empty versions if set to `true`.                              | `true`        |
| `CV_SHOW_INVALID`    | Logs invalid dependencies if set to `true`.                          | `true`        |
| `CV_THREADING`       | Enables multi-threading if set to `true`.                            | `true`        |
| `CV_MAX_THREADS`     | Sets the maximum number of threads to use when threading is enabled. | `8`           |
| `CV_USER`            | Specifies the username for repository authentication.                | `my_username` |
| `CV_PASSWORD`        | Specifies the password for repository authentication.                | `my_password` |

#### Other configuration sections

The format is `CV_<SECTION>_<KEY>` where `<KEY>` corresponds to a configuration key in the `<SECTION>` section.

### Usage Example

To override cache settings:

```bash
export CV_CACHE_TIME=1800
maven_check_versions --pom_file path/to/pom.xml
```

---

## License

This project is licensed under the MIT License.

---