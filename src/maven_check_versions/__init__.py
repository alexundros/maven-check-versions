#!/usr/bin/python3
"""Main entry point for the package"""

import logging
import os
import sys
import time
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from configparser import ConfigParser

import requests
import urllib3
from bs4 import BeautifulSoup
from .cache import load_cache, save_cache, update_cache, process_cache
from .config import get_config_parser, get_config_value, config_items
from .logutils import (
    log_skip_if_required, log_search_if_required,
    log_invalid_if_required, configure_logging
)
from .utils import (
    parse_command_line, get_artifact_name, collect_dependencies,
    get_dependency_identifiers, fail_mode_if_required, resolve_version,
    get_version, check_versions, get_pom_tree
)


def process_main(arguments: dict) -> None:
    """
    Main processing function.

    Args:
        arguments (dict): Dictionary of parsed command line arguments.
    """
    config_parser = get_config_parser(arguments)

    if not get_config_value(config_parser, arguments, 'warnings', 'urllib3', value_type=bool):
        urllib3.disable_warnings()

    cache_disabled = get_config_value(config_parser, arguments, 'cache_off', value_type=bool)
    if (cache_file_path := arguments.get('cache_file')) is None:
        cache_file_path = 'maven_check_versions.cache'
    cache_data = load_cache(cache_file_path) if not cache_disabled else None

    if pom_file := arguments.get('pom_file'):
        process_pom(cache_data, config_parser, arguments, pom_file)
    elif artifact_to_find := arguments.get('find_artifact'):
        process_artifact(cache_data, config_parser, arguments, artifact_to_find)
    else:
        for key, pom in config_items(config_parser, 'pom_files'):
            process_pom(cache_data, config_parser, arguments, pom)

    if cache_data is not None:
        save_cache(cache_data, cache_file_path)


def process_pom(
        cache_data: dict | None, config_parser: ConfigParser, arguments: dict, pom_path: str, prefix: str = None
) -> None:
    """
    Process POM files.

    Args:
        cache_data (dict | None): Cache data for dependencies.
        config_parser (ConfigParser): Configuration data.
        arguments (dict): Command line arguments.
        pom_path (str): Path or URL to the POM file to process.
        prefix (str, optional): Prefix for the artifact name. Defaults to None.
    """
    verify_ssl = get_config_value(config_parser, arguments, 'verify', 'requests', value_type=bool)

    tree = get_pom_tree(pom_path, verify_ssl, config_parser, arguments)
    root = tree.getroot()
    ns_mapping = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}  # NOSONAR

    artifact_name = get_artifact_name(root, ns_mapping)
    if prefix is not None:
        prefix = artifact_name = f"{prefix} / {artifact_name}"
    logging.info(f"=== Processing: {artifact_name} ===")

    dependencies = collect_dependencies(root, ns_mapping, config_parser, arguments)
    process_dependencies(cache_data, config_parser, arguments, dependencies, ns_mapping, root, verify_ssl)

    process_modules_if_required(cache_data, config_parser, arguments, root, pom_path, ns_mapping, prefix)


def process_dependencies(
        cache_data: dict | None, config_parser: ConfigParser, arguments: dict, dependencies: list,
        ns_mapping: dict, root: ET.Element, verify_ssl: bool
) -> None:
    """
    Process dependencies in a POM file.

    Args:
        cache_data (dict | None): Cache object to store dependencies.
        config_parser (ConfigParser): Configuration object.
        arguments (dict): Command-line arguments.
        dependencies (list): List of dependencies from the POM file.
        ns_mapping (dict): XML namespace mapping.
        root (ET.Element): Root XML element of the POM file.
        verify_ssl (bool): Whether to verify HTTPS certificates.
    """
    for dependency in dependencies:
        artifact_id, group_id = get_dependency_identifiers(dependency, ns_mapping)
        if artifact_id is None or group_id is None:
            logging.error("Missing artifactId or groupId in a dependency.")
            continue

        version, skip_flag = get_version(config_parser, arguments, ns_mapping, root, dependency)
        if skip_flag is True:
            log_skip_if_required(config_parser, arguments, group_id, artifact_id, version)
            continue

        log_search_if_required(config_parser, arguments, group_id, artifact_id, version)

        if cache_data is not None and cache_data.get(f"{group_id}:{artifact_id}") is not None:
            if process_cache(arguments, cache_data, config_parser, artifact_id, group_id, version):
                continue

        if not process_repositories(artifact_id, cache_data, config_parser, group_id, arguments, verify_ssl, version):
            logging.warning(f"Not Found: {group_id}:{artifact_id}, current:{version}")


