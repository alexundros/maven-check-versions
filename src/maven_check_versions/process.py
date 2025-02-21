#!/usr/bin/python3
"""This file provides process functions"""

import logging
import os
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from configparser import ConfigParser

import maven_check_versions.cache as _cache
import maven_check_versions.config as _config
import maven_check_versions.logutils as _logutils
import maven_check_versions.utils as _utils
import requests
import urllib3
from bs4 import BeautifulSoup


def process_main(arguments: dict) -> None:
    """
    Main processing function.

    Args:
        arguments (dict): Command-line arguments.
    """
    config_parser = _config.get_config_parser(arguments)

    if not _config.get_config_value(config_parser, arguments, 'warnings', 'urllib3', value_type=bool):
        urllib3.disable_warnings()

    cache_disabled = _config.get_config_value(config_parser, arguments, 'cache_off', value_type=bool)
    if (cache_file_path := arguments.get('cache_file')) is None:
        cache_file_path = 'maven_check_versions.cache'
    cache_data = _cache.load_cache(cache_file_path) if not cache_disabled else None

    if pom_file := arguments.get('pom_file'):
        process_pom(cache_data, config_parser, arguments, pom_file)
    elif artifact_to_find := arguments.get('find_artifact'):
        process_artifact(cache_data, config_parser, arguments, artifact_to_find)
    else:
        for key, pom in _config.config_items(config_parser, 'pom_files'):
            process_pom(cache_data, config_parser, arguments, pom)

    if cache_data is not None:
        _cache.save_cache(cache_data, cache_file_path)


def process_pom(
        cache_data: dict | None, config_parser: ConfigParser, arguments: dict, pom_path: str, prefix: str = None
) -> None:
    """
    Processes a POM file.

    Args:
        cache_data (dict | None): Cache data.
        config_parser (ConfigParser): Configuration parser.
        arguments (dict): Command-line arguments.
        pom_path (str): Path or URL to the POM file.
        prefix (str, optional): Prefix for the artifact name.
    """
    verify_ssl = _config.get_config_value(config_parser, arguments, 'verify', 'requests', value_type=bool)

    tree = _utils.get_pom_tree(pom_path, verify_ssl, config_parser, arguments)
    root = tree.getroot()
    ns_mapping = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}  # NOSONAR

    artifact_name = _utils.get_artifact_name(root, ns_mapping)
    if prefix is not None:
        prefix = artifact_name = f"{prefix} / {artifact_name}"
    logging.info(f"=== Processing: {artifact_name} ===")

    dependencies = _utils.collect_dependencies(root, ns_mapping, config_parser, arguments)
    process_dependencies(cache_data, config_parser, arguments, dependencies, ns_mapping, root, verify_ssl)

    process_modules_if_required(cache_data, config_parser, arguments, root, pom_path, ns_mapping, prefix)


def process_dependencies(
        cache_data: dict | None, config_parser: ConfigParser, arguments: dict, dependencies: list,
        ns_mapping: dict, root: ET.Element, verify_ssl: bool
) -> None:
    """
    Processes dependencies in a POM file.

    Args:
        cache_data (dict | None): Cache data.
        config_parser (ConfigParser): Configuration parser.
        arguments (dict): Command-line arguments.
        dependencies (list): List of dependencies.
        ns_mapping (dict): XML namespace mapping.
        root (ET.Element): Root element of the POM file.
        verify_ssl (bool): SSL verification flag.
    """
    for dependency in dependencies:
        artifact_id, group_id = _utils.get_dependency_identifiers(dependency, ns_mapping)
        if artifact_id is None or group_id is None:
            logging.error("Missing artifactId or groupId in a dependency.")
            continue

        version, skip_flag = _utils.get_version(config_parser, arguments, ns_mapping, root, dependency)
        if skip_flag is True:
            _logutils.log_skip_if_required(config_parser, arguments, group_id, artifact_id, version)
            continue

        _logutils.log_search_if_required(config_parser, arguments, group_id, artifact_id, version)

        if cache_data is not None and cache_data.get(f"{group_id}:{artifact_id}") is not None:
            if _cache.process_cache(arguments, cache_data, config_parser, artifact_id, group_id, version):
                continue

        if not process_repositories(artifact_id, cache_data, config_parser, group_id, arguments, verify_ssl, version):
            logging.warning(f"Not Found: {group_id}:{artifact_id}, current:{version}")


