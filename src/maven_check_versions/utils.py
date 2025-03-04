#!/usr/bin/python3
"""This file provides utility functions"""

import logging
import os
import re
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from argparse import ArgumentParser

import dateutil.parser as parser
import maven_check_versions.cache as _cache
import maven_check_versions.config as _config
import maven_check_versions.logutils as _logutils
import requests


def parse_command_line() -> dict:
    """
    Parses command-line arguments.

    Returns:
        dict: Dictionary with parsed command-line arguments.
    """
    argument_parser = ArgumentParser(prog='maven_check_versions')
    argument_parser.add_argument('-ci', '--ci_mode', help='Enable CI Mode', action='store_true', default=False)
    argument_parser.add_argument('-pf', '--pom_file', help='Path to POM File')
    argument_parser.add_argument('-fa', '--find_artifact', help='Artifact to find')
    # override for config file options
    argument_parser.add_argument('-co', '--cache_off', help='Disable Cache', action='store_true', default=None)
    argument_parser.add_argument('-cf', '--cache_file', help='Path to Cache File')
    argument_parser.add_argument('-ct', '--cache_time', help='Cache expiration time in seconds')
    argument_parser.add_argument('-lfo', '--logfile_off', help='Disable Log file', action='store_true', default=None)
    argument_parser.add_argument('-lf', '--log_file', help='Path to Log File')
    argument_parser.add_argument('-cfg', '--config_file', help='Path to Config File')
    argument_parser.add_argument('-fm', '--fail_mode', help='Enable Fail Mode', action='store_true', default=None)
    argument_parser.add_argument('-mjv', '--fail_major', help='Major version threshold for failure')
    argument_parser.add_argument('-mnv', '--fail_minor', help='Minor version threshold for failure')
    argument_parser.add_argument('-sp', '--search_plugins', help='Search plugins', action='store_true', default=None)
    argument_parser.add_argument('-sm', '--process_modules', help='Process modules', action='store_true', default=None)
    argument_parser.add_argument('-sk', '--show_skip', help='Show Skip', action='store_true', default=None)
    argument_parser.add_argument('-ss', '--show_search', help='Show Search', action='store_true', default=None)
    argument_parser.add_argument(
        '-ev', '--empty_version', help='Allow empty version', action='store_true', default=None)
    argument_parser.add_argument('-si', '--show_invalid', help='Show Invalid', action='store_true', default=None)
    argument_parser.add_argument('-un', '--user', help='Basic Auth user')
    argument_parser.add_argument('-up', '--password', help='Basic Auth password')
    argument_parser.add_argument('-th', '--threading', help='Enable threading', action='store_true', default=None)
    argument_parser.add_argument('-mt', '--max_threads', help='Maximum number of threads', type=int)
    return vars(argument_parser.parse_args())


def get_artifact_name(root: ET.Element, ns_mapping: dict) -> str:
    """
    Extracts the full artifact name from a POM file.

    Args:
        root (ET.Element): Root element of the POM file.
        ns_mapping (dict): XML namespace mapping.

    Returns:
        str: Full artifact name (groupId:artifactId).
    """
    artifact_id = root.find('./xmlns:artifactId', namespaces=ns_mapping).text
    group_id_element = root.find('./xmlns:groupId', namespaces=ns_mapping)
    return (group_id_element.text + ':' if group_id_element is not None else '') + artifact_id


def collect_dependencies(
        root: ET.Element, ns_mapping: dict, config: dict, arguments: dict
) -> list:
    """
    Collects dependencies from a POM file.

    Args:
        root (ET.Element): Root element of the POM file.
        ns_mapping (dict): XML namespace mapping.
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.

    Returns:
        list: List of dependency elements.
    """
    dependencies = root.findall('.//xmlns:dependency', namespaces=ns_mapping)
    if _config.get_config_value(config, arguments, 'search_plugins', value_type=bool):
        plugin_xpath = './/xmlns:plugins/xmlns:plugin'
        plugins = root.findall(plugin_xpath, namespaces=ns_mapping)
        dependencies.extend(plugins)
    return dependencies


