#!/usr/bin/python3
"""This file provides config functions"""

import configparser
import logging
import os
from configparser import ConfigParser
from pathlib import Path

import yaml


def get_config(arguments: dict) -> dict | ConfigParser:
    """
    Get config parser for YAML or INI configuration.

    Args:
        arguments (dict): Command-line arguments.

    Returns:
        dict | ConfigParser: Parsed YAML as dict or INI as ConfigParser.
    """
    config = ConfigParser()
    config.optionxform = str
    if (config_file := arguments.get('config_file')) is None:
        config_file = file_yml = 'maven_check_versions.yml'
        file_cfg = 'maven_check_versions.cfg'
        if not os.path.exists(config_file):
            config_file = file_cfg
        if not os.path.exists(config_file):
            config_file = os.path.join(Path.home(), file_yml)
            if not os.path.exists(config_file):
                config_file = os.path.join(Path.home(), file_cfg)

    if os.path.exists(config_file):
        logging.info(f"Load Config: {Path(config_file).absolute()}")
        if config_file.endswith('.yml'):
            with open(config_file, encoding='utf-8') as f:
                config = yaml.safe_load(f)
        else:
            config.read_file(open(config_file))

    return config


def get_config_value(
        config: dict | ConfigParser, arguments: dict, key: str, section: str = 'base', value_type=None
) -> any:
    """
    Get configuration value with optional type conversion.

    Args:
        config (dict | ConfigParser): Parsed YAML as dict or INI as ConfigParser.
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
            if isinstance(config, dict):
                value = config.get(section).get(key)
            else:  # ConfigParser
                value = config.get(section, key)
        if value_type == bool:
            value = str(value).lower() == 'true'
        if value_type == int:
            value = int(value)
        if value_type == float:
            value = float(value)
        return value
    except (AttributeError, KeyError, configparser.Error):
        return None


def config_items(config: dict | ConfigParser, section: str) -> list[tuple[str, str]]:
    """
    Retrieves all items from a configuration section.

    Args:
        config (dict | ConfigParser): Parsed YAML as dict or INI as ConfigParser.
        section (str): Section name.

    Returns:
        list[tuple[str, str]]: List of key-value pair tuples.
    """
    try:
        if isinstance(config, dict):
            return list(config.get(section).items())
        else:  # ConfigParser
            return config.items(section)
    except (AttributeError, KeyError, configparser.Error):
        return []
