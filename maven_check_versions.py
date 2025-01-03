#!/usr/bin/python3
"""This script processes Maven POM files and checks for dependencies versions"""

import configparser
import datetime
import json
import logging
import math
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from argparse import ArgumentParser
from configparser import ConfigParser
from pathlib import Path, PurePath

# Modules from PACKAGES Env or local packages
local_package_dir = os.path.dirname(__file__)
site_packages_path = os.path.join(local_package_dir, '.site-packages')
sys.path.append(site_packages_path)
if packages_env := os.getenv('PACKAGES'):
    sys.path.append(packages_env)
    if not os.path.exists(packages_env):
        print('Invalid PACKAGES environment')
        sys.exit(1)

import dateutil.parser as parser
import requests
import urllib3
from bs4 import BeautifulSoup


def parse_command_line_arguments() -> dict:
    """
    Parse command line arguments.

    Returns:
        dict: A dictionary containing parsed command line arguments.
    """
    argument_parser = ArgumentParser()
    argument_parser.add_argument('-ci', '--ci_mode', help='CI Mode', action='store_true')
    argument_parser.add_argument('-pf', '--pom_file', help='POM File')
    argument_parser.add_argument('-fa', '--find_artifact', help='Find artifact')
    # override config
    argument_parser.add_argument('-co', '--cache_off', help='Dont use Cache', action='store_true')
    argument_parser.add_argument('-lfo', '--logfile_off', help='Dont use Log file', action='store_true')
    argument_parser.add_argument('-cf', '--config_file', help='Config File')
    argument_parser.add_argument('-fm', '--fail_mode', help='Fail Mode', action='store_true')
    argument_parser.add_argument('-mjv', '--fail_major', help='Fail Major delta')
    argument_parser.add_argument('-mnv', '--fail_minor', help='Fail Minor delta')
    argument_parser.add_argument('-sp', '--search_plugins', help='Search plugins', action='store_true')
    argument_parser.add_argument('-sm', '--process_modules', help='Process modules', action='store_true')
    argument_parser.add_argument('-sk', '--show_skip', help='Show Skip', action='store_true')
    argument_parser.add_argument('-ss', '--show_search', help='Show Search', action='store_true')
    argument_parser.add_argument('-ev', '--empty_version', help='Empty Version', action='store_true')
    argument_parser.add_argument('-si', '--show_invalid', help='Show Invalid', action='store_true')
    argument_parser.add_argument('-un', '--user', help='Basic Auth user')
    argument_parser.add_argument('-up', '--password', help='Basic Auth password')
    return vars(argument_parser.parse_args())


def main_process(parsed_arguments: dict) -> None:
    """
    Main processing function.

    Args:
        parsed_arguments (dict): Dictionary of parsed command line arguments.
    """
    os.chdir(os.path.dirname(__file__))

    config = ConfigParser()
    config.optionxform = str
    if (config_file := parsed_arguments.get('config_file')) is None:
        config_file = Path(__file__).stem + '.cfg'
    if os.path.exists(config_file):
        config.read(config_file)

    if not get_config_value(config, parsed_arguments, 'warnings', 'urllib3', vt=bool):
        urllib3.disable_warnings()

    cache_disabled = get_config_value(config, parsed_arguments, 'cache_off')
    cache_file_path = Path(__file__).stem + '.cache'
    cache_data = load_cache(cache_file_path) if not cache_disabled else None

    if pom_file := parsed_arguments.get('pom_file'):
        process_pom(cache_data, config, parsed_arguments, pom_file)
    elif artifact_to_find := parsed_arguments.get('find_artifact'):
        find_artifact(cache_data, config, parsed_arguments, artifact_to_find)
    else:
        for key, pom in config_items(config, 'pom_file'):
            process_pom(cache_data, config, parsed_arguments, pom)

    if cache_data is not None:
        save_cache(cache_data, cache_file_path)


