#!/usr/bin/python3
"""This file provides cache utilities"""
import json
import logging
import math
import os
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Optional, Dict, Any

import maven_check_versions.config as _config
import pymemcache
import redis
import tarantool
from maven_check_versions.config import Config, Arguments

_ARTIFACTS_KEY = 'maven_check_versions_artifacts'
_VULNERABILITIES_KEY = 'maven_check_versions_vulnerabilities'
_HOST = 'localhost'
_REDIS_PORT = 6379
_TARANTOOL_PORT = 3301
_MEMCACHED_PORT = 11211

update_cache_artifact_lock = threading.Lock()


class DCJSONEncoder(json.JSONEncoder):  # pragma: no cover
    """
    Custom JSON encoder for serializing dataclasses.
    """

    def default(self, obj):
        """
        Encodes dataclass objects to JSON by converting them to dictionaries.

        Args:
            obj: The object to encode.

        Returns:
            dict: The encoded object as a dictionary, or delegates to the parent encoder.
        """
        try:
            return asdict(obj) if is_dataclass(obj) else super().default(obj)
        except Exception as e:
            logging.error(f"Failed to encode dataclass: {e}")
            return None


class _CacheBackend(ABC):
    """
    Abstract base class for cache backend implementations.
    """

    @abstractmethod
    def load(self, config: Config, arguments: Arguments, section: str) -> Dict[str, Any]:  # pragma: no cover
        """
        Loads the cache data from the specified backend.

        Args:
            config (Config): Configuration dictionary parsed from YAML.
            arguments (Arguments): Command-line arguments.
            section (str): Configuration section to use (e.g., 'base' or 'vulnerability').

        Returns:
            Dict[str, Any]: The cache data dictionary. Returns an empty dictionary if loading
                fails or no data is available.
        """
        pass

    @abstractmethod
    def save(  # pragma: no cover
            self, config: Config, arguments: Arguments, cache_data: Dict[str, Any], section: str
    ) -> None:
        """
        Saves the cache data.

        Args:
            config (Config): Configuration dictionary parsed from YAML.
            arguments (Arguments): Command-line arguments.
            cache_data (Dict[str, Any]): Cache data to save.
            section (str): Configuration section to use (e.g., 'base' or 'vulnerability').
        """
        pass


class _CacheBackendRegistry:
    """
    Registry for managing cache backend implementations.
    """
    _backends: dict[str, _CacheBackend] = {}

    @classmethod
    def register(cls, name: str, backend: _CacheBackend):
        """
        Register a cache backend with a given name.
        """
        cls._backends[name] = backend

    @classmethod
    def get(cls, name: str) -> _CacheBackend:
        """
        Retrieve a cache backend by name, defaulting to JSON if not found.
        """
        return cls._backends.get(name, _JSONCacheBackend())


class _JSONCacheBackend(_CacheBackend):
    """
    Backend for caching data in json files.
    """

    def load(self, config: Config, arguments: Arguments, section: str) -> Dict[str, Any]:
        cache_file = _config.get_config_value(
            config, arguments, 'cache_file', section=section,
            default=(_VULNERABILITIES_KEY if section == 'vulnerability' else _ARTIFACTS_KEY) + '.json')

        if os.path.exists(cache_file):
            try:
                logging.info(f"Load Cache file: {Path(cache_file).absolute()}")
                with open(cache_file, encoding='utf-8') as cf:
                    return json.load(cf)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON cache data: {e}")
        return {}

    def save(
            self, config: Config, arguments: Arguments, cache_data: Dict[str, Any], section: str
    ) -> None:
        cache_file = _config.get_config_value(
            config, arguments, 'cache_file', section=section,
            default=(_VULNERABILITIES_KEY if section == 'vulnerability' else _ARTIFACTS_KEY) + '.json')

        try:
            logging.info(f"Save Cache file: {Path(cache_file).absolute()}")
            with open(cache_file, 'w', encoding='utf-8') as cf:
                cf.write(json.dumps(cache_data, cls=DCJSONEncoder))
        except Exception as e:
            logging.error(f"Failed to save cache to JSON file {cache_file}: {e}")