def process_repositories(
        artifact_id: str, cache_data: dict | None, config_parser: ConfigParser, group_id: str,
        arguments: dict, verify_ssl: bool, version: str
):
    """
    Process repositories to find a dependency.

    Args:
        artifact_id (str): Artifact ID of the dependency.
        cache_data (dict | None): Cache data containing dependency information.
        config_parser (ConfigParser): Configuration parser for settings.
        group_id (str): Group ID of the dependency.
        arguments (dict): Parsed command line arguments.
        verify_ssl (bool): Whether to verify SSL certificates.
        version (str): Version of the dependency.

    Returns:
        bool: True if the dependency is found in any repository, False otherwise.
    """
    if len(items := config_items(config_parser, 'repositories')):
        for section_key, repository_section in items:
            if (process_repository(
                    cache_data, config_parser, arguments, group_id, artifact_id, version,
                    section_key, repository_section, verify_ssl)):
                return True
    return False


def process_modules_if_required(
        cache_data: dict | None, config_parser: ConfigParser, arguments: dict, root: ET.Element,
        pom_path: str, ns_mapping: dict, prefix: str = None
) -> None:
    """
    Process modules listed in the POM file if required.

    Args:
        cache_data (dict | None): Cache data for dependencies.
        config_parser (ConfigParser): Configuration data.
        arguments (dict): Command line arguments.
        root (ET.Element): Root element of the POM file.
        pom_path (str): Path to the POM file.
        ns_mapping (dict): XML namespace mapping.
        prefix (str): Prefix for the artifact name.
    """
    if get_config_value(config_parser, arguments, 'process_modules', value_type=bool):
        directory_path = os.path.dirname(pom_path)
        module_xpath = './/xmlns:modules/xmlns:module'

        for module in root.findall(module_xpath, namespaces=ns_mapping):
            module_pom_path = f"{directory_path}/{module.text}/pom.xml"
            if os.path.exists(module_pom_path):
                process_pom(cache_data, config_parser, arguments, module_pom_path, prefix)


def process_artifact(
        cache_data: dict | None, config_parser: ConfigParser, arguments: dict, artifact_to_find: str
) -> None:
    """
    Process finding artifacts.

    Args:
        cache_data (dict | None): Cache data.
        config_parser (ConfigParser): Configuration settings.
        arguments (dict): Command-line arguments.
        artifact_to_find (str): Artifact to search for.
    """
    verify_ssl = get_config_value(config_parser, arguments, 'verify', 'requests', value_type=bool)
    group_id, artifact_id, version = artifact_to_find.split(sep=":", maxsplit=3)

    log_search_if_required(config_parser, arguments, group_id, artifact_id, version)

    dependency_found = False
    for section_key, repository_section in config_items(config_parser, 'repositories'):
        if (dependency_found := process_repository(
                cache_data, config_parser, arguments, group_id, artifact_id, version,
                section_key, repository_section, verify_ssl)):
            break
    if not dependency_found:
        logging.warning(f"Not Found: {group_id}:{artifact_id}, current:{version}")


def process_repository(
        cache_data: dict | None, config_parser: ConfigParser, arguments: dict, group_id: str,
        artifact_id: str, version: str, section_key: str, repository_section: str, verify_ssl: bool
) -> bool:
    """
    Process a repository section.

    Args:
        cache_data (dict | None): The cache dictionary.
        config_parser (ConfigParser): The configuration parser.
        arguments (dict): Dictionary containing the parsed command line arguments.
        group_id (str): The group ID of the artifact.
        artifact_id (str): The artifact ID.
        version (str): The version of the artifact.
        section_key (str): The key for the repository section.
        repository_section (str): The repository section name.
        verify_ssl (bool): Whether to verify SSL certificates.

    Returns:
        bool: True if the dependency is found, False otherwise.
    """
    auth_info = ()
    if get_config_value(config_parser, arguments, 'auth', repository_section, value_type=bool):
        auth_info = (
            get_config_value(config_parser, arguments, 'user'),
            get_config_value(config_parser, arguments, 'password')
        )

    base_url = get_config_value(config_parser, arguments, 'base', repository_section)
    path_suffix = get_config_value(config_parser, arguments, 'path', repository_section)
    repository_name = get_config_value(config_parser, arguments, 'repo', repository_section)

    path = f"{base_url}/{path_suffix}"
    if repository_name is not None:
        path = f"{path}/{repository_name}"
    path = f"{path}/{group_id.replace('.', '/')}/{artifact_id}"

    metadata_url = path + '/maven-metadata.xml'
    response = requests.get(metadata_url, auth=auth_info, verify=verify_ssl)

    if response.status_code == 200:
        tree = ET.ElementTree(ET.fromstring(response.text))
        version_elements = tree.getroot().findall('.//version')
        available_versions = list(map(lambda v: v.text, version_elements))

        if check_versions(
                cache_data, config_parser, arguments, group_id, artifact_id, version, section_key,
                path, auth_info, verify_ssl, available_versions, response):
            return True

    if get_config_value(config_parser, arguments, 'service_rest', repository_section, value_type=bool):
        return process_rest(
            cache_data, config_parser, arguments, group_id, artifact_id, version, section_key,
            repository_section, base_url, auth_info, verify_ssl)

    return False