def load_cache(cache_file: str) -> dict:
    """
    Load cache from a file.

    Args:
        cache_file (str): Path to the cache file.

    Returns:
        dict: A dictionary representing the loaded cache.
    """
    if os.path.exists(cache_file):
        logging.info(f"Load Cache: {PurePath(cache_file).name}")
        with open(cache_file, 'r') as cf:
            return json.load(cf)
    return {}


def save_cache(cache_data: dict, cache_file: str) -> None:
    """
    Save cache to a file.

    Args:
        cache_data (dict): The cache data to be saved.
        cache_file (str): Path to the file where the cache will be saved.
    """
    if cache_data is not None:
        logging.info(f"Save Cache: {PurePath(cache_file).name}")
        with open(cache_file, 'w') as cf:
            json.dump(cache_data, cf)


def process_pom(cache_data: dict, config: ConfigParser, parsed_arguments: dict, pom_path: str,
                prefix: str = None) -> None:
    """
    Process POM files.

    Args:
        cache_data (dict): Cache data for dependencies.
        config (ConfigParser): Configuration data.
        parsed_arguments (dict): Command line arguments.
        pom_path (str): Path or URL to the POM file to process.
        prefix (str, optional): Prefix for the artifact name. Defaults to None.
    """
    verify_ssl = get_config_value(config, parsed_arguments, 'verify', 'requests', vt=bool)

    if pom_path.startswith('http'):
        auth_info = ()
        if get_config_value(config, parsed_arguments, 'auth', 'pom_http', vt=bool):
            username = get_config_value(config, parsed_arguments, 'user')
            password = get_config_value(config, parsed_arguments, 'password')
            auth_info = (username, password)

        response = requests.get(pom_path, auth=auth_info, verify=verify_ssl)

        if response.status_code != 200:
            raise FileNotFoundError(f'{pom_path} not found')
        tree = ET.ElementTree(ET.fromstring(response.text))
    else:
        if not os.path.exists(pom_path):
            raise FileNotFoundError(f'{pom_path} not found')
        tree = ET.parse(pom_path)

    root_element = tree.getroot()
    namespace_mapping = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}

    artifact_id = root_element.find('./xmlns:artifactId', namespaces=namespace_mapping).text
    group_id_element = root_element.find('./xmlns:groupId', namespaces=namespace_mapping)
    full_artifact_name = (group_id_element.text + ':' if group_id_element is not None else '') + artifact_id
    if prefix is not None:
        full_artifact_name = f"{prefix} / {full_artifact_name}"

    logging.info(f"=== Processing: {full_artifact_name} ===")

    dependencies = root_element.findall('.//xmlns:dependency', namespaces=namespace_mapping)

    if get_config_value(config, parsed_arguments, 'search_plugins', vt=bool):
        plugin_xpath = './/xmlns:plugins/xmlns:plugin'
        plugins = root_element.findall(plugin_xpath, namespaces=namespace_mapping)
        dependencies.extend(plugins)

    process_dependencies(
        cache_data, config, parsed_arguments, dependencies, namespace_mapping, root_element, verify_ssl)

    if get_config_value(config, parsed_arguments, 'process_modules', vt=bool):
        directory_path = os.path.dirname(pom_path)
        module_xpath = './/xmlns:modules/xmlns:module'

        for module in root_element.findall(module_xpath, namespaces=namespace_mapping):
            module_pom_path = f"{directory_path}/{module.text}/pom.xml"
            if os.path.exists(module_pom_path):
                process_pom(cache_data, config, parsed_arguments, module_pom_path, full_artifact_name)


