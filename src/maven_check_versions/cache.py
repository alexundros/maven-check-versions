#!/usr/bin/python3
"""This file provides cache utilities"""

import json
import logging
import math
import os
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path

import pymemcache
import redis
import tarantool
import maven_check_versions.config as _config
from maven_check_versions.config import Config, Arguments

KEY1 = 'maven_check_versions_artifacts'
KEY2 = 'maven_check_versions_vulnerabilities'
HOST = 'localhost'
REDIS_PORT = 6379
TARANTOOL_PORT = 3301
MEMCACHED_PORT = 11211


class DCJSONEncoder(json.JSONEncoder):  # pragma: no cover
    """
    JSON Encoder for dataclasses.
    """
    def default(self, obj):
        """
        Encodes dataclass objects to JSON by converting them to dictionaries.

        Args:
            obj: The object to encode.

        Returns:
            dict: The encoded object as a dictionary, or delegates to the parent encoder.
        """
        if is_dataclass(obj):
            return asdict(obj)
        return super().default(obj)


def _redis_config(config: Config, arguments: Arguments, section: str) -> tuple:
    """
    Retrieves the Redis connection parameters from the configuration.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').

    Returns:
        tuple: A tuple containing (host, port, key, user, password) for Redis connection.
            - host (str): Redis server hostname.
            - port (int): Redis server port.
            - key (str): Redis key for storing cache data.
            - user (str | None): Redis username (optional).
            - password (str | None): Redis password (optional).
    """
    return (
        _config.get_config_value(
            config, arguments, 'redis_host', section=section, default=HOST),
        _config.get_config_value(
            config, arguments, 'redis_port', section=section, default=REDIS_PORT),
        _config.get_config_value(
            config, arguments, 'redis_key', section=section,
            default=KEY2 if section == 'vulnerability' else KEY1),
        _config.get_config_value(config, arguments, 'redis_user', section=section),
        _config.get_config_value(config, arguments, 'redis_password', section=section)
    )


def _tarantool_config(config: Config, arguments: Arguments, section: str) -> tuple:
    """
    Retrieves the Tarantool connection parameters from the configuration.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').

    Returns:
        tuple: A tuple containing (host, port, space, user, password) for Tarantool connection.
            - host (str): Tarantool server hostname.
            - port (int): Tarantool server port.
            - space (str): Tarantool space name for storing cache data.
            - user (str | None): Tarantool username (optional).
            - password (str | None): Tarantool password (optional).
    """
    return (
        _config.get_config_value(
            config, arguments, 'tarantool_host', section=section, default=HOST),
        _config.get_config_value(
            config, arguments, 'tarantool_port', section=section, default=TARANTOOL_PORT),
        _config.get_config_value(
            config, arguments, 'tarantool_space', section=section,
            default=KEY2 if section == 'vulnerability' else KEY1),
        _config.get_config_value(config, arguments, 'tarantool_user', section=section),
        _config.get_config_value(config, arguments, 'tarantool_password', section=section)
    )


def _memcached_config(config: Config, arguments: Arguments, section: str) -> tuple:
    """
    Retrieves the Memcached connection parameters from the configuration.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').

    Returns:
        tuple: A tuple containing (host, port, key) for Memcached connection.
            - host (str): Memcached server hostname.
            - port (int): Memcached server port.
            - key (str): Memcached key for storing cache data.
    """
    return (
        _config.get_config_value(
            config, arguments, 'memcached_host', section=section, default=HOST),
        _config.get_config_value(
            config, arguments, 'memcached_port', section=section, default=MEMCACHED_PORT),
        _config.get_config_value(
            config, arguments, 'memcached_key', section=section,
            default=KEY2 if section == 'vulnerability' else KEY1)
    )


def load_cache(config: Config, arguments: Arguments, section: str = 'base') -> dict:
    """
    Loads the cache data from the specified backend based on the configuration.
    Supports JSON, Redis, Tarantool, and Memcached backends.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str, optional): Configuration section to use (default is 'base').

    Returns:
        dict: Cache data as a dictionary if successfully loaded, otherwise an empty dictionary.
    """
    match _config.get_config_value(
        config, arguments, 'cache_backend', section=section, default='json'
    ):
        case 'json':
            success, value = _load_cache_json(config, arguments, section)
            if success:
                return value
        case 'redis':
            success, value = _load_cache_redis(config, arguments, section)
            if success:
                return value
        case 'tarantool':
            success, value = _load_cache_tarantool(config, arguments, section)
            if success:
                return value
        case 'memcached':
            success, value = _load_cache_memcached(config, arguments, section)
            if success:
                return value
    return {}


