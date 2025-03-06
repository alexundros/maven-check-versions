#!/usr/bin/python3
"""This file provides cache utilities"""

import json
import logging
import math
import os
import time
from pathlib import Path

import maven_check_versions.config as _config


def load_cache(config: dict, arguments: dict) -> dict:
    """
    Loads the cache.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.

    Returns:
        dict: Cache data dictionary or an empty dictionary.
    """
    match _config.get_config_value(
        config, arguments, 'cache_backend', value_type=str, default_value='json'
    ):
        case 'json':
            if (cache_file := arguments.get('cache_file')) is None:
                cache_file = 'maven_check_versions.cache'
            if os.path.exists(cache_file):
                logging.info(f"Load Cache: {Path(cache_file).absolute()}")
                with open(cache_file) as cf:
                    return json.load(cf)
    return {}


def save_cache(config: dict, arguments: dict, cache_data: dict) -> None:
    """
    Saves the cache.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.
        cache_data (dict): Cache data to save.
    """
    if cache_data is not None:
        match _config.get_config_value(
            config, arguments, 'cache_backend', value_type=str, default_value='json'
        ):
            case 'json':
                if (cache_file := arguments.get('cache_file')) is None:
                    cache_file = 'maven_check_versions.cache'
                logging.info(f"Save Cache: {Path(cache_file).absolute()}")
                with open(cache_file, 'w') as cf:
                    json.dump(cache_data, cf)


def process_cache(
        config: dict, arguments: dict, cache_data: dict | None, artifact_id: str,
        group_id: str, version: str
) -> bool:
    """
    Processes cached data for a dependency.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.
        cache_data (dict | None): Cache data for dependencies.
        artifact_id (str): Artifact ID of the dependency.
        group_id (str): Group ID of the dependency.
        version (str): Version of the dependency.

    Returns:
        bool: True if the cache is valid and up-to-date, False otherwise.
    """
    data = cache_data.get(f"{group_id}:{artifact_id}")
    cached_time, cached_version, cached_key, cached_date, cached_versions = data
    if cached_version == version:
        return True

    ct_threshold = _config.get_config_value(config, arguments, 'cache_time', value_type=int)

    if ct_threshold == 0 or time.time() - cached_time < ct_threshold:
        message_format = '*{}: {}:{}, current:{} versions: {} updated: {}'
        formatted_date = cached_date if cached_date is not None else ''
        logging.info(message_format.format(
            cached_key, group_id, artifact_id, version, ', '.join(cached_versions),
            formatted_date).rstrip())
        return True
    return False


def update_cache(
        cache_data: dict | None, available: list, artifact_id: str, group_id, item: str,
        last_modified_date: str | None, section_key: str
) -> None:
    """
    Updates the cache with new artifact data.

    Args:
        cache_data (dict | None): Cache dictionary to update.
        available (list): List of available versions for the artifact.
        artifact_id (str): Artifact ID.
        group_id (str): Group ID.
        item (str): Current artifact version.
        last_modified_date (str | None): Last modified date of the artifact.
        section_key (str): Repository section key.
    """
    if cache_data is not None:
        value = (math.trunc(time.time()), item, section_key, last_modified_date, available[:3])
        cache_data[f"{group_id}:{artifact_id}"] = value