def process_dependencies(
        cache_data: dict, config: ConfigParser, parsed_arguments: dict, dependencies: list,
        namespace_mapping: dict, root_element: ET.Element, verify_ssl: bool) -> None:
    """
    Process dependencies in a POM file.

    Args:
        cache_data (dict): Cache object to store dependencies.
        config (ConfigParser): Configuration object.
        parsed_arguments (dict): Command-line arguments.
        dependencies (list): List of dependencies from the POM file.
        namespace_mapping (dict): XML namespace mapping.
        root_element (ET.Element): Root XML element of the POM file.
        verify_ssl (bool): Whether to verify HTTPS certificates.
    """
    for dependency in dependencies:
        artifact_id = dependency.find('xmlns:artifactId', namespaces=namespace_mapping)
        if artifact_id is None:
            continue
        artifact_id_text = artifact_id.text

        group_id = dependency.find('xmlns:groupId', namespaces=namespace_mapping)
        if group_id is None:
            logging.error(f"Empty groupId in {artifact_id_text}")
            continue
        group_id_text = group_id.text

        version, skip_flag = get_version(
            config, parsed_arguments, group_id_text, artifact_id_text, namespace_mapping, root_element, dependency)

        if skip_flag is True:
            if get_config_value(config, parsed_arguments, 'show_skip', vt=bool):
                logging.warning(f"Skip: {group_id_text}:{artifact_id_text}:{version}")
            continue

        if get_config_value(config, parsed_arguments, 'show_search', vt=bool):
            if version is None or re.match('^\\${([^}]+)}$', version):
                logging.warning(f"Search: {group_id_text}:{artifact_id_text}:{version}")
            else:
                logging.info(f"Search: {group_id_text}:{artifact_id_text}:{version}")

        if (cache_data is not None and
                cache_data.get(f"{group_id_text}:{artifact_id_text}") is not None):

            cached_time, cached_version, cached_key, cached_date, cached_versions = cache_data.get(
                f"{group_id_text}:{artifact_id_text}")
            if cached_version == version:
                continue

            cache_time_threshold = get_config_value(config, parsed_arguments, 'cache_time', vt=int)

            if cache_time_threshold == 0 or time.time() - cached_time < cache_time_threshold:
                message_format = '*{}: {}:{}, current:{} versions: {} updated: {}'
                formatted_date = cached_date if cached_date is not None else ''
                logging.info(message_format.format(
                    cached_key, group_id_text, artifact_id_text, version,
                    ', '.join(cached_versions), formatted_date).rstrip())
                continue

        dependency_found = False
        for section_key, repository_section in config_items(config, 'repositories'):
            if (dependency_found :=
            process_repository(*(
                    cache_data, config, parsed_arguments, group_id_text, artifact_id_text, version,
                    section_key, repository_section, verify_ssl))):
                break
        if not dependency_found:
            logging.warning(f"Not Found: {group_id_text}:{artifact_id_text}, current:{version}")


def find_artifact(cache_data: dict, config: ConfigParser, parsed_arguments: dict, artifact_to_find: str) -> None:
    """
    Process finding artifacts.

    Args:
        cache_data (dict): Cache data.
        config (ConfigParser): Configuration settings.
        parsed_arguments (dict): Command-line arguments.
        artifact_to_find (str): Artifact to search for.
    """
    verify_ssl = get_config_value(config, parsed_arguments, 'verify', 'requests', vt=bool)
    group_id, artifact_id, version = artifact_to_find.split(sep=":", maxsplit=3)

    if get_config_value(config, parsed_arguments, 'show_search', vt=bool):
        logging.info(f"Search: {group_id}:{artifact_id}:{version}")

    dependency_found = False
    for section_key, repository_section in config_items(config, 'repositories'):
        if (dependency_found :=
        process_repository(*(
                cache_data, config, parsed_arguments, group_id, artifact_id, version,
                section_key, repository_section, verify_ssl))):
            break
    if not dependency_found:
        logging.warning(f"Not Found: {group_id}:{artifact_id}, current:{version}")


