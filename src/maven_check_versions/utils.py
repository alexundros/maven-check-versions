#!/usr/bin/python3
"""This file provides utility functions"""

import logging
import os
import re
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from argparse import ArgumentParser
from typing import Optional

import dateutil.parser as parser
import maven_check_versions.cache as _cache
import maven_check_versions.config as _config
import maven_check_versions.logutils as _logutils
import requests
from maven_check_versions.config import Config, Arguments


def parse_command_line() -> Arguments:
    """
    Parses the command-line arguments and returns them as an Arguments object.

    Returns:
        Arguments: An object containing the parsed command-line arguments,
                    wrapping a dictionary of argument key-value pairs.
    """
    argument_parser = ArgumentParser(prog='maven_check_versions')
    add_general_args(argument_parser)
    add_cache_args(argument_parser)
    add_logging_args(argument_parser)
    add_fail_mode_args(argument_parser)
    add_search_args(argument_parser)
    add_auth_args(argument_parser)
    add_threading_args(argument_parser)
    return Arguments(vars(argument_parser.parse_args()))


def add_general_args(argument_parser: ArgumentParser) -> None:
    """
    Adds general command-line arguments to the argument parser.
    These include options for CI mode, POM file path, artifact to find, and configuration file path.

    Args:
        argument_parser (ArgumentParser): The ArgumentParser instance to which general arguments are added.
    """
    argument_parser.add_argument('-ci', '--ci_mode', help='Enable CI Mode', action='store_true', default=False)
    argument_parser.add_argument('-pf', '--pom_file', help='Path to POM File')
    argument_parser.add_argument('-fa', '--find_artifact', help='Artifact to find')
    argument_parser.add_argument('-cfg', '--config_file', help='Path to Config File')
    argument_parser.add_argument('-ll', '--log_level', help='Logging level', default=None)


def add_cache_args(argument_parser: ArgumentParser) -> None:
    """
    Adds cache-related arguments to the parser.

    Args:
        argument_parser (ArgumentParser): The argument parser to which arguments are added.
    """
    argument_parser.add_argument('-co', '--cache_off', help='Disable Cache', action='store_true', default=None)
    argument_parser.add_argument('-cf', '--cache_file', help='Path to Cache File')
    argument_parser.add_argument('-ct', '--cache_time', help='Cache expiration time in seconds')
    argument_parser.add_argument('-cb', '--cache_backend', help='Cache backend')

    argument_parser.add_argument('-rsh', '--redis_host', help='Redis host', default=None)
    argument_parser.add_argument('-rsp', '--redis_port', help='Redis port', default=None)
    argument_parser.add_argument('-rsk', '--redis_key', help='Redis key', default=None)
    argument_parser.add_argument('-rsu', '--redis_user', help='Redis user', default=None)
    argument_parser.add_argument('-rsup', '--redis_password', help='Redis password', default=None)

    argument_parser.add_argument('-tlh', '--tarantool_host', help='Tarantool host', default=None)
    argument_parser.add_argument('-tlp', '--tarantool_port', help='Tarantool port', default=None)
    argument_parser.add_argument('-tls', '--tarantool_space', help='Tarantool space', default=None)
    argument_parser.add_argument('-tlu', '--tarantool_user', help='Tarantool user', default=None)
    argument_parser.add_argument('-tlup', '--tarantool_password', help='Tarantool password', default=None)

    argument_parser.add_argument('-mch', '--memcached_host', help='Memcached host', default=None)
    argument_parser.add_argument('-mcp', '--memcached_port', help='Memcached port', default=None)
    argument_parser.add_argument('-mck', '--memcached_key', help='Memcached key', default=None)


def add_logging_args(argument_parser: ArgumentParser) -> None:
    """
    Adds logging-related arguments to the parser.

    Args:
        argument_parser (ArgumentParser): The argument parser to which arguments are added.
    """
    argument_parser.add_argument('-lfo', '--logfile_off', help='Disable Log file', action='store_true', default=None)
    argument_parser.add_argument('-lf', '--log_file', help='Path to Log File')