class _RedisCacheBackend(_CacheBackend):
    """
    Backend for caching data in Redis.
    """

    @staticmethod
    def _config(config: Config, arguments: Arguments, section: str) -> tuple:
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
                config, arguments, 'redis_host', section=section, default=_HOST),
            _config.get_config_value(
                config, arguments, 'redis_port', section=section, default=_REDIS_PORT),
            _config.get_config_value(
                config, arguments, 'redis_key', section=section,
                default=_VULNERABILITIES_KEY if section == 'vulnerability' else _ARTIFACTS_KEY),
            _config.get_config_value(config, arguments, 'redis_user', section=section),
            _config.get_config_value(config, arguments, 'redis_password', section=section)
        )

    @contextmanager
    def _connection(
            self, host: str, port: int, user: Optional[str], password: Optional[str]
    ):
        """
        Context manager for Redis connection, ensuring proper cleanup.

        Args:
            host (str): Redis server host.
            port (int): Redis server port.
            user (Optional[str]): Redis username, if required.
            password (Optional[str]): Redis password, if required.

        Yields:
            redis.Redis: An instance of the Redis client.

        Raises:
            redis.ConnectionError: If the connection to Redis fails.
            redis.RedisError: If an error occurs during Redis operations.
        """
        inst = redis.Redis(host=host, port=port, username=user, password=password, decode_responses=True)
        try:
            yield inst
        finally:
            inst.close()

    def load(self, config: Config, arguments: Arguments, section: str) -> Dict[str, Any]:
        try:
            host, port, ckey, user, password = self._config(config, arguments, section)

            with self._connection(host, port, user, password) as inst:
                cache_data: Dict[str, Any] = {}
                if data := inst.hgetall(ckey):
                    for key, value in data.items():
                        try:
                            cache_data[key] = json.loads(value)
                        except json.JSONDecodeError as e:
                            logging.error(f"Failed to decode Redis data for key {key}: {e}")
                return cache_data

        except redis.ConnectionError as e:  # pragma: no cover
            logging.error(f"Redis connection failed: {e}")
        except redis.RedisError as e:  # pragma: no cover
            logging.error(f"Redis error: {e}")
        except Exception as e:
            logging.error(f"Failed to load cache from Redis: {e}")
        return {}

    def save(
            self, config: Config, arguments: Arguments, cache_data: Dict[str, Any], section: str
    ) -> None:
        try:
            host, port, ckey, user, password = self._config(config, arguments, section)

            with self._connection(host, port, user, password) as inst:
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


class _TarantoolCacheBackend(_CacheBackend):
    """
    Backend for caching data in Tarantool.
    """

    @staticmethod
    def _config(config: Config, arguments: Arguments, section: str) -> tuple:
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
                config, arguments, 'tarantool_host', section=section, default=_HOST),
            _config.get_config_value(
                config, arguments, 'tarantool_port', section=section, default=_TARANTOOL_PORT),
            _config.get_config_value(
                config, arguments, 'tarantool_space', section=section,
                default=_VULNERABILITIES_KEY if section == 'vulnerability' else _ARTIFACTS_KEY),
            _config.get_config_value(config, arguments, 'tarantool_user', section=section),
            _config.get_config_value(config, arguments, 'tarantool_password', section=section)
        )

    @contextmanager
    def _connection(
            self, host: str, port: int, user: Optional[str], password: Optional[str]
    ):
        """
        Context manager for Tarantool connection, ensuring proper cleanup.

        Args:
            host (str): Tarantool server host.
            port (int): Tarantool server port.
            user (Optional[str]): Tarantool username, if required.
            password (Optional[str]): Tarantool password, if required.

        Yields:
            tarantool.Connection: An instance of the Tarantool connection.

        Raises:
            tarantool.DatabaseError: If an error occurs during Tarantool operations.
        """
        conn = tarantool.Connection(host, port, user=user, password=password)
        try:
            yield conn
        finally:
            conn.close()

    def load(self, config: Config, arguments: Arguments, section: str) -> Dict[str, Any]:
        try:
            host, port, space, user, password = self._config(config, arguments, section)

            with self._connection(host, port, user, password) as conn:
                cache_data: Dict[str, Any] = {}
                if data := conn.select(space):
                    for item in data:
                        try:
                            cache_data[item[0]] = json.loads(item[1])
                        except json.JSONDecodeError as e:
                            logging.error(f"Failed to decode Tarantool data for key {item[0]}: {e}")
                return cache_data

        except tarantool.DatabaseError as e:  # pragma: no cover
            logging.error(f"Tarantool error: {e}")
        except Exception as e:
            logging.error(f"Failed to load cache from Tarantool: {e}")
        return {}

    def save(
            self, config: Config, arguments: Arguments, cache_data: Dict[str, Any], section: str
    ) -> None:
        try:
            host, port, space, user, password = self._config(config, arguments, section)

            with self._connection(host, port, user, password) as conn:
                space = conn.space(space)
                for key, value in cache_data.items():
                    space.replace((key, json.dumps(value, cls=DCJSONEncoder)))

        except tarantool.DatabaseError as e:  # pragma: no cover
            logging.error(f"Tarantool error: {e}")
        except Exception as e:
            logging.error(f"Failed to save cache to Tarantool: {e}")