def get_version(config: ConfigParser, parsed_arguments: dict, group_id: str, artifact_id: str, namespace_mapping: dict,
                root_element: ET.Element, dependency: ET.Element) -> tuple[str | None, bool]:
    """
    Get version information.

    Args:
        config (ConfigParser): The configuration parser.
        parsed_arguments (dict): Dictionary containing the parsed command line arguments.
        group_id (str): The group ID of the artifact.
        artifact_id (str): The artifact ID.
        namespace_mapping (dict): Namespace dictionary for XML parsing.
        root_element (ET.Element): Root element of the POM file.
        dependency (ET.Element): Dependency element from which to extract version.

    Returns:
        tuple[str | None, bool]: A tuple containing the resolved version and a boolean indicating if the version should be skipped.
    """
    version_element = dependency.find('xmlns:version', namespaces=namespace_mapping)

    if version_element is None:
        if not get_config_value(config, parsed_arguments, 'empty_version', vt=bool):
            return None, True
    else:
        version_text = version_element.text
        variable_expression = '^\\${([^}]+)}$'

        if match := re.search(variable_expression, version_text):
            property_xpath = f"./xmlns:properties/xmlns:{match.group(1)}"
            found_property = root_element.find(property_xpath, namespaces=namespace_mapping)
            if found_property is not None:
                version_text = found_property.text

        if version_text == '${project.version}':
            project_version_element = root_element.find('xmlns:version', namespaces=namespace_mapping).text
            if match := re.search(variable_expression, project_version_element):
                property_xpath = f"./xmlns:properties/xmlns:{match.group(1)}"
                found_property = root_element.find(property_xpath, namespaces=namespace_mapping)
                if found_property is not None:
                    project_version_element = found_property.text
            version_text = project_version_element

        if re.match(variable_expression, version_text):
            if not get_config_value(config, parsed_arguments, 'empty_version', vt=bool):
                return version_text, True

    return version_text, False