def add_fail_mode_args(argument_parser: ArgumentParser) -> None:
    """
    Adds fail mode-related arguments to the parser.

    Args:
        argument_parser (ArgumentParser): The argument parser to which arguments are added.
    """
    argument_parser.add_argument('-fm', '--fail_mode', help='Enable Fail Mode', action='store_true', default=None)
    argument_parser.add_argument('-mjv', '--fail_major', help='Major version threshold for failure')
    argument_parser.add_argument('-mnv', '--fail_minor', help='Minor version threshold for failure')


def add_search_args(argument_parser: ArgumentParser) -> None:
    """
    Adds search-related arguments to the parser.

    Args:
        argument_parser (ArgumentParser): The argument parser to which arguments are added.
    """
    argument_parser.add_argument('-sp', '--search_plugins', help='Search plugins', action='store_true', default=None)
    argument_parser.add_argument('-sm', '--process_modules', help='Process modules', action='store_true', default=None)
    argument_parser.add_argument('-sk', '--show_skip', help='Show Skip', action='store_true', default=None)
    argument_parser.add_argument('-ss', '--show_search', help='Show Search', action='store_true', default=None)
    argument_parser.add_argument(
        '-ev', '--empty_version', help='Allow empty version', action='store_true', default=None)
    argument_parser.add_argument('-si', '--show_invalid', help='Show Invalid', action='store_true', default=None)


def add_auth_args(argument_parser: ArgumentParser) -> None:
    """
    Adds authentication-related arguments to the parser.

    Args:
        argument_parser (ArgumentParser): The argument parser to which arguments are added.
    """
    argument_parser.add_argument('-un', '--user', help='Basic Auth user')
    argument_parser.add_argument('-up', '--password', help='Basic Auth password')


def add_threading_args(argument_parser: ArgumentParser) -> None:
    """
    Adds threading-related arguments to the parser.

    Args:
        argument_parser (ArgumentParser): The argument parser to which arguments are added.
    """
    argument_parser.add_argument('-th', '--threading', help='Enable threading', action='store_true', default=None)
    argument_parser.add_argument('-mt', '--max_threads', help='Maximum number of threads', type=int)


def get_artifact_name(root: ET.Element, ns_mapping: dict) -> str:
    """
    Extracts the groupId and artifactId from the POM file's root element.

    Args:
        root (ET.Element): The root element of the POM file's XML tree.
        ns_mapping (dict): A dictionary mapping XML namespaces for parsing.

    Returns:
        str: The full artifact name in the format 'groupId:artifactId'.
            If groupId is not present, returns only the artifactId.
    """
    artifact = root.find('./xmlns:artifactId', namespaces=ns_mapping)
    artifact_text = str(artifact.text) if artifact is not None else ''
    group = root.find('./xmlns:groupId', namespaces=ns_mapping)
    return (str(group.text) + ':' if group is not None else '') + artifact_text


def collect_dependencies(
        root: ET.Element, ns_mapping: dict, config: Config, arguments: Arguments
) -> list:
    """
    Collects all dependency elements from the POM file.
    Optionally includes plugin elements if 'search_plugins' is enabled in the configuration.

    Args:
        root (ET.Element): The root element of the POM file's XML tree.
        ns_mapping (dict): A dictionary mapping XML namespaces for parsing.
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.

    Returns:
        list[ET.Element]: A list of dependency elements (and plugin elements if specified).
    """
    dependencies = root.findall('.//xmlns:dependency', namespaces=ns_mapping)
    if _config.get_config_value(config, arguments, 'search_plugins'):
        plugins = root.findall('.//xmlns:plugins/xmlns:plugin', namespaces=ns_mapping)
        dependencies.extend(plugins)
    return dependencies


def get_dependency_identifiers(dependency: ET.Element, ns_mapping: dict) -> tuple[str, str]:
    """
    Extracts the groupId and artifactId from a dependency element.

    Args:
        dependency (ET.Element): The dependency XML element from the POM file.
        ns_mapping (dict): A dictionary mapping XML namespaces for parsing.

    Returns:
        tuple[str, str]: A tuple containing:
            - group (str): The groupId, or an empty string if not present.
            - artifact (str): The artifactId, or an empty string if not present.
    """
    artifact = dependency.find('xmlns:artifactId', namespaces=ns_mapping)
    group = dependency.find('xmlns:groupId', namespaces=ns_mapping)
    return (
        str(group.text) if group is not None else '',
        str(artifact.text) if artifact is not None else ''
    )


