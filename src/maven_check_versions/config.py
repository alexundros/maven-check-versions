#!/usr/bin/python3
"""This file provides config functions"""

import configparser
import logging
import os
from configparser import ConfigParser
from pathlib import Path


def get_config_parser(arguments: dict) -> ConfigParser:
    """
    Creates and configures a configuration parser.

    Args:
        arguments (dict): Command-line arguments.

    Returns:
        ConfigParser: Configured configuration parser.
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
    Retrieves a configuration value with optional type conversion.

    Args:
        config_parser (ConfigParser): Configuration parser.
        arguments (dict): Command-line arguments.
        key (str): Configuration key.
        section (str, optional): Configuration section (default is 'base').
        value_type (type, optional): Type for value conversion.

    Returns:
        any: Configuration value or None if not found.
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
    Retrieves all items from a configuration section.

    Args:
        config_parser (ConfigParser): Configuration parser.
        section (str): Section name.

    Returns:
        list[tuple[str, str]]: List of key-value pair tuples.
    """
    try:
        return config_parser.items(section)
    except configparser.Error:
        return []
