#!/usr/bin/python3
"""This file provides cache utilities"""

import json
import logging
import math
import os
import time
from configparser import ConfigParser
from pathlib import Path

import maven_check_versions.config as _config


def load_cache(cache_file: str) -> dict:
    """
    Load cache from a file.

    Args:
        cache_file (str): Path to the cache file.

    Returns:
        dict: A dictionary representing the loaded cache.
    """
    if os.path.exists(cache_file):
        logging.info(f"Load Cache: {Path(cache_file).absolute()}")
        with open(cache_file) as cf:
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
        logging.info(f"Save Cache: {Path(cache_file).absolute()}")
        with open(cache_file, 'w') as cf:
            json.dump(cache_data, cf)


def process_cache(
        arguments: dict, cache_data: dict | None, config_parser: ConfigParser, artifact_id: str,
        group_id: str, version: str
) -> bool:
    """
    Process cached data for a dependency.

    Args:
        arguments (dict): Parsed command line arguments.
        cache_data (dict | None): Cache data containing dependency information.
        config_parser (ConfigParser): Configuration parser for settings.
        artifact_id (str): Artifact ID of the dependency.
        group_id (str): Group ID of the dependency.
        version (str): Version of the dependency.

    Returns:
        bool: True if the cached data is valid and up-to-date, False otherwise.
    """
    data = cache_data.get(f"{group_id}:{artifact_id}")
    cached_time, cached_version, cached_key, cached_date, cached_versions = data
    if cached_version == version:
        return True

    cache_time_threshold = _config.get_config_value(config_parser, arguments, 'cache_time', value_type=int)

    if cache_time_threshold == 0 or time.time() - cached_time < cache_time_threshold:
        message_format = '*{}: {}:{}, current:{} versions: {} updated: {}'
        formatted_date = cached_date if cached_date is not None else ''
        logging.info(message_format.format(
            cached_key, group_id, artifact_id, version, ', '.join(cached_versions),
            formatted_date).rstrip())
        return True
    return False


def update_cache(
        cache_data: dict | None, available_versions: list, artifact_id: str, group_id, item: str,
        last_modified_date: str | None, section_key: str
) -> None:
    """
    Update the cache data with the latest information about the artifact.

    Args:
        cache_data (dict | None): The cache dictionary where data is stored.
        available_versions (list): List of available versions for the artifact.
        artifact_id (str): The artifact ID of the Maven dependency.
        group_id (str): The group ID of the Maven dependency.
        item (str): The specific version item being processed.
        last_modified_date (str | None): The last modified date of the artifact.
        section_key (str): The key for the repository section.
    """
    if cache_data is not None:
        value = (math.trunc(time.time()), item, section_key, last_modified_date, available_versions[:3])
        cache_data[f"{group_id}:{artifact_id}"] = value
