#!/usr/bin/python3
"""This file provides cache utilities"""
import json
import logging
import math
import os
import time
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import maven_check_versions.config as _config
import pymemcache
import redis
import tarantool
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
        return asdict(obj) if is_dataclass(obj) else super().default(obj)


def _redis_config(
        config: Config, arguments: Arguments, section: str
) -> Tuple[str, int, str, Optional[str], Optional[str]]:
    """
    Retrieves the Redis connection parameters from the configuration.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').

    Returns:
        tuple: A tuple containing (host, port, key, user, password) for Redis connection.
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


@contextmanager
def _redis_connection(host: str, port: int, user: Optional[str], password: Optional[str]):
    """
    Context manager for Redis connection, ensuring proper cleanup.

    Args:
        host (str): Redis server host.
        port (int): Redis server port.
        user (Optional[str]): Redis username, if required.
        password (Optional[str]): Redis password, if required.

    Yields:
        redis.Redis: An instance of the Redis client.
    """
    inst = redis.Redis(host=host, port=port, username=user, password=password, decode_responses=True)
    try:
        yield inst
    finally:
        inst.close()


@contextmanager
def _tarantool_connection(host: str, port: int, user: Optional[str], password: Optional[str]):
    """
    Context manager for Tarantool connection, ensuring proper cleanup.

    Args:
        host (str): Tarantool server host.
        port (int): Tarantool server port.
        user (Optional[str]): Tarantool username, if required.
        password (Optional[str]): Tarantool password, if required.

    Yields:
        tarantool.Connection: An instance of the Tarantool connection.
    """
    conn = tarantool.Connection(host, port, user=user, password=password)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def _memcached_connection(host: str, port: int):
    """
    Context manager for Memcached connection, ensuring proper cleanup.

    Args:
        host (str): Memcached server host.
        port (int): Memcached server port.

    Yields:
        pymemcache.client.base.Client: An instance of the Memcached client.
    """
    client = pymemcache.client.base.Client((host, port))
    try:
        yield client
    finally:
        client.close()


def _load_cache_json(
        config: Config, arguments: Arguments, section: str
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Attempts to load the cache data from a JSON file specified in the configuration.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').

    Returns:
        tuple[bool, dict]: A tuple containing:
            - bool: True if the cache was successfully loaded, False otherwise.
            - Optional[Dict[str, Any]]: The cache data dictionary if successful, otherwise None.
    """
    cache_file = _config.get_config_value(
        config, arguments, 'cache_file', section=section,
        default=(KEY2 if section == 'vulnerability' else KEY1) + '.json')

    if os.path.exists(cache_file):
        logging.info(f"Load Cache: {Path(cache_file).absolute()}")
        try:
            with open(cache_file) as cf:
                return True, json.load(cf)
        except json.JSONDecodeError as e:  # pragma: no cover
            logging.error(f"Failed to decode JSON cache data: {e}")
    return False, None


