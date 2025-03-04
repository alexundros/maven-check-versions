#!/usr/bin/python3
"""This file provides config functions"""

import logging
import os
from pathlib import Path

import yaml


def get_config(arguments: dict) -> dict:
    """
    Get config parser for YAML configuration.

    Args:
        arguments (dict): Command-line arguments.

    Returns:
        dict: Parsed YAML as dict.
    """
    config = {}
    if (config_file := arguments.get('config_file')) is None:
        config_file = 'maven_check_versions.yml'
        if not os.path.exists(config_file):
            config_file = os.path.join(Path.home(), config_file)

    if os.path.exists(config_file):
        logging.info(f"Load Config: {Path(config_file).absolute()}")
        with open(config_file, encoding='utf-8') as f:
            config = yaml.safe_load(f)

    return config


def get_config_value(
        config: dict, arguments: dict, key: str, section: str = 'base', value_type=None
) -> any:
    """
    Get configuration value with optional type conversion.

    Args:
        config (dict): Parsed YAML as dict.
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
            value = config.get(section).get(key)
        if value_type == bool:
            value = str(value).lower() == 'true'
        if value_type == int:
            value = int(value)
        if value_type == float:
            value = float(value)
        return value
    except (AttributeError, KeyError):
        return None


def config_items(config: dict, section: str) -> list[tuple[str, str]]:
    """
    Retrieves all items from a configuration section.

    Args:
        config (dict): Parsed YAML as dict.
        section (str): Section name.

    Returns:
        list[tuple[str, str]]: List of key-value pair tuples.
    """
    try:
        return list(config.get(section).items())
    except (AttributeError, KeyError):
        return []