def process_rest(
        cache_data: dict | None, config_parser: ConfigParser, arguments: dict, group_id: str,
        artifact_id: str, version: str, section_key: str, repository_section: str, base_url: str,
        auth_info: tuple, verify_ssl: bool
) -> bool:
    """
    Process REST services.

    Args:
        cache_data (dict | None): The cache dictionary.
        config_parser (ConfigParser): The configuration parser.
        arguments (dict): Dictionary containing the parsed command line arguments.
        group_id (str): The group ID of the artifact.
        artifact_id (str): The artifact ID.
        version (str): The version of the artifact.
        section_key (str): The key for the repository section.
        repository_section (str): The repository section name.
        base_url (str): The base URL of the repository.
        auth_info (tuple): Tuple containing basic authentication credentials.
        verify_ssl (bool): Whether to verify SSL certificates.

    Returns:
        bool: True if the dependency is found, False otherwise.
    """
    repository_name = get_config_value(config_parser, arguments, 'repo', repository_section)
    path = f"{base_url}/service/rest/repository/browse/{repository_name}"
    path = f"{path}/{group_id.replace('.', '/')}/{artifact_id}"

    metadata_url = path + '/maven-metadata.xml'
    response = requests.get(metadata_url, auth=auth_info, verify=verify_ssl)

    if response.status_code == 200:
        tree = ET.ElementTree(ET.fromstring(response.text))
        version_elements = tree.getroot().findall('.//version')
        available_versions = list(map(lambda v: v.text, version_elements))

        if check_versions(
                cache_data, config_parser, arguments, group_id, artifact_id, version,
                section_key, path, auth_info, verify_ssl, available_versions, response):
            return True

    response = requests.get(path + '/', auth=auth_info, verify=verify_ssl)

    if response.status_code == 200:
        html_content = BeautifulSoup(response.text, 'html.parser')
        version_links = html_content.find('table').find_all('a')
        available_versions = list(map(lambda v: v.text, version_links))
        path = f"{base_url}/repository/{repository_name}/{group_id.replace('.', '/')}/{artifact_id}"

        if check_versions(
                cache_data, config_parser, arguments, group_id, artifact_id, version,
                section_key, path, auth_info, verify_ssl, available_versions, response):
            return True

    return False


# noinspection PyMissingOrEmptyDocstring
def main() -> None:
    exception_occurred = False
    ci_mode_enabled = False

    try:
        start_time = time.time()
        arguments = parse_command_line()
        configure_logging(arguments)
        ci_mode_enabled = arguments.get('ci_mode')

        process_main(arguments)

        elapsed_time = f"{time.time() - start_time:.2f} sec."
        logging.info(f"Processing is completed, {elapsed_time}")

    except FileNotFoundError as ex:
        exception_occurred = True
        logging.exception(ex)

    except AssertionError:
        exception_occurred = True

    except KeyboardInterrupt:
        exception_occurred = True
        logging.warning('Processing is interrupted')

    except SystemExit:  # NOSONAR
        exception_occurred = True

    except Exception as ex:
        exception_occurred = True
        logging.exception(ex)

    try:
        if not ci_mode_enabled:
            input('Press Enter to continue')
    except (KeyboardInterrupt, UnicodeDecodeError):
        pass
    sys.exit(1 if exception_occurred else 0)


if __name__ == '__main__':
    main()
