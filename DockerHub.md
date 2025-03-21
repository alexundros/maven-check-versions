# Maven Check Versions

**GitHub project link:** https://github.com/alexundros/maven-check-versions

Is a Python package designed for analyzing Maven POM files and managing dependencies.
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
- **Caching:** Caches results for faster rechecks.
- **Logging:** Provides configurable logging for detailed analysis.
- **Command-Line Interface:** Easily integrates into CI/CD pipelines.

---

## Installation

Pull image:

```bash
docker pull alexundros/maven-check-versions
```

Pull image based on pypy:

```bash
docker pull alexundros/maven-check-versions:pypy
```

## Usage

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

| Parameter         | Short | Description                                                                                     | Example                               |
|-------------------|-------|-------------------------------------------------------------------------------------------------|---------------------------------------|
| `--ci_mode`       | `-ci` | Enables CI (Continuous Integration) mode. Suppresses prompts and waits for user input.          | `--ci_mode`                           |
| `--pom_file`      | `-pf` | Specifies the path to the Maven POM file to process.                                            | `--pom_file path/to/pom.xml`          |
| `--find_artifact` | `-fa` | Searches for a specific artifact. Provide the artifact in `groupId:artifactId:version` format.  | `--find_artifact com.example:lib:1.0` |

### Cache Control

| Parameter         | Short | Description                                                             | Example                   |
|-------------------|-------|-------------------------------------------------------------------------|---------------------------|
| `--cache_off`     | `-co` | Disables caching to force fresh dependency checks.                      | `--cache_off`             |
| `--cache_file`    | `-cf` | Specifies a custom path for the cache file (only for JSON backend).     | `--cache_file cache.json` |
| `--cache_time`    | `-ct` | Specifies the cache expiration time in seconds.                         | `--cache_time 1800`       |
| `--cache_backend` | `-cb` | Specifies the cache backend to use (json, redis, tarantool, memcached). | `--cache_backend redis`   |

Depending on the selected cache backend, additional command-line arguments may be required:

#### Redis Cache Backend

| Parameter          | Short   | Description                                      | Example                  |
|--------------------|---------|--------------------------------------------------|--------------------------|
| `--redis_host`     | `-rsh`  | Redis host (default: localhost).                 | `--redis_host redis`     |
| `--redis_port`     | `-rsp`  | Redis port (default: 6379).                      | `--redis_port 6379`      |
| `--redis_key`      | `-rsk`  | Redis key (default: maven_check_versions_cache). | `--redis_key mycache`    |
| `--redis_user`     | `-rsu`  | Redis username (optional).                       | `--redis_user user`      |
| `--redis_password` | `-rsup` | Redis password (optional).                       | `--redis_password pass`  |

#### Tarantool Cache Backend

| Parameter              | Short   | Description                                            | Example                      |
|------------------------|---------|--------------------------------------------------------|------------------------------|
| `--tarantool_host`     | `-tlh`  | Tarantool host (default: localhost).                   | `--tarantool_host tarantool` |
| `--tarantool_port`     | `-tlp`  | Tarantool port (default: 3301).                        | `--tarantool_port 3301`      |
| `--tarantool_space`    | `-tls`  | Tarantool space (default: maven_check_versions_cache). | `--tarantool_space myspace`  |
| `--tarantool_user`     | `-tlu`  | Tarantool username (optional).                         | `--tarantool_user user`      |
| `--tarantool_password` | `-tlup` | Tarantool password (optional).                         | `--tarantool_password pass`  |

#### Memcached Cache Backend

| Parameter           | Short  | Description                                          | Example                      |
|---------------------|--------|------------------------------------------------------|------------------------------|
| `--memcached_host`  | `-mch` | Memcached host (default: localhost).                 | `--memcached_host memcached` |
| `--memcached_port`  | `-mcp` | Memcached port (default: 11211).                     | `--memcached_port 11211`     |
| `--memcached_key`   | `-mck` | Memcached key (default: maven_check_versions_cache). | `--memcached_key mycache`    |

### Logging Options

| Parameter       | Short | Description                                                           | Example                 |
|-----------------|-------|-----------------------------------------------------------------------|-------------------------|
| `--logfile_off` | `-lfo`| Disables logging to a file. Logs will only be shown in the terminal.  | `--logfile_off`         |
| `--log_file`    | `-lf` | Specifies the path to a custom log file.                              | `--log_file my_log.log` |

### Configuration Options

| Parameter       | Short | Description                                             | Example                     |
|-----------------|-------|---------------------------------------------------------|-----------------------------|
| `--config_file` | `-cfg`| Specifies a custom configuration file for the script.   | `--config_file config.yml`  |

### Error Handling and Validation

| Parameter      | Short | Description                                                                                        | Example          |
|----------------|-------|----------------------------------------------------------------------------------------------------|------------------|
| `--fail_mode`  | `-fm` | Enables "fail mode." The script will terminate if dependency versions exceed specified thresholds. | `--fail_mode`    |
| `--fail_major` | `-mjv`| Specifies the major version difference threshold for failure.                                      | `--fail_major 1` |
| `--fail_minor` | `-mnv`| Specifies the minor version difference threshold for failure.                                      | `--fail_minor 2` |

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