def get_dependency_identifiers(dependency: ET.Element, ns_mapping: dict) -> tuple[str, str | None]:
    """
    Extracts artifactId and groupId from a dependency.

    Args:
        dependency (ET.Element): Dependency element.
        ns_mapping (dict): XML namespace mapping.

    Returns:
        tuple[str, str | None]: Tuple of artifactId and groupId (or None if groupId is missing).
    """
    artifact_id = dependency.find('xmlns:artifactId', namespaces=ns_mapping)
    group_id = dependency.find('xmlns:groupId', namespaces=ns_mapping)
    return None if artifact_id is None else artifact_id.text, None if group_id is None else group_id.text


def fail_mode_if_required(
        config: dict, current_major_version: int, current_minor_version: int, item: str,
        major_version_threshold: int, minor_version_threshold: int, arguments: dict, version: str
) -> None:
    """
    Checks fail mode and raises an exception if version exceeds thresholds.

    Args:
        config (dict): Parsed YAML as dict.
        current_major_version (int): Current major version.
        current_minor_version (int): Current minor version.
        item (str): Version to check.
        major_version_threshold (int): Major version threshold for failure.
        minor_version_threshold (int): Minor version threshold for failure.
        arguments (dict): Command-line arguments.
        version (str): Current artifact version.
    """
    if _config.get_config_value(config, arguments, 'fail_mode', value_type=bool):
        item_major_version = 0
        item_minor_version = 0

        if item_match := re.match('^(\\d+).(\\d+).?', item):
            item_major_version, item_minor_version = int(item_match.group(1)), int(item_match.group(2))

        if item_major_version - current_major_version > major_version_threshold or \
                item_minor_version - current_minor_version > minor_version_threshold:
            logging.warning(f"Fail version: {item} > {version}")
            raise AssertionError


def resolve_version(version: str, root: ET.Element, ns_mapping: dict) -> str:
    """
    Resolves version text by checking POM properties.

    Args:
        version (str): Version text, possibly with placeholders.
        root (ET.Element): Root element of the POM file.
        ns_mapping (dict): XML namespace mapping.

    Returns:
        str: Resolved version or original text if unresolved.
    """
    if match := re.match(r'^\${([^}]+)}$', version):
        property_xpath = f"./xmlns:properties/xmlns:{match.group(1)}"
        property_element = root.find(property_xpath, namespaces=ns_mapping)
        if property_element is not None:
            version = property_element.text
    return version


def get_version(
        config: dict, arguments: dict, ns_mapping: dict, root: ET.Element,
        dependency: ET.Element
) -> tuple[str | None, bool]:
    """
    Extracts version information from a dependency.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.
        ns_mapping (dict): XML namespace mapping.
        root (ET.Element): Root element of the POM file.
        dependency (ET.Element): Dependency element.

    Returns:
        tuple[str | None, bool]: Tuple of version (or None) and skip flag.
    """
    version_text = ''
    version = dependency.find('xmlns:version', namespaces=ns_mapping)

    if version is None:
        if not _config.get_config_value(config, arguments, 'empty_version', value_type=bool):
            return None, True
    else:
        version_text = resolve_version(version.text, root, ns_mapping)

        if version_text == '${project.version}':
            project_version_text = root.find('xmlns:version', namespaces=ns_mapping).text
            version_text = resolve_version(project_version_text, root, ns_mapping)

        if re.match('^\\${([^}]+)}$', version_text):
            if not _config.get_config_value(config, arguments, 'empty_version', value_type=bool):
                return version_text, True

    return version_text, False