def process_repositories(
        artifact_id: str, cache_data: dict | None, config_parser: ConfigParser, group_id: str,
        arguments: dict, verify_ssl: bool, version: str
):
    """
    Processes repositories to find a dependency.

    Args:
        artifact_id (str): Artifact ID.
        cache_data (dict | None): Cache data.
        config_parser (ConfigParser): Configuration parser.
        group_id (str): Group ID.
        arguments (dict): Command-line arguments.
        verify_ssl (bool): SSL verification flag.
        version (str): Dependency version.

    Returns:
        bool: True if the dependency is found, False otherwise.
    """
    if len(items := _config.config_items(config_parser, 'repositories')):
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
    Processes modules in a POM file if required.

    Args:
        cache_data (dict | None): Cache data.
        config_parser (ConfigParser): Configuration parser.
        arguments (dict): Command-line arguments.
        root (ET.Element): Root element of the POM file.
        pom_path (str): Path to the POM file.
        ns_mapping (dict): XML namespace mapping.
        prefix (str, optional): Prefix for the artifact name.
    """
    if _config.get_config_value(config_parser, arguments, 'process_modules', value_type=bool):
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
    Processes the search for a specified artifact.

    Args:
        cache_data (dict | None): Cache data.
        config_parser (ConfigParser): Configuration parser.
        arguments (dict): Command-line arguments.
        artifact_to_find (str): Artifact to search for in groupId:artifactId:version format.
    """
    verify_ssl = _config.get_config_value(config_parser, arguments, 'verify', 'requests', value_type=bool)
    group_id, artifact_id, version = artifact_to_find.split(sep=":", maxsplit=3)

    _logutils.log_search_if_required(config_parser, arguments, group_id, artifact_id, version)

    dependency_found = False
    for section_key, repository_section in _config.config_items(config_parser, 'repositories'):
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
    Processes a repository section.

    Args:
        cache_data (dict | None): Cache data.
        config_parser (ConfigParser): Configuration parser.
        arguments (dict): Command-line arguments.
        group_id (str): Group ID.
        artifact_id (str): Artifact ID.
        version (str): Artifact version.
        section_key (str): Repository section key.
        repository_section (str): Repository section name.
        verify_ssl (bool): SSL verification flag.

    Returns:
        bool: True if the dependency is found, False otherwise.
    """
    auth_info = ()
    if _config.get_config_value(config_parser, arguments, 'auth', repository_section, value_type=bool):
        auth_info = (
            _config.get_config_value(config_parser, arguments, 'user'),
            _config.get_config_value(config_parser, arguments, 'password')
        )

    base_url = _config.get_config_value(config_parser, arguments, 'base', repository_section)
    path_suffix = _config.get_config_value(config_parser, arguments, 'path', repository_section)
    repository_name = _config.get_config_value(config_parser, arguments, 'repo', repository_section)

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

        if _utils.check_versions(
                cache_data, config_parser, arguments, group_id, artifact_id, version, section_key,
                path, auth_info, verify_ssl, available_versions, response):
            return True

    if _config.get_config_value(config_parser, arguments, 'service_rest', repository_section, value_type=bool):
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
    Processes REST services for a repository.

    Args:
        cache_data (dict | None): Cache data.
        config_parser (ConfigParser): Configuration parser.
        arguments (dict): Command-line arguments.
        group_id (str): Group ID.
        artifact_id (str): Artifact ID.
        version (str): Artifact version.
        section_key (str): Repository section key.
        repository_section (str): Repository section name.
        base_url (str): Base URL of the repository.
        auth_info (tuple): Authentication credentials.
        verify_ssl (bool): SSL verification flag.

    Returns:
        bool: True if the dependency is found, False otherwise.
    """
    repository_name = _config.get_config_value(config_parser, arguments, 'repo', repository_section)
    path = f"{base_url}/service/rest/repository/browse/{repository_name}"
    path = f"{path}/{group_id.replace('.', '/')}/{artifact_id}"

    metadata_url = path + '/maven-metadata.xml'
    response = requests.get(metadata_url, auth=auth_info, verify=verify_ssl)

    if response.status_code == 200:
        tree = ET.ElementTree(ET.fromstring(response.text))
        version_elements = tree.getroot().findall('.//version')
        available_versions = list(map(lambda v: v.text, version_elements))

        if _utils.check_versions(
                cache_data, config_parser, arguments, group_id, artifact_id, version,
                section_key, path, auth_info, verify_ssl, available_versions, response):
            return True

    response = requests.get(path + '/', auth=auth_info, verify=verify_ssl)

    if response.status_code == 200:
        html_content = BeautifulSoup(response.text, 'html.parser')
        version_links = html_content.find('table').find_all('a')
        available_versions = list(map(lambda v: v.text, version_links))
        path = f"{base_url}/repository/{repository_name}/{group_id.replace('.', '/')}/{artifact_id}"

        if _utils.check_versions(
                cache_data, config_parser, arguments, group_id, artifact_id, version,
                section_key, path, auth_info, verify_ssl, available_versions, response):
            return True

    return False