def _load_cache_json(config: Config, arguments: Arguments, section: str) -> tuple[bool, dict]:
    """
    Attempts to load the cache data from a JSON file specified in the configuration.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').

    Returns:
        tuple[bool, dict]: A tuple containing:
            - bool: True if the cache was successfully loaded, False otherwise.
            - dict: The cache data dictionary if successful, otherwise an empty dictionary.
        """
    cache_file = _config.get_config_value(
        config, arguments, 'cache_file', section=section,
        default=(KEY2 if section == 'vulnerability' else KEY1) + '.json')
    if os.path.exists(cache_file):
        logging.info(f"Load Cache: {Path(cache_file).absolute()}")
        with open(cache_file) as cf:
            return True, json.load(cf)
    return False, {}


def _load_cache_redis(config: Config, arguments: Arguments, section: str) -> tuple[bool, dict]:
    """
    Attempts to load the cache data from Redis using the configuration parameters.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').

    Returns:
        tuple[bool, dict]: A tuple containing:
            - bool: True if the cache was successfully loaded, False otherwise.
            - dict: The cache data dictionary if successful, otherwise an empty dictionary.
    """
    try:
        host, port, ckey, user, password = _redis_config(config, arguments, section)
        inst = redis.Redis(
            host=host, port=port, username=user, password=password,
            decode_responses=True)
        cache_data = {}
        if isinstance(data := inst.hgetall(ckey), dict):
            for key, value in data.items():
                cache_data[key] = json.loads(value)

        return True, cache_data
    except Exception as e:
        logging.error(f"Failed to load cache from Redis: {e}")
        return False, {}


def _load_cache_tarantool(config: Config, arguments: Arguments, section: str) -> tuple[bool, dict]:
    """
    Attempts to load the cache data from Tarantool using the configuration parameters.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').

    Returns:
        tuple[bool, dict]: A tuple containing:
            - bool: True if the cache was successfully loaded, False otherwise.
            - dict: The cache data dictionary if successful, otherwise an empty dictionary.
    """
    try:
        host, port, space, user, password = _tarantool_config(config, arguments, section)
        conn = tarantool.connect(host, port, user=user, password=password)
        cache_data = {}
        for record in conn.space(space).select():
            cache_data[record[0]] = json.loads(record[1])

        return True, cache_data
    except Exception as e:
        logging.error(f"Failed to load cache from Tarantool: {e}")
    return False, {}


def _load_cache_memcached(config: Config, arguments: Arguments, section: str) -> tuple[bool, dict]:
    """
    Attempts to load the cache data from Memcached using the configuration parameters.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').

    Returns:
        tuple[bool, dict]: A tuple containing:
            - bool: True if the cache was successfully loaded, False otherwise.
            - dict: The cache data dictionary if successful, otherwise an empty dictionary.
    """
    try:
        host, port, key = _memcached_config(config, arguments, section)
        client = pymemcache.client.base.Client((host, port))
        if (cache_data := client.get(key)) is not None:
            return True, json.loads(cache_data)

    except Exception as e:
        logging.error(f"Failed to load cache from Memcached: {e}")
    return False, {}


def save_cache(config: Config, arguments: Arguments, cache_data: dict, section: str = 'base') -> None:
    """
    Saves the cache data to the specified backend based on the configuration.
    Supports JSON, Redis, Tarantool, and Memcached backends.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        cache_data (dict): Cache data to save.
        section (str, optional): Configuration section to use (default is 'base').
    """
    if cache_data is not None:
        match _config.get_config_value(
            config, arguments, 'cache_backend', section=section, default='json'
        ):
            case 'json':
                _save_cache_json(config, arguments, cache_data, section)
            case 'redis':
                _save_cache_redis(config, arguments, cache_data, section)
            case 'tarantool':
                _save_cache_tarantool(config, arguments, cache_data, section)
            case 'memcached':
                _save_cache_memcached(config, arguments, cache_data, section)


