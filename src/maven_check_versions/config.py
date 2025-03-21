#!/usr/bin/python3
"""This file provides config functions"""

import logging
import os
from pathlib import Path
from typing import Dict, Any

import yaml


class Config(Dict):
    """Wrapper for Config"""
    pass


class Arguments(Dict):
    """Wrapper for Arguments"""
    pass


def get_config(arguments: Arguments) -> Config:
    """
    Get config parser for YAML configuration.

    Args:
        arguments (Arguments): Command-line arguments.

    Returns:
        dict: Parsed YAML as dict.
    """
    config = Config()
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
        config: Config, arguments: Arguments, key: str, section: str = 'base', default: Any = None
) -> Any:
    """
    Get configuration value with optional type conversion.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        key (str): Configuration key.
        section (str, optional): Configuration section (default is 'base').
        default (Any, optional): Default value.

    Returns:
        Any: Configuration value or None if not found.
    """
    value = None
    if section == 'base' and key in arguments:
        value = arguments.get(key)
        env_key = 'CV_' + key.upper()
        if env_key in os.environ and (get := os.environ.get(env_key)):
            if get.lower() == 'true':
                value = True
            elif get.lower() == 'false':
                value = False
    if value is None and section in config and (get := config.get(section)):
        value = get.get(key)
    return default if value is None else value


def config_items(config: Config, section: str) -> list[tuple[str, str]]:
    """
    Retrieves all items from a configuration section.

    Args:
        config (Config): Parsed YAML as dict.
        section (str): Section name.

    Returns:
        list[tuple[str, str]]: List of key-value pair tuples.
    """
    return list(get.items()) if (get := config.get(section)) else []