def _load_cache_redis(
        config: Config, arguments: Arguments, section: str
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Attempts to load the cache data from Redis using the configuration parameters.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').

    Returns:
        tuple[bool, dict]: A tuple containing:
            - bool: True if the cache was successfully loaded, False otherwise.
            - Optional[Dict[str, Any]]: The cache data dictionary if successful, otherwise None.
    """
    try:
        host, port, ckey, user, password = _redis_config(config, arguments, section)

        with _redis_connection(host, port, user, password) as inst:
            cache_data: Dict[str, Any] = {}
            if isinstance(data := inst.hgetall(ckey), dict):
                for key, value in data.items():
                    try:
                        cache_data[key] = json.loads(value)
                    except json.JSONDecodeError as e:  # pragma: no cover
                        logging.error(f"Failed to decode Redis data for key {key}: {e}")
            return True, cache_data

    except redis.ConnectionError as e:  # pragma: no cover
        logging.error(f"Redis connection failed: {e}")
    except redis.RedisError as e:  # pragma: no cover
        logging.error(f"Redis error: {e}")
    except Exception as e:
        logging.error(f"Failed to load cache from Redis: {e}")
    return False, None


def _load_cache_tarantool(
        config: Config, arguments: Arguments, section: str
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Attempts to load the cache data from Tarantool using the configuration parameters.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').

    Returns:
        tuple[bool, dict]: A tuple containing:
            - bool: True if the cache was successfully loaded, False otherwise.
            - Optional[Dict[str, Any]]: The cache data dictionary if successful, otherwise None.
    """
    try:
        host, port, space, user, password = _tarantool_config(config, arguments, section)

        with _tarantool_connection(host, port, user, password) as conn:
            cache_data: Dict[str, Any] = {}
            if data := conn.select(space):
                for item in data:
                    try:
                        cache_data[item[0]] = json.loads(item[1])
                    except json.JSONDecodeError as e:  # pragma: no cover
                        logging.error(f"Failed to decode Tarantool data for key {item[0]}: {e}")
            return True, cache_data

    except tarantool.DatabaseError as e:  # pragma: no cover
        logging.error(f"Tarantool error: {e}")
    except Exception as e:
        logging.error(f"Failed to load cache from Tarantool: {e}")
    return False, None


def _load_cache_memcached(
        config: Config, arguments: Arguments, section: str
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Attempts to load the cache data from Memcached using the configuration parameters.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').

    Returns:
        tuple[bool, dict]: A tuple containing:
            - bool: True if the cache was successfully loaded, False otherwise.
            - Optional[Dict[str, Any]]: The cache data dictionary if successful, otherwise None.
    """
    try:
        host, port, key = _memcached_config(config, arguments, section)

        with _memcached_connection(host, port) as client:
            if data := client.get(key):
                try:
                    return True, json.loads(data)
                except json.JSONDecodeError as e:  # pragma: no cover
                    logging.error(f"Failed to decode Memcached data: {e}")

    except pymemcache.exceptions.MemcacheError as e:  # pragma: no cover
        logging.error(f"Memcached error: {e}")
    except Exception as e:
        logging.error(f"Failed to load cache from Memcached: {e}")
    return False, None


def _save_cache_json(
        config: Config, arguments: Arguments, cache_data: Dict[str, Any], section: str
) -> None:
    """
    Saves the cache data to a JSON file specified in the configuration.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        cache_data (Dict[str, Any]): Cache data to save.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').
    """
    cache_file = _config.get_config_value(
        config, arguments, 'cache_file', section=section,
        default=(KEY2 if section == 'vulnerability' else KEY1) + '.json')
    logging.info(f"Save Cache: {Path(cache_file).absolute()}")

    try:
        with open(cache_file, 'w') as cf:
            json.dump(cache_data, cf, cls=DCJSONEncoder)
    except Exception as e:  # pragma: no cover
        logging.error(f"Failed to save cache to JSON file {cache_file}: {e}")


def _save_cache_redis(
        config: Config, arguments: Arguments, cache_data: Dict[str, Any], section: str
) -> None:
    """
    Saves the cache data to Redis using the configuration parameters.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        cache_data (Dict[str, Any]): Cache data to save.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').
    """
    try:
        host, port, ckey, user, password = _redis_config(config, arguments, section)

        with _redis_connection(host, port, user, password) as inst:
            for key, value in cache_data.items():
                try:
                    inst.hset(ckey, key, json.dumps(value, cls=DCJSONEncoder))
                except redis.RedisError as e:  # pragma: no cover
                    logging.error(f"Failed to save cache to Redis for key {key}: {e}")

    except redis.ConnectionError as e:  # pragma: no cover
        logging.error(f"Redis connection failed: {e}")
    except redis.RedisError as e:  # pragma: no cover
        logging.error(f"Redis error: {e}")
    except Exception as e:
        logging.error(f"Failed to save cache to Redis: {e}")


def _save_cache_tarantool(
        config: Config, arguments: Arguments, cache_data: Dict[str, Any], section: str
) -> None:
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

        with _tarantool_connection(host, port, user, password) as conn:
            space = conn.space(space)
            for key, value in cache_data.items():
                space.replace((key, json.dumps(value, cls=DCJSONEncoder)))

    except tarantool.DatabaseError as e:  # pragma: no cover
        logging.error(f"Tarantool error: {e}")
    except Exception as e:
        logging.error(f"Failed to save cache to Tarantool: {e}")


def _save_cache_memcached(
        config: Config, arguments: Arguments, cache_data: Dict[str, Any], section: str
) -> None:
    """
    Saves the cache data to Memcached using the configuration parameters.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        cache_data (Dict[str, Any]): Cache data to save.
        section (str): Configuration section to use (e.g., 'base' or 'vulnerability').
    """
    try:
        host, port, key = _memcached_config(config, arguments, section)

        with _memcached_connection(host, port) as client:
            client.set(key, json.dumps(cache_data, cls=DCJSONEncoder))

    except pymemcache.exceptions.MemcacheError as e:  # pragma: no cover
        logging.error(f"Memcached error: {e}")
    except Exception as e:
        logging.error(f"Failed to save cache to Memcached: {e}")


def load_cache(config: Config, arguments: Arguments, section: str = 'base') -> Optional[Dict[str, Any]]:
    """
    Loads the cache data from the specified backend based on the configuration.
    Supports JSON, Redis, Tarantool, and Memcached backends.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str, optional): Configuration section to use (default is 'base').

    Returns:
        Optional[Dict[str, Any]]: Cache data as a dictionary if successfully loaded, otherwise None.
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
    return None


def save_cache(
        config: Config, arguments: Arguments, cache_data: Optional[Dict[str, Any]], section: str = 'base'
) -> None:
    """
    Saves the cache data to the specified backend based on the configuration.
    Supports JSON, Redis, Tarantool, and Memcached backends.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        cache_data (Optional[Dict[str, Any]]): Cache data to save.
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


def process_cache_artifact(
        config: Config, arguments: Arguments, cache_data: Optional[Dict[str, Any]],
        artifact: str, group: str, version: Optional[str]
) -> bool:
    """
    Checks if the cached data for the specified artifact is valid and up-to-date.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        cache_data (Optional[Dict[str, Any]]): The cache data dictionary containing artifact information.
        artifact (str): The artifact ID of the dependency.
        group (str): The group ID of the dependency.
        version (Optional[str]): The current version of the artifact, or None if not specified.

    Returns:
        bool: True if the cache exists and either the cached version matches the provided version
            or the cache timestamp is within the configured time threshold, False otherwise.
    """
    if cache_data is None or (data := cache_data.get(f"{group}:{artifact}")) is None:
        return False
    cached_time, cached_version, cached_key, cached_date, cached_versions = data
    if cached_version == version:
        return True

    ct_threshold = _config.get_config_value(config, arguments, 'cache_time')

    if ct_threshold == 0 or time.time() - cached_time < ct_threshold:
        message_format = '*{}: {}:{}, current:{} versions: {} updated: {}'
        logging.info(message_format.format(
            cached_key, group, artifact, version, ', '.join(cached_versions),
            cached_date if cached_date is not None else '').rstrip())
        return True
    return False


def update_cache_artifact(
        cache_data: Optional[Dict[str, Any]], versions: list, artifact: str, group,
        item: str, last_modified_date: Optional[str], section_key: str
) -> None:
    """
    Updates the cache dictionary with the latest data for the specified artifact.

    Args:
        cache_data (Optional[Dict[str, Any]]): The cache dictionary to update, or None if caching is disabled.
        versions (list): List of available versions for the artifact.
        artifact (str): The artifact ID of the dependency.
        group (str): The group ID of the dependency.
        item (str): The current version of the artifact being processed.
        last_modified_date (Optional[str]):
            The last modified date of the artifact in ISO format, or None if unavailable.
        section_key (str): The repository section key from the configuration.
    """
    if cache_data is not None:
        value = (math.trunc(time.time()), item, section_key, last_modified_date, versions[:3])
        cache_data[f"{group}:{artifact}"] = value