def _save_cache_json(config: Config, arguments: Arguments, cache_data: dict, section: str) -> None:
    """
    Saves the cache data to a JSON file specified in the configuration.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        cache_data (dict): Cache data to save.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').
    """
    cache_file = _config.get_config_value(
        config, arguments, 'cache_file', section=section,
        default=(KEY2 if section == 'vulnerability' else KEY1) + '.json')
    logging.info(f"Save Cache: {Path(cache_file).absolute()}")
    with open(cache_file, 'w') as cf:
        json.dump(cache_data, cf, cls=DCJSONEncoder)


def _save_cache_redis(config: Config, arguments: Arguments, cache_data: dict, section: str) -> None:
    """
    Saves the cache data to Redis using the configuration parameters.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        cache_data (dict): Cache data to save.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').
    """
    try:
        host, port, ckey, user, password = _redis_config(config, arguments, section)
        inst = redis.Redis(
            host=host, port=port, username=user, password=password,
            decode_responses=True)
        for key, value in cache_data.items():
            inst.hset(ckey, key, json.dumps(value, cls=DCJSONEncoder))

    except Exception as e:
        logging.error(f"Failed to save cache to Redis: {e}")


def _save_cache_tarantool(config: Config, arguments: Arguments, cache_data: dict, section: str) -> None:
    """
    Saves the cache data to Tarantool using the configuration parameters.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        cache_data (dict): Cache data to save.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').
    """
    try:
        host, port, space, user, password = _tarantool_config(config, arguments, section)
        conn = tarantool.connect(host, port, user=user, password=password)
        space = conn.space(space)
        for key, value in cache_data.items():
            space.replace((key, json.dumps(value, cls=DCJSONEncoder)))

    except Exception as e:
        logging.error(f"Failed to save cache to Tarantool: {e}")


def _save_cache_memcached(config: Config, arguments: Arguments, cache_data: dict, section: str) -> None:
    """
    Saves the cache data to Memcached using the configuration parameters.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        cache_data (dict): Cache data to save.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').
    """
    try:
        host, port, key = _memcached_config(config, arguments, section)
        client = pymemcache.client.base.Client((host, port))
        client.set(key, json.dumps(cache_data, cls=DCJSONEncoder))
    except Exception as e:
        logging.error(f"Failed to save cache to Memcached: {e}")


def process_cache_artifact(
        config: Config, arguments: Arguments, cache_data: dict | None, artifact: str, group: str,
        version: str | None
) -> bool:
    """
    Checks if the cached data for the specified artifact is valid and up-to-date.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        cache_data (dict | None): The cache data dictionary containing artifact information.
        artifact (str): The artifact ID of the dependency.
        group (str): The group ID of the dependency.
        version (str | None): The current version of the artifact, or None if not specified.

    Returns:
        bool: True if the cache exists, matches the version, and is within the time threshold,
            False otherwise.
    """
    if cache_data is None or (data := cache_data.get(f"{group}:{artifact}")) is None:
        return False
    cached_time, cached_version, cached_key, cached_date, cached_versions = data
    if cached_version == version:
        return True

    ct_threshold = _config.get_config_value(config, arguments, 'cache_time')

    if ct_threshold == 0 or time.time() - cached_time < ct_threshold:
        message_format = '*{}: {}:{}, current:{} versions: {} updated: {}'
        formatted_date = cached_date if cached_date is not None else ''
        logging.info(message_format.format(
            cached_key, group, artifact, version, ', '.join(cached_versions),
            formatted_date).rstrip())
        return True
    return False


def update_cache_artifact(
        cache_data: dict | None, versions: list, artifact: str, group, item: str,
        last_modified_date: str | None, section_key: str
) -> None:
    """
    Updates the cache dictionary with the latest data for the specified artifact.

    Args:
        cache_data (dict | None): The cache dictionary to update, or None if caching is disabled.
        versions (list): List of available versions for the artifact.
        artifact (str): The artifact ID of the dependency.
        group (str): The group ID of the dependency.
        item (str): The current version of the artifact being processed.
        last_modified_date (str | None):
            The last modified date of the artifact in ISO format, or None if unavailable.
        section_key (str): The repository section key from the configuration.
    """
    if cache_data is not None:
        value = (math.trunc(time.time()), item, section_key, last_modified_date, versions[:3])
        cache_data[f"{group}:{artifact}"] = value
