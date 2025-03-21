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
        Default encode.
        """
        if is_dataclass(obj):
            return asdict(obj)
        return super().default(obj)


def _redis_config(config: Config, arguments: Arguments, section: str) -> tuple:
    """Get Redis parameters.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section.

    Returns:
        tuple: Redis parameters.
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
    """Get Tarantool parameters.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section.

    Returns:
        tuple: Tarantool parameters.
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
    """Get Memcached parameters.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section.

    Returns:
        tuple: Memcached parameters.
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
    Loads the cache.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        section (str, optional): Configuration section (default is 'base').

    Returns:
        dict: Cache data dictionary or an empty dictionary.
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
        Loads the cache from JSON file.

        Args:
            config (Config): Parsed YAML as dict.
            arguments (Arguments): Command-line arguments.
            section (str): Configuration section.

        Returns:
            dict: Cache data dictionary or an empty dictionary.
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
    """Loads the cache from Redis.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.

    Returns:
        tuple[bool, dict]: Success flag and cache data dictionary or an empty dictionary.
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
    """Loads the cache from Tarantool.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.

    Returns:
        tuple[bool, dict]: Success flag and cache data dictionary or an empty dictionary.
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
    """Loads the cache from Memcached.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.

    Returns:
        tuple[bool, dict]: Success flag and cache data dictionary or an empty dictionary.
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
    Saves the cache.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        cache_data (dict): Cache data to save.
        section (str, optional): Configuration section (default is 'base').
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
    Saves the cache to JSON file.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        cache_data (dict): Cache data to save.
        section (str): Configuration section.
    """
    cache_file = _config.get_config_value(
        config, arguments, 'cache_file', section=section,
        default=(KEY2 if section == 'vulnerability' else KEY1) + '.json')
    logging.info(f"Save Cache: {Path(cache_file).absolute()}")
    with open(cache_file, 'w') as cf:
        json.dump(cache_data, cf, cls=DCJSONEncoder)


def _save_cache_redis(config: Config, arguments: Arguments, cache_data: dict, section: str) -> None:
    """Saves the cache to Redis.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        cache_data (dict): Cache data to save.
        section (str): Configuration section.
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
    """Saves the cache to Tarantool.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        cache_data (dict): Cache data to save.
        section (str): Configuration section.
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
    """Saves the cache to Memcached.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        cache_data (dict): Cache data to save.
        section (str): Configuration section.
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
    Processes cached data for artifact.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        cache_data (dict | None): Cache data for dependencies.
        artifact (str): Artifact ID of the dependency.
        group (str): Group ID of the dependency.
        version (str | None): Version of the dependency.

    Returns:
        bool: True if the cache is valid and up-to-date, False otherwise.
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
    Updates the cache with new artifact data.

    Args:
        cache_data (dict | None): Cache dictionary to update.
        versions (list): List of available versions for the artifact.
        artifact (str): Artifact ID.
        group (str): Group ID.
        item (str): Current artifact version.
        last_modified_date (str | None): Last modified date of the artifact.
        section_key (str): Repository section key.
    """
    if cache_data is not None:
        value = (math.trunc(time.time()), item, section_key, last_modified_date, versions[:3])
        cache_data[f"{group}:{artifact}"] = value
