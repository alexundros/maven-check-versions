---
# Maven Check Versions

Is a Python package designed for analyzing Maven POM files and managing dependencies.
It checks the versions of dependencies in a project and identifies the latest available versions in Maven repositories.
Developed for developers, this package simplifies dependency management in Maven-based projects.
It is especially useful in CI/CD environments, where maintaining consistency and up-to-date dependencies is critical.

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

You can install the tool via `pip`:

```bash
pip install maven_check_versions
```

---

## Usage

Run the script directly from the command line:

```bash
python -m maven_check_versions --pom_file <path-to-pom.xml>
```

### Example Commands:

- Analyze a specific POM file:
  ```bash
  python -m maven_check_versions --pom_file <path-to-pom.xml>
  ```

- Search for a specific artifact:
  ```bash
  python -m maven_check_versions --find_artifact com.example:my-lib:1.0
  ```

- Enable CI mode to suppress prompts:
  ```bash
  python -m maven_check_versions --ci_mode
  ```

---

## Command-Line Arguments

### General Options

| Parameter         | Short | Description                                                                                      | Example                               |
|-------------------|-------|--------------------------------------------------------------------------------------------------|---------------------------------------|
| `--ci_mode`       | `-ci` | Enables CI (Continuous Integration) mode. Suppresses prompts and waits for user input.           | `--ci_mode`                           |
| `--pom_file`      | `-pf` | Specifies the path to the Maven POM file to process.                                             | `--pom_file path/to/pom.xml`          |
| `--find_artifact` | `-fa` | Searches for a specific artifact. Provide the artifact in `groupId:artifactId:version` format.   | `--find_artifact com.example:lib:1.0` |

### Cache Control

| Parameter      | Short | Description                                        | Example                      |
|----------------|-------|----------------------------------------------------|------------------------------|
| `--cache_off`  | `-co` | Disables caching to force fresh dependency checks. | `--cache_off`                |
| `--cache_file` | `-cf` | Specifies a custom path for the cache file.        | `--cache_file my_cache.json` |
| `--cache_time` | `-cf` | Specifies the cache expiration time in seconds.    | `--cache_time 1800`          |

### Logging Options

| Parameter       | Short | Description                                                           | Example                 |
|-----------------|-------|-----------------------------------------------------------------------|-------------------------|
| `--logfile_off` | `-lfo`| Disables logging to a file. Logs will only be shown in the terminal.  | `--logfile_off`         |
| `--log_file`    | `-lf` | Specifies the path to a custom log file.                              | `--log_file my_log.log` |

### Configuration Options

| Parameter       | Short | Description                                             | Example                     |
|-----------------|-------|---------------------------------------------------------|-----------------------------|
| `--config_file` | `-cfg`| Specifies a custom configuration file for the script.   | `--config_file config.cfg`  |

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

### Authentication

| Parameter    | Short | Description                                                                 | Example                  |
|--------------|-------|-----------------------------------------------------------------------------|--------------------------|
| `--user`     | `-un` | Specifies a username for basic authentication when accessing repositories.  | `--user my_username`     |
| `--password` | `-up` | Specifies a password for basic authentication when accessing repositories.  | `--password my_password` |

---

## Configuration

You can customize the tool’s behavior using a configuration file `maven_check_versions.cfg` or environment variables.
The following settings can be adjusted:

- **SSL Verification:** Enable or disable SSL verification for HTTP requests.
- **Cache Preferences:** Control cache duration and behavior.
- **Repository Settings:** Define base URLs, authentication, and paths for repositories.
- **Logging Preferences:** Specify log levels and file paths.

See the [`maven_check_versions.cfg.dist`](https://raw.githubusercontent.com/alexundros/maven-check-versions/refs/heads/main/maven_check_versions.cfg.dist) file configuration file structure.

---

## License

This project is licensed under the MIT License. See the [`LICENSE`](https://raw.githubusercontent.com/alexundros/maven-check-versions/refs/heads/main/LICENSE) file for more details.

---