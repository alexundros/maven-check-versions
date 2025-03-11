#!/usr/bin/python3
"""This file provides cache utilities"""

import json
import logging
import math
import os
import time
from pathlib import Path

import maven_check_versions.config as _config
import pymemcache
import redis
import tarantool

FILE = 'maven_check_versions.cache.json'
KEY = 'maven_check_versions_cache'
HOST = 'localhost'
REDIS_PORT = '6379'
TARANTOOL_PORT = '3301'
MEMCACHED_PORT = '11211'


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
        config, arguments, 'cache_backend', value_type=str, default='json'
    ):
        case 'json':
            success, value = _load_cache_json(config, arguments)
            if success:
                return value
        case 'redis':
            success, value = _load_cache_redis(config, arguments)
            if success:
                return value
        case 'tarantool':
            success, value = _load_cache_tarantool(config, arguments)
            if success:
                return value
        case 'memcached':
            success, value = _load_cache_memcached(config, arguments)
            if success:
                return value
    return {}


def _load_cache_json(config: dict, arguments: dict) -> tuple[bool, dict]:
    """
        Loads the cache from JSON file.

        Args:
            config (dict): Parsed YAML as dict.
            arguments (dict): Command-line arguments.

        Returns:
            dict: Cache data dictionary or an empty dictionary.
        """
    cache_file = _config.get_config_value(
        config, arguments, 'cache_file', value_type=str, default=FILE)
    if os.path.exists(cache_file):
        logging.info(f"Load Cache: {Path(cache_file).absolute()}")
        with open(cache_file) as cf:
            return True, json.load(cf)
    return False, {}


def _redis_config(arguments, config) -> tuple:
    """Get Redis parameters.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.

    Returns:
        tuple: Redis parameters.
    """
    host = _config.get_config_value(
        config, arguments, 'redis_host', value_type=str, default=HOST)
    port = _config.get_config_value(
        config, arguments, 'redis_port', value_type=int, default=REDIS_PORT)
    key = _config.get_config_value(
        config, arguments, 'redis_key', value_type=str, default=KEY)
    user = _config.get_config_value(config, arguments, 'redis_user')
    password = _config.get_config_value(config, arguments, 'redis_password')

    return host, port, key, user, password


def _load_cache_redis(config: dict, arguments: dict) -> tuple[bool, dict]:
    """Loads the cache from Redis.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.

    Returns:
        tuple[bool, dict]: Success flag and cache data dictionary or an empty dictionary.
    """
    try:
        host, port, ckey, user, password = _redis_config(arguments, config)
        inst = redis.Redis(
            host=host, port=port, username=user, password=password,
            decode_responses=True)
        cache_data = {}
        for key, value in inst.hgetall(ckey).items():
            cache_data[key] = json.loads(value)

        return True, cache_data
    except Exception as e:
        logging.error(f"Failed to load cache from Redis: {e}")
        return False, {}


def _tarantool_config(arguments, config) -> tuple:
    """Get Tarantool parameters.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.

    Returns:
        tuple: Tarantool parameters.
    """
    host = _config.get_config_value(
        config, arguments, 'tarantool_host', value_type=str, default=HOST)
    port = _config.get_config_value(
        config, arguments, 'tarantool_port', value_type=int, default=TARANTOOL_PORT)
    space = _config.get_config_value(
        config, arguments, 'tarantool_space', value_type=str, default=KEY)
    user = _config.get_config_value(config, arguments, 'tarantool_user')
    password = _config.get_config_value(config, arguments, 'tarantool_password')

    return host, port, space, user, password


def _load_cache_tarantool(config: dict, arguments: dict) -> tuple[bool, dict]:
    """Loads the cache from Tarantool.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.

    Returns:
        tuple[bool, dict]: Success flag and cache data dictionary or an empty dictionary.
    """
    try:
        host, port, space, user, password = _tarantool_config(arguments, config)
        conn = tarantool.connect(host, port, user=user, password=password)
        cache_data = {}
        for record in conn.space(space).select():
            cache_data[record[0]] = json.loads(record[1])

        return True, cache_data
    except Exception as e:
        logging.error(f"Failed to load cache from Tarantool: {e}")
    return False, {}


