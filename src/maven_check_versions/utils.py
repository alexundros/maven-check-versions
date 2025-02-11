#!/usr/bin/python3
"""This file provides utility functions"""

# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from argparse import ArgumentParser
from configparser import ConfigParser

from .config import get_config_value


def parse_command_line() -> dict:
    """
    Parse command line arguments.

    Returns:
        dict: A dictionary containing parsed command line arguments.
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
    return vars(argument_parser.parse_args())


def get_artifact_name(root: ET.Element, ns_mapping: dict) -> str:
    """
    Get the full name of the artifact from the POM file.

    Args:
        root (ET.Element): Root element of the POM file.
        ns_mapping (dict): XML namespace mapping.

    Returns:
        str: Full artifact name.
    """
    artifact_id = root.find('./xmlns:artifactId', namespaces=ns_mapping).text
    group_id_element = root.find('./xmlns:groupId', namespaces=ns_mapping)
    return (group_id_element.text + ':' if group_id_element is not None else '') + artifact_id


def collect_dependencies(
        root: ET.Element, ns_mapping: dict, config_parser: ConfigParser, arguments: dict
) -> list:
    """
    Collect dependencies from the POM file.

    Args:
        root (ET.Element): Root element of the POM file.
        ns_mapping (dict): XML namespace mapping.
        config_parser (ConfigParser): Configuration data.
        arguments (dict): Command line arguments.

    Returns:
        list: List of dependencies from the POM file.
    """
    dependencies = root.findall('.//xmlns:dependency', namespaces=ns_mapping)
    if get_config_value(config_parser, arguments, 'search_plugins', value_type=bool):
        plugin_xpath = './/xmlns:plugins/xmlns:plugin'
        plugins = root.findall(plugin_xpath, namespaces=ns_mapping)
        dependencies.extend(plugins)
    return dependencies


def get_dependency_identifiers(dependency: ET.Element, ns_mapping: dict) -> tuple[str, str | None]:
    """
    Extract artifactId and groupId from a dependency.

    Args:
        dependency (ET.Element): Dependency element.
        ns_mapping (dict): XML namespace mapping.

    Returns:
        tuple[str, str | None]: artifactId and groupId (if present).
    """
    artifact_id = dependency.find('xmlns:artifactId', namespaces=ns_mapping)
    group_id = dependency.find('xmlns:groupId', namespaces=ns_mapping)
    return None if artifact_id is None else artifact_id.text, None if group_id is None else group_id.text