def fail_mode_if_required(
        config: Config, current_major_version: int, current_minor_version: int, item: str,
        major_version_threshold: int, minor_version_threshold: int, arguments: Arguments,
        version: Optional[str]
) -> None:
    """
    Checks if fail mode is enabled and if the version exceeds specified thresholds.
    Logs a warning and raises an AssertionError if thresholds are exceeded.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        current_major_version (int): The major version of the current artifact version.
        current_minor_version (int): The minor version of the current artifact version.
        item (str): The version string to check against thresholds (e.g., '1.2.3').
        major_version_threshold (int): The maximum allowed difference in major versions.
        minor_version_threshold (int): The maximum allowed difference in minor versions.
        arguments (Arguments): Command-line arguments.
        version (Optional[str]): The current version of the artifact (e.g., '1.0.0').
    """
    if _config.get_config_value(config, arguments, 'fail_mode'):
        item_major_version = 0
        item_minor_version = 0

        if item and (item_match := re.match(r'^(\d+).(\d+).?', item)):
            item_major_version, item_minor_version = int(item_match.group(1)), int(item_match.group(2))

        if item_major_version - current_major_version > major_version_threshold or \
                item_minor_version - current_minor_version > minor_version_threshold:
            logging.warning(f"Fail version: {item} > {version}")
            raise AssertionError


def resolve_version(version: str, root: ET.Element, ns_mapping: dict) -> str:
    """
    Resolves the version string by replacing placeholders with values from POM properties.
    Handles placeholders like '${property}' or '${project.version}'.

    Args:
        version (str): The version string, which may contain placeholders (e.g., '${version}').
        root (ET.Element): The root element of the POM file's XML tree.
        ns_mapping (dict): A dictionary mapping XML namespaces for parsing.

    Returns:
        str: The resolved version string if a placeholder is matched and found in properties,
            otherwise the original version string.
    """
    if match := re.match(r'^\${([^}]+)}$', version):
        property_xpath = f"./xmlns:properties/xmlns:{match.group(1)}"
        property_element = root.find(property_xpath, namespaces=ns_mapping)
        if property_element is not None:
            version = str(property_element.text)
    return version


def get_version(
        config: Config, arguments: Arguments, ns_mapping: dict, root: ET.Element,
        dependency: ET.Element
) -> tuple[Optional[str], bool]:
    """
    Extracts version information from a dependency.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        ns_mapping (dict): XML namespace mapping.
        root (ET.Element): Root element of the POM file.
        dependency (ET.Element): Dependency element.

    Returns:
        tuple[Optional[str], bool]: Tuple of version (or None) and skip flag.
    """
    version_text = ''
    version = dependency.find('xmlns:version', namespaces=ns_mapping)

    if version is None:
        if not _config.get_config_value(config, arguments, 'empty_version'):
            return None, True
    else:
        version_text = resolve_version(str(version.text), root, ns_mapping)

        if version_text == '${project.version}':
            project_version = root.find('xmlns:version', namespaces=ns_mapping)
            project_version_text = str(project_version.text) if project_version is not None else ''
            version_text = resolve_version(project_version_text, root, ns_mapping)

        if version_text and re.match(r'^\${([^}]+)}$', version_text):
            if not _config.get_config_value(config, arguments, 'empty_version'):
                return version_text, True

    return version_text, False


