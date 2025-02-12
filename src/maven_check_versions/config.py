#!/usr/bin/python3
"""This file provides config functions"""

import configparser
import logging
import os
from configparser import ConfigParser
from pathlib import Path


def get_config_parser(arguments: dict) -> ConfigParser:
    """
    Get config parser.

    Args:
        arguments (dict): Dictionary of parsed command line arguments.

    Returns:
        ConfigParser: Config parser.
    """
    config_parser = ConfigParser()
    config_parser.optionxform = str
    if (config_file := arguments.get('config_file')) is None:
        config_file = 'maven_check_versions.cfg'
        if not os.path.exists(config_file):
            config_file = os.path.join(Path.home(), config_file)
    if os.path.exists(config_file):
        logging.info(f"Load Config: {Path(config_file).absolute()}")
        config_parser.read_file(open(config_file))
    return config_parser


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


def config_items(config_parser: ConfigParser, section: str) -> list[tuple[str, str]]:
    """
    Retrieve all items from a configuration section.

    Args:
        config_parser (ConfigParser): The configuration parser.
        section (str): The section of the configuration file.

    Returns:
        list[tuple[str, str]]: A list of tuples containing the key-value pairs for the specified section.
    """
    try:
        return config_parser.items(section)
    except configparser.Error:
        return []