def process_repository(
        cache_data: dict, config: ConfigParser, parsed_arguments: dict, group_id: str, artifact_id: str,
        version: str, section_key: str, repository_section: str, verify_ssl: bool) -> bool:
    """
    Process a repository section.

    Args:
        cache_data (dict): The cache dictionary.
        config (ConfigParser): The configuration parser.
        parsed_arguments (dict): Dictionary containing the parsed command line arguments.
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
    if get_config_value(config, parsed_arguments, 'auth', repository_section, vt=bool):
        auth_info = (
            get_config_value(config, parsed_arguments, 'user'),
            get_config_value(config, parsed_arguments, 'password')
        )

    base_url = get_config_value(config, parsed_arguments, 'base', repository_section)
    path_suffix = get_config_value(config, parsed_arguments, 'path', repository_section)
    repository_name = get_config_value(config, parsed_arguments, 'repo', repository_section)

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

        if check_versions(*(cache_data, config, parsed_arguments, group_id, artifact_id, version, section_key,
                            path, auth_info, verify_ssl, available_versions, response)):
            return True

    if get_config_value(config, parsed_arguments, 'service_rest', repository_section, vt=bool):
        return service_rest(*(
            cache_data, config, parsed_arguments, group_id, artifact_id, version, section_key,
            repository_section, base_url, auth_info, verify_ssl))

    return False


def check_versions(
        cache_data: dict, config: ConfigParser, parsed_arguments: dict, group_id: str, artifact_id: str, version: str,
        section_key: str,
        path: str, auth_info: tuple, verify_ssl: bool, available_versions: list[str],
        response: requests.Response) -> bool:
    """
    Check versions.

    Args:
        cache_data (dict): The cache dictionary.
        config (ConfigParser): The configuration parser.
        parsed_arguments (dict): Dictionary containing the parsed command line arguments.
        group_id (str): The group ID of the artifact.
        artifact_id (str): The artifact ID.
        version (str): The version of the artifact.
        section_key (str): The key for the repository section.
        path (str): The path to the dependency in the repository.
        auth_info (tuple): Tuple containing basic authentication credentials.
        verify_ssl (bool): Whether to verify SSL certificates.
        available_versions (list[str]): List of available versions.
        response (requests.Response): The response object from the repository.

    Returns:
        bool: True if the current version is valid, False otherwise.
    """
    available_versions = list(filter(lambda v: re.match('^\\d+.+', v), available_versions))
    latest_version = available_versions[-1]
    available_versions.reverse()

    if available_versions[0] != latest_version:
        logging.warning(f"Last versions: {available_versions[:5]}")

    major_version_threshold = 0
    minor_version_threshold = 0
    current_major_version = 0
    current_minor_version = 0
    if get_config_value(config, parsed_arguments, 'fail_mode', vt=bool):
        major_version_threshold = int(get_config_value(config, parsed_arguments, 'fail_major'))
        minor_version_threshold = int(get_config_value(config, parsed_arguments, 'fail_minor'))

        if version_match := re.match('^(\\d+).(\\d+).+', version):
            current_major_version, current_minor_version = int(version_match.group(1)), int(version_match.group(2))

    skip_current_version = get_config_value(config, parsed_arguments, 'skip_current', vt=bool)
    invalid_flag = False

    for item in available_versions:
        if item == version and skip_current_version:
            if cache_data is not None:
                timestamp = math.trunc(time.time())
                cache_data[f"{group_id}:{artifact_id}"] = (timestamp, item, section_key, None, available_versions[:3])
            return True

        is_valid, last_modified_date = pom_data(auth_info, verify_ssl, artifact_id, item, path)
        if is_valid:
            message_format = '{}: {}:{}, current:{} {} {}'
            logging.info(message_format.format(
                section_key, group_id, artifact_id, version, available_versions[:3],
                last_modified_date).rstrip())

            if cache_data is not None:
                timestamp = math.trunc(time.time())
                cache_data[f"{group_id}:{artifact_id}"] = (
                    timestamp, item, section_key, last_modified_date, available_versions[:3])

            if get_config_value(config, parsed_arguments, 'fail_mode', vt=bool):
                item_major_version = 0
                item_minor_version = 0
                if item_match := re.match('^(\\d+).(\\d+).+', item):
                    item_major_version, item_minor_version = int(item_match.group(1)), int(item_match.group(2))

                if item_major_version - current_major_version > major_version_threshold or \
                        item_minor_version - current_minor_version > minor_version_threshold:
                    logging.warning(f"Fail version: {item} > {version}")
                    raise AssertionError
            return True

        else:
            if get_config_value(config, parsed_arguments, 'show_invalid', vt=bool):
                if not invalid_flag:
                    logging.info(response.url)
                logging.warning(f"Invalid: {group_id}:{artifact_id}:{item}")
            invalid_flag = True

    return False


def service_rest(
        cache_data: dict, config: ConfigParser, parsed_arguments: dict, group_id: str, artifact_id: str, version: str,
        section_key: str,
        repository_section: str, base_url: str, auth_info: tuple, verify_ssl: bool) -> bool:
    """
    Process REST services.

    Args:
        cache_data (dict): The cache dictionary.
        config (ConfigParser): The configuration parser.
        parsed_arguments (dict): Dictionary containing the parsed command line arguments.
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
    repository_name = get_config_value(config, parsed_arguments, 'repo', repository_section)
    path = f"{base_url}/service/rest/repository/browse/{repository_name}"
    path = f"{path}/{group_id.replace('.', '/')}/{artifact_id}"

    metadata_url = path + '/maven-metadata.xml'
    response = requests.get(metadata_url, auth=auth_info, verify=verify_ssl)

    if response.status_code == 200:
        tree = ET.ElementTree(ET.fromstring(response.text))
        version_elements = tree.getroot().findall('.//version')
        available_versions = list(map(lambda v: v.text, version_elements))

        if check_versions(*(cache_data, config, parsed_arguments, group_id, artifact_id, version, section_key,
                            path, auth_info, verify_ssl, available_versions, response)):
            return True

    response = requests.get(path + '/', auth=auth_info, verify=verify_ssl)

    if response.status_code == 200:
        html_content = BeautifulSoup(response.text, 'html.parser')
        version_links = html_content.find('table').find_all('a')
        available_versions = list(map(lambda v: v.text, version_links))
        path = f"{base_url}/repository/{repository_name}/{group_id.replace('.', '/')}/{artifact_id}"

        if check_versions(*(cache_data, config, parsed_arguments, group_id, artifact_id, version, section_key,
                            path, auth_info, verify_ssl, available_versions, response)):
            return True

    return False