def _memcached_config(arguments, config) -> tuple:
    """Get Memcached parameters.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.

    Returns:
        tuple: Memcached host, port, and key.
    """
    host = (_config.get_config_value
            (config, arguments, 'memcached_host', value_type=str, default=HOST))
    port = _config.get_config_value(
        config, arguments, 'memcached_port', value_type=int, default=MEMCACHED_PORT)
    key = _config.get_config_value(
        config, arguments, 'memcached_key', value_type=str, default=KEY)

    return host, port, key


def _load_cache_memcached(config: dict, arguments: dict) -> tuple[bool, dict]:
    """Loads the cache from Memcached.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.

    Returns:
        tuple[bool, dict]: Success flag and cache data dictionary or an empty dictionary.
    """
    try:
        host, port, key = _memcached_config(arguments, config)
        client = pymemcache.client.base.Client((host, port))
        if (cache_data := client.get(key)) is not None:
            return True, json.loads(cache_data)

    except Exception as e:
        logging.error(f"Failed to load cache from Memcached: {e}")
    return False, {}


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
            config, arguments, 'cache_backend', value_type=str, default='json'
        ):
            case 'json':
                _save_cache_json(config, arguments, cache_data)
            case 'redis':
                _save_cache_redis(config, arguments, cache_data)
            case 'tarantool':
                _save_cache_tarantool(config, arguments, cache_data)
            case 'memcached':
                _save_cache_memcached(config, arguments, cache_data)


def _save_cache_json(config: dict, arguments: dict, cache_data: dict) -> None:
    """
    Saves the cache to JSON file.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.
        cache_data (dict): Cache data to save.
    """
    cache_file = _config.get_config_value(
        config, arguments, 'cache_file', value_type=str, default=FILE)
    logging.info(f"Save Cache: {Path(cache_file).absolute()}")
    with open(cache_file, 'w') as cf:
        json.dump(cache_data, cf)


def _save_cache_redis(config: dict, arguments: dict, cache_data: dict) -> None:
    """Saves the cache to Redis.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.
        cache_data (dict): Cache data to save.
    """
    try:
        host, port, ckey, user, password = _redis_config(arguments, config)
        inst = redis.Redis(
            host=host, port=port, username=user, password=password,
            decode_responses=True)
        for key, value in cache_data.items():
            inst.hset(ckey, key, json.dumps(value))

    except Exception as e:
        logging.error(f"Failed to save cache to Redis: {e}")


def _save_cache_tarantool(config: dict, arguments: dict, cache_data: dict) -> None:
    """Saves the cache to Tarantool.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.
        cache_data (dict): Cache data to save.
    """
    try:
        host, port, space, user, password = _tarantool_config(arguments, config)
        conn = tarantool.connect(host, port, user=user, password=password)
        space = conn.space(space)
        for key, value in cache_data.items():
            space.replace((key, json.dumps(value)))

    except Exception as e:
        logging.error(f"Failed to save cache to Tarantool: {e}")


def _save_cache_memcached(config: dict, arguments: dict, cache_data: dict) -> None:
    """Saves the cache to Memcached.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.
        cache_data (dict): Cache data to save.
    """
    try:
        host, port, key = _memcached_config(arguments, config)
        client = pymemcache.client.base.Client((host, port))
        client.set(key, json.dumps(cache_data))
    except Exception as e:
        logging.error(f"Failed to save cache to Memcached: {e}")


def process_cache(
        config: dict, arguments: dict, cache_data: dict | None, artifact_id: str, group_id: str,
        version: str
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
        cache_data: dict | None, versions: list, artifact_id: str, group_id, item: str,
        last_modified_date: str | None, section_key: str
) -> None:
    """
    Updates the cache with new artifact data.

    Args:
        cache_data (dict | None): Cache dictionary to update.
        versions (list): List of available versions for the artifact.
        artifact_id (str): Artifact ID.
        group_id (str): Group ID.
        item (str): Current artifact version.
        last_modified_date (str | None): Last modified date of the artifact.
        section_key (str): Repository section key.
    """
    if cache_data is not None:
        value = (math.trunc(time.time()), item, section_key, last_modified_date, versions[:3])
        cache_data[f"{group_id}:{artifact_id}"] = value