| Parameter      | Short | Description                                                                 | Example           |
|----------------|-------|-----------------------------------------------------------------------------|-------------------|
| `--threading`  | `-th` | Enables multi-threading to process dependencies and modules concurrently.   | `--threading`     |
| `--max_threads`| `-mt` | Specifies the maximum number of threads to use when threading is enabled.   | `--max_threads 8` |

### Authentication

| Parameter    | Short | Description                                                                 | Example                  |
|--------------|-------|-----------------------------------------------------------------------------|--------------------------|
| `--user`     | `-un` | Specifies a username for basic authentication when accessing repositories.  | `--user my_username`     |
| `--password` | `-up` | Specifies a password for basic authentication when accessing repositories.  | `--password my_password` |

---

## Configuration

You can customize the tool’s behavior using a configuration file [`maven_check_versions.yml`](https://raw.githubusercontent.com/alexundros/maven-check-versions/refs/heads/main/maven_check_versions.yml.dist).
The following settings can be adjusted:

- **SSL Verification:** Enable or disable SSL verification for HTTP requests.
- **Cache Preferences:** Control cache duration and behavior.
- **Repository Settings:** Define base URLs, authentication, and paths for repositories.
- **Logging Preferences:** Specify log levels and file paths.

Use a default configuration file name:

```bash
docker run --rm -v './config.cfg:/app/maven_check_versions.yml' -v 'path/to/pom.xml:/app/pom.xml' alexundros/maven_check_versions -pf /app/pom.xml
```

Use a specific configuration file name:

```bash
docker run --rm -v './config.cfg:/app/cfg.yml' -v 'path/to/pom.xml:/app/pom.xml' alexundros/maven_check_versions -cfg /app/cfg.yml -pf /app/pom.xml
```

### Cache Configuration

The tool supports multiple cache backends:

- **JSON** (default): Stores cache data in a local JSON file specified by `cache_file`.
- **Redis**: Uses a Redis server for caching.
- **Tarantool**: Uses a Tarantool server for caching.
- **Memcached**: Uses a Memcached server for caching.

### Example configuration

maven_check_versions.yml:
```
base:
  cache_off: false
  cache_time: 600
  cache_backend: redis
  redis_host: redis
  redis_port: 6379
  redis_key: mycache
  redis_user: user
  redis_password: pass
  fail_mode: false
  fail_major: 0
  fail_minor: 0
  search_plugins: false
  process_modules: false
  show_skip: false
  show_search: false
  empty_version: false
  show_invalid: false
  skip_version: true
  threading: false
  max_threads: 8
  user: "USER"
  password: "PASSWORD"

pom_http:
  auth: true

urllib3:
  warnings: true

requests:
  verify: true

pom_files:
  pom-name: "path/to/pom.xml"

repositories:
  "Central (repo1.maven.org)": "repo1.maven"

repo1.maven:
  base: "https://repo1.maven.org"
  path: "maven2"
  auth: false
```

---

## Environment Variables

The tool supports environment variables to override configuration settings or provide credentials for external services. Below is a list of supported environment variables:

### Configuration Overrides
These variables override settings from the `maven_check_versions.yml` file or command-line arguments. The format is `CV_<KEY>` where `<KEY>` corresponds to a configuration key in the `base` section (case-insensitive).

| Variable            | Description                                                                 | Example Value   |
|---------------------|-----------------------------------------------------------------------------|-----------------|
| `CV_CACHE_OFF`      | Disables caching if set to `true`.                                          | `true`          |
| `CV_CACHE_TIME`     | Sets cache expiration time in seconds.                                      | `3600`          |
| `CV_FAIL_MODE`      | Enables fail mode if set to `true`.                                         | `true`          |
| `CV_FAIL_MAJOR`     | Sets the major version threshold for failure.                               | `1`             |
| `CV_FAIL_MINOR`     | Sets the minor version threshold for failure.                               | `2`             |
| `CV_SEARCH_PLUGINS` | Enables searching plugins if set to `true`.                                 | `true`          |
| `CV_PROCESS_MODULES`| Enables processing of modules if set to `true`.                             | `true`          |
| `CV_SHOW_SKIP`      | Logs skipped dependencies if set to `true`.                                 | `true`          |
| `CV_SHOW_SEARCH`    | Logs search actions if set to `true`.                                       | `true`          |
| `CV_EMPTY_VERSION`  | Allows empty versions if set to `true`.                                     | `true`          |
| `CV_SHOW_INVALID`   | Logs invalid dependencies if set to `true`.                                 | `true`          |
| `CV_THREADING`      | Enables multi-threading if set to `true`.                                   | `true`          |
| `CV_MAX_THREADS`    | Sets the maximum number of threads to use when threading is enabled.        | `8`             |
| `CV_USER`           | Specifies the username for repository authentication.                       | `my_username`   |
| `CV_PASSWORD`       | Specifies the password for repository authentication.                       | `my_password`   |

### Usage Example

To override cache settings:

```bash
docker run --rm -e CV_CACHE_TIME=1800 -v 'path/to/pom.xml:/app/pom.xml' alexundros/maven_check_versions -pf /app/pom.xml
```

---

## License

This project is licensed under the MIT License. See the [`LICENSE`](https://raw.githubusercontent.com/alexundros/maven-check-versions/refs/heads/main/LICENSE) file for more details.

---