def check_versions(
        cache_data: dict | None, config: dict, arguments: dict, group_id: str,
        artifact_id: str, version: str, section_key: str, path: str, auth_info: tuple, verify_ssl: bool,
        available_versions: list[str], response: requests.Response
) -> bool:
    """
    Checks dependency versions in a repository.

    Args:
        cache_data (dict | None): Cache data.
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.
        group_id (str): Group ID.
        artifact_id (str): Artifact ID.
        version (str): Current version.
        section_key (str): Repository section key.
        path (str): Path to the dependency in the repository.
        auth_info (tuple): Authentication credentials.
        verify_ssl (bool): SSL verification flag.
        available_versions (list[str]): List of available versions.
        response (requests.Response): Repository response.

    Returns:
        bool: True if the current version is valid, False otherwise.
    """
    available_versions = list(filter(lambda v: re.match('^\\d+.+', v), available_versions))
    available_versions.reverse()

    major_threshold = minor_threshold = 0
    current_major = current_minor = 0

    if _config.get_config_value(config, arguments, 'fail_mode', value_type=bool):
        major_threshold = int(_config.get_config_value(config, arguments, 'fail_major'))
        minor_threshold = int(_config.get_config_value(config, arguments, 'fail_minor'))

        if version_match := re.match('^(\\d+)\\.(\\d+).?', version):
            current_major, current_minor = int(version_match.group(1)), int(version_match.group(2))

    skip_current = _config.get_config_value(config, arguments, 'skip_current', value_type=bool)
    invalid_flag = False

    for item in available_versions:
        if item == version and skip_current:
            _cache.update_cache(cache_data, available_versions, artifact_id, group_id, item, None, section_key)
            return True

        is_valid, last_modified = get_pom_data(auth_info, verify_ssl, artifact_id, item, path)
        if is_valid:
            logging.info('{}: {}:{}, current:{} {} {}'.format(
                section_key, group_id, artifact_id, version, available_versions[:3], last_modified).rstrip())

            _cache.update_cache(cache_data, available_versions, artifact_id, group_id, item, last_modified, section_key)

            fail_mode_if_required(
                config, current_major, current_minor, item,
                major_threshold, minor_threshold, arguments, version)
            return True

        else:
            _logutils.log_invalid_if_required(
                config, arguments, response, group_id, artifact_id, item, invalid_flag)
            invalid_flag = True

    return False


def get_pom_data(
        auth_info: tuple, verify_ssl: bool, artifact_id: str, version: str, path: str
) -> tuple[bool, str | None]:
    """
    Retrieves POM file data from a repository.

    Args:
        auth_info (tuple): Authentication credentials.
        verify_ssl (bool): SSL verification flag.
        artifact_id (str): Artifact ID.
        version (str): Artifact version.
        path (str): Path to the dependency in the repository.

    Returns:
        tuple[bool, str | None]: Tuple of success flag and last modified date (or None).
    """
    url = f"{path}/{version}/{artifact_id}-{version}.pom"
    response = requests.get(url, auth=auth_info, verify=verify_ssl)

    if response.status_code == 200:
        last_modified_header = response.headers.get('Last-Modified')
        return True, parser.parse(last_modified_header).date().isoformat()

    return False, None


def get_pom_tree(
        pom_path: str, verify_ssl: bool, config: dict, arguments: dict
) -> ET.ElementTree:
    """
    Loads the XML tree of a POM file.

    Args:
        pom_path (str): Path or URL to the POM file.
        verify_ssl (bool): SSL verification flag.
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.

    Returns:
        ET.ElementTree: Parsed XML tree of the POM file.
    """
    if pom_path.startswith('http'):
        auth_info = ()
        if _config.get_config_value(config, arguments, 'auth', 'pom_http', value_type=bool):
            auth_info = (
                _config.get_config_value(config, arguments, 'user'),
                _config.get_config_value(config, arguments, 'password')
            )
        response = requests.get(pom_path, auth=auth_info, verify=verify_ssl)
        if response.status_code != 200:
            raise FileNotFoundError(f'{pom_path} not found')
        return ET.ElementTree(ET.fromstring(response.text))
    else:
        if not os.path.exists(pom_path):
            raise FileNotFoundError(f'{pom_path} not found')
        return ET.parse(pom_path)