def pom_data(auth_info: tuple, verify_ssl: bool, artifact_id: str, version: str, path: str) -> tuple[bool, str | None]:
    """
    Get POM data.

    Args:
        auth_info (tuple): Tuple containing basic authentication credentials.
        verify_ssl (bool): Whether to verify SSL certificates.
        artifact_id (str): The artifact ID.
        version (str): The version of the artifact.
        path (str): The path to the dependency in the repository.

    Returns:
        tuple[bool, str | None]: A tuple containing a boolean indicating if the data was retrieved successfully and the date of the last modification.
    """
    url = f"{path}/{version}/{artifact_id}-{version}.pom"
    response = requests.get(url, auth=auth_info, verify=verify_ssl)

    if response.status_code == 200:
        last_modified_header = response.headers.get('Last-Modified')
        return True, parser.parse(last_modified_header).date().isoformat()

    return False, None


def get_config_value(
        config: ConfigParser, parsed_arguments: dict, key: str, section: str = 'base', value_type=None
) -> any | None:
    """
    Get configuration value with optional type conversion.

    Args:
        config (ConfigParser): Configuration data.
        parsed_arguments (dict): Command line arguments.
        section (str): Configuration section name.
        option (str, optional): Configuration option name. Defaults to None.
        value_type (type, optional): Value type for conversion. Defaults to str.

    Returns:
        Any: Value of the configuration option or None if not found.
    """
    try:
        if section == 'base' and key in parsed_arguments:
            if value := parsed_arguments.get(key):
                return value

            env_key = 'CV_' + key.upper()
            if (env_value := os.environ.get(env_key)):
                return env_value

        value = config.get(section, key)

        if value_type == bool:
            return value.lower() == 'true'
        if value_type == int:
            return int(value)
        if value_type == float:
            return float(value)

        return value
    except configparser.Error:
        return None


def config_items(config: ConfigParser, section: str) -> list[tuple[str, str]]:
    """
    Retrieve all items from a configuration section.

    Args:
        config (ConfigParser): The configuration parser.
        section (str): The section of the configuration file.

    Returns:
        list[tuple[str, str]]: A list of tuples containing the key-value pairs for the specified section.
    """
    try:
        return config.items(section)
    except configparser.Error:
        return []


def configure_logging(parsed_arguments: dict) -> None:
    """
    Configure logging.

    Args:
        parsed_arguments (dict): Dictionary containing the parsed command line arguments.
    """
    handlers = [logging.StreamHandler(sys.stdout)]

    if not parsed_arguments.get('logfile_off'):
        log_directory = os.path.dirname(__file__)
        log_file_path = os.path.join(log_directory, Path(__file__).stem + '.log')
        handlers.append(logging.FileHandler(log_file_path, 'w'))

    logging.Formatter.formatTime = lambda self, record, fmt=None: \
        datetime.datetime.fromtimestamp(record.created)

    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers,
        format='%(asctime)s %(levelname)s: %(message)s'
    )


def main() -> None:
    exception_occurred = False
    ci_mode_enabled = False

    try:
        start_time = time.time()
        parsed_arguments = parse_command_line_arguments()
        configure_logging(parsed_arguments)
        ci_mode_enabled = parsed_arguments.get('ci_mode')

        main_process(parsed_arguments)

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
    except KeyboardInterrupt:
        pass
    except UnicodeDecodeError:
        pass
    sys.exit(1 if exception_occurred else 0)


if __name__ == '__main__':
    main()