class _MemcachedCacheBackend(_CacheBackend):
    """
    Backend for caching data in Memcached.
    """

    @staticmethod
    def _config(config: Config, arguments: Arguments, section: str) -> tuple:
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
                config, arguments, 'memcached_host', section=section, default=_HOST),
            _config.get_config_value(
                config, arguments, 'memcached_port', section=section, default=_MEMCACHED_PORT),
            _config.get_config_value(
                config, arguments, 'memcached_key', section=section,
                default=_VULNERABILITIES_KEY if section == 'vulnerability' else _ARTIFACTS_KEY)
        )

    @contextmanager
    def _connection(self, host: str, port: int):
        """
        Context manager for Memcached connection, ensuring proper cleanup.

        Args:
            host (str): Memcached server host.
            port (int): Memcached server port.

        Yields:
            pymemcache.client.base.Client: An instance of the Memcached client.

        Raises:
            pymemcache.exceptions.MemcacheError: If an error occurs during Memcached operations.
        """
        client = pymemcache.client.base.Client((host, port))
        try:
            yield client
        finally:
            client.close()

    def load(self, config: Config, arguments: Arguments, section: str) -> Dict[str, Any]:
        try:
            host, port, key = self._config(config, arguments, section)

            with self._connection(host, port) as client:
                if data := client.get(key):
                    try:
                        return json.loads(data)
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to decode Memcached data: {e}")

        except pymemcache.exceptions.MemcacheError as e:  # pragma: no cover
            logging.error(f"Memcached error: {e}")
        except Exception as e:
            logging.error(f"Failed to load cache from Memcached: {e}")
        return {}

    def save(
            self, config: Config, arguments: Arguments, cache_data: Dict[str, Any], section: str
    ) -> None:
        try:
            host, port, key = self._config(config, arguments, section)

            with self._connection(host, port) as client:
                client.set(key, json.dumps(cache_data, cls=DCJSONEncoder))

        except pymemcache.exceptions.MemcacheError as e:  # pragma: no cover
            logging.error(f"Memcached error: {e}")
        except Exception as e:
            logging.error(f"Failed to save cache to Memcached: {e}")


_CacheBackendRegistry.register('json', _JSONCacheBackend())
_CacheBackendRegistry.register('redis', _RedisCacheBackend())
_CacheBackendRegistry.register('tarantool', _TarantoolCacheBackend())
_CacheBackendRegistry.register('memcached', _MemcachedCacheBackend())


def load_cache(config: Config, arguments: Arguments, section: str = 'base') -> Dict[str, Any]:
    """
    Loads the cache data from the specified backend based on the configuration.
    Supports JSON, Redis, Tarantool, and Memcached backends.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        section (str, optional): Configuration section to use, such as 'base' or 'vulnerability'.
            Defaults to 'base'.

    Returns:
        Dict[str, Any]: Cache data as a dictionary.
            Returns an empty dictionary if the backend fails or no data is available.
            If the specified backend is not found, defaults to JSON backend.
    """
    key = _config.get_config_value(config, arguments, 'cache_backend', section=section)
    return _CacheBackendRegistry.get(key).load(config, arguments, section)


def save_cache(
        config: Config, arguments: Arguments, cache_data: Optional[Dict[str, Any]],
        section: str = 'base'
) -> None:
    """
    Saves the cache data to the specified backend based on the configuration.
    Supports JSON, Redis, Tarantool, and Memcached backends.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        cache_data (Optional[Dict[str, Any]]): Cache data to save.
        section (str, optional): Configuration section to use, such as 'base' or 'vulnerability'.
            Defaults to 'base'.
    """
    if cache_data is not None:
        key = _config.get_config_value(config, arguments, 'cache_backend', section=section)
        _CacheBackendRegistry.get(key).save(config, arguments, cache_data, section)


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
        version (Optional[str]): The current version of the artifact, or None if not specified or unresolved.

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
        with update_cache_artifact_lock:
            value = (math.trunc(time.time()), item, section_key, last_modified_date, versions[:3])
            cache_data[f"{group}:{artifact}"] = value
