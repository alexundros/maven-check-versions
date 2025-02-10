#!/usr/bin/python3
"""This file provides utility functions"""

import configparser
import os
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from configparser import ConfigParser


def get_config_value(
        config_parser: ConfigParser, arguments: dict, key: str, section: str = 'base', value_type=None
) -> any:
    """
    Get configuration value with optional type conversion.

    Args:
        config_parser (ConfigParser): Configuration data.
        arguments (dict): Command line arguments.
        key (str): Configuration section name.
        section (str, optional): Configuration option name. Defaults to None.
        value_type (type, optional): Value type for conversion. Defaults to str.

    Returns:
        Any: Value of the configuration option or None if not found.
    """
    try:
        value = None
        if section == 'base' and key in arguments:
            value = arguments.get(key)
            if 'CV_' + key.upper() in os.environ:
                value = os.environ.get('CV_' + key.upper())
        if value is None:
            value = config_parser.get(section, key)
        if value_type == bool:
            value = str(value).lower() == 'true'
        if value_type == int:
            value = int(value)
        if value_type == float:
            value = float(value)
        return value
    except configparser.Error:
        return None


def get_artifact_name(root_element: ET.Element, ns_mapping: dict) -> str:
    """
    Get the full name of the artifact from the POM file.

    Args:
        root_element (ET.Element): Root element of the POM file.
        ns_mapping (dict): XML namespace mapping.

    Returns:
        str: Full artifact name.
    """
    artifact_id = root_element.find('./xmlns:artifactId', namespaces=ns_mapping).text
    group_id_element = root_element.find('./xmlns:groupId', namespaces=ns_mapping)
    return (group_id_element.text + ':' if group_id_element is not None else '') + artifact_id