def check_versions(
        cache_data: Optional[dict], config: Config, arguments: Arguments, group: str, artifact: str,
        version: Optional[str], section_key: str, path: str, auth_info: Optional[tuple[str, str]],
        verify_ssl: bool, available_versions: list[str], response: requests.Response
) -> bool:
    """
    Checks dependency versions in a repository.

    Args:
        cache_data (Optional[dict]): Cache data.
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        group (str): Group ID.
        artifact (str): Artifact ID.
        version (Optional[str]): Current version.
        section_key (str): Repository section key.
        path (str): Path to the dependency in the repository.
        auth_info (Optional[tuple[str, str]]): Authentication credentials.
        verify_ssl (bool): SSL verification flag.
        available_versions (list[str]): List of available versions.
        response (requests.Response): Repository response.

    Returns:
        bool: True if the current version is valid, False otherwise.
    """
    available_versions = [v for v in available_versions if re.match(r'^\d+.+', v)]
    available_versions.reverse()

    major_threshold = minor_threshold = 0
    current_major = current_minor = 0

    if _config.get_config_value(config, arguments, 'fail_mode'):
        major_threshold = int(_config.get_config_value(config, arguments, 'fail_major'))
        minor_threshold = int(_config.get_config_value(config, arguments, 'fail_minor'))

        if version and (version_match := re.match(r'^(\d+)\.(\d+).?', version)):
            current_major, current_minor = int(version_match.group(1)), int(version_match.group(2))

    skip_current = _config.get_config_value(config, arguments, 'skip_current')
    invalid_flag = False

    for item in available_versions:
        if item == version and skip_current:
            _cache.update_cache_artifact(cache_data, available_versions, artifact, group, item, None, section_key)
            return True

        is_valid, last_modified = get_pom_data(auth_info, verify_ssl, artifact, item, path)
        if is_valid:
            logging.info('{}: {}:{}, current:{} {} {}'.format(
                section_key, group, artifact, version, available_versions[:3], last_modified).rstrip())

            _cache.update_cache_artifact(
                cache_data, available_versions, artifact, group, item, last_modified, section_key)

            fail_mode_if_required(
                config, current_major, current_minor, item,
                major_threshold, minor_threshold, arguments, version)
            return True

        else:
            _logutils.log_invalid_if_required(
                config, arguments, response, group, artifact, item, invalid_flag)
            invalid_flag = True

    return False


def get_pom_data(
        auth_info: Optional[tuple[str, str]], verify_ssl: bool, artifact: str, version: str, path: str
) -> tuple[bool, Optional[str]]:
    """
    Retrieves POM file data from a repository.

    Args:
        auth_info (Optional[tuple[str, str]]): Authentication credentials.
        verify_ssl (bool): SSL verification flag.
        artifact (str): Artifact ID.
        version (str): Artifact version.
        path (str): Path to the dependency in the repository.

    Returns:
        tuple[bool, Optional[str]]: Tuple of success flag and last modified date (or None).
    """
    with requests.Session() as session:
        url = f"{path}/{version}/{artifact}-{version}.pom"
        response = session.get(url, auth=auth_info, verify=verify_ssl)

        if response.status_code == 200:
            last_modified_header = response.headers.get('Last-Modified')
            return True, parser.parse(last_modified_header).date().isoformat()

    return False, None


def get_pom_tree(
        pom_path: str, verify_ssl: bool, config: Config, arguments: Arguments
) -> ET.ElementTree:
    """
    Loads the XML tree of a POM file.

    Args:
        pom_path (str): Path or URL to the POM file.
        verify_ssl (bool): SSL verification flag.
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.

    Returns:
        ET.ElementTree: Parsed XML tree of the POM file.
    """
    if pom_path.startswith('http'):
        auth_info: Optional[tuple[str, str]] = None
        if _config.get_config_value(config, arguments, 'auth', 'pom_http'):
            auth_info = (
                _config.get_config_value(config, arguments, 'user'),
                _config.get_config_value(config, arguments, 'password')
            )
        with requests.Session() as session:
            response = session.get(pom_path, auth=auth_info, verify=verify_ssl)
            if response.status_code != 200:
                raise FileNotFoundError(f"Failed to get_pom_tree {pom_path}: HTTP {response.status_code}")
            return ET.ElementTree(ET.fromstring(response.text))
    else:
        if not os.path.exists(pom_path) or not os.path.isfile(pom_path):
            raise FileNotFoundError(f"Failed to get_pom_tree {pom_path}")
        return ET.parse(pom_path)
