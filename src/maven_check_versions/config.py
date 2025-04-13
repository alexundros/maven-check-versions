#!/usr/bin/python3
"""This file provides config functions"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml


class Config(dict):
    """Wrapper for Config"""
    pass


class Arguments(dict):
    """Wrapper for Arguments"""
    pass


def get_config(arguments: Arguments) -> Config:
    """
    Loads the configuration from a YAML file specified in the arguments or a default location.

    Args:
        arguments (Arguments): Command-line arguments.

    Returns:
        Config: A Config object (dictionary) containing the parsed YAML configuration.
                If no config file is found, returns an empty Config object.
    """
    config = Config()
    if (config_file := arguments.get('config_file')) is None:
        config_file = 'maven_check_versions.yml'
        if not os.path.exists(config_file):
            config_file = os.path.join(Path.home(), config_file)

    if os.path.exists(config_file):
        logging.info(f"Load Config: {Path(config_file).absolute()}")
        try:
            with open(config_file, encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:  # pragma: no cover
            logging.error(f"Failed to get_config: {e}")

    return config


def get_config_value(
        config: Config, arguments: Arguments, key: str, section: str = 'base', default: Any = None
) -> Any:
    """
    Retrieves a configuration value from command-line arguments or the config dictionary,
    with a fallback to a default value.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        key (str): Configuration key.
        section (str, optional): Configuration section to use (default is 'base').
        default (Any, optional): Default value if the key is not found (default is None).

    Returns:
        Any: The value associated with the key, sourced from arguments, environment variables,
            or the config dictionary, or the default value if not found.
    """
    value = None
    if section == 'base' and key in arguments:
        value = arguments.get(key)
    if value is None:
        inner = '' if section == 'base' else section.upper() + '_'
        env = 'CV_' + inner + key.upper()
        if env in os.environ and (value := os.environ.get(env)) is not None:
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
    if value is None and section in config and (get := config.get(section)):
        value = get.get(key)
    return default if value is None else value


def config_items(config: Config, section: str) -> list[tuple[str, str]]:
    """
    Retrieves all key-value pairs from a specified configuration section.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        section (str): The name of the configuration section (e.g., 'repositories').

    Returns:
        list[tuple[str, str]]: A list of tuples, each containing a key and its value from the section.
                            Returns an empty list if the section does not exist.
    """
    return list(get.items()) if (get := config.get(section)) else []
