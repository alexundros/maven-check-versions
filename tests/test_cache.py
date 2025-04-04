#!/usr/bin/python3
"""Tests for package cache functions"""

import os
import sys
import time
from json import JSONDecodeError

import pytest
# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

from maven_check_versions.config import Config, Arguments
from maven_check_versions.cache import (
    load_cache, save_cache, update_cache_artifact,
    process_cache_artifact, DCJSONEncoder
)


# noinspection PyShadowingNames
def test_load_cache(mocker):
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', mocker.mock_open(read_data='{"k": "v"}'))
    assert load_cache(Config(), Arguments()) == {'k': 'v'}

    mocker.patch('json.load').side_effect = JSONDecodeError('error', 'error', 0)
    assert load_cache(Config(), Arguments()) == {}

    mocker.patch('os.path.exists', return_value=False)
    assert load_cache(Config(), Arguments()) == {}

    mock_redis = mocker.patch('redis.Redis')
    mock_redis.return_value.hgetall.return_value = {'key': '{"k":"v"}'}
    assert load_cache(Config({'base': {'cache_backend': 'redis'}}), Arguments()) == {'key': {'k': 'v'}}

    mock_loads = mocker.patch('json.loads')
    mock_loads.side_effect = JSONDecodeError('error', 'error', 0)
    assert load_cache(Config({'base': {'cache_backend': 'redis'}}), Arguments()) == {}
    mocker.stop(mock_loads)

    mock_redis.side_effect = Exception
    assert load_cache(Config({'base': {'cache_backend': 'redis'}}), Arguments()) == {}

    mock_tarantool = mocker.patch('tarantool.Connection')
    mock_tarantool.return_value.select.return_value = [('key', '{"k":"v"}')]
    assert load_cache(Config({'base': {'cache_backend': 'tarantool'}}), Arguments()) == {'key': {'k': 'v'}}

    mock_loads = mocker.patch('json.loads')
    mock_loads.side_effect = JSONDecodeError('error', 'error', 0)
    assert load_cache(Config({'base': {'cache_backend': 'tarantool'}}), Arguments()) == {}
    mocker.stop(mock_loads)

    mock_tarantool.side_effect = Exception
    assert load_cache(Config({'base': {'cache_backend': 'tarantool'}}), Arguments()) == {}

    mock_memcache = mocker.patch('pymemcache.client.base.Client')
    mock_memcache.return_value.get.return_value = '{"k":"v"}'
    assert load_cache(Config({'base': {'cache_backend': 'memcached'}}), Arguments()) == {'k': 'v'}

    mock_loads = mocker.patch('json.loads')
    mock_loads.side_effect = JSONDecodeError('error', 'error', 0)
    assert load_cache(Config({'base': {'cache_backend': 'memcached'}}), Arguments()) == {}
    mocker.stop(mock_loads)

    mock_memcache.side_effect = Exception
    assert load_cache(Config({'base': {'cache_backend': 'memcached'}}), Arguments()) == {}
    mocker.stopall()


# noinspection PyShadowingNames
def test_save_cache(mocker):
    mock_open = mocker.patch('builtins.open')
    mock_json = mocker.patch('json.dumps')
    save_cache(Config(), Arguments(), {'k': 'v'})
    mock_open.assert_called_once_with('maven_check_versions_artifacts.json', 'w', encoding='utf-8')
    mock_json.assert_called_once_with({'k': 'v'}, cls=DCJSONEncoder)

    mock_json.side_effect = Exception
    save_cache(Config(), Arguments(), {'k': 'v'})

    mock_redis = mocker.patch('redis.Redis')
    save_cache(Config({'base': {'cache_backend': 'redis'}}), Arguments(), {'k': 'v'})

    mock_redis.side_effect = Exception
    save_cache(Config({'base': {'cache_backend': 'redis'}}), Arguments(), {'k': 'v'})

    mock_tarantool = mocker.patch('tarantool.Connection')
    save_cache(Config({'base': {'cache_backend': 'tarantool'}}), Arguments(), {'k': 'v'})

    mock_tarantool.side_effect = Exception
    save_cache(Config({'base': {'cache_backend': 'tarantool'}}), Arguments(), {'k': 'v'})

    mock_memcache = mocker.patch('pymemcache.client.base.Client')
    save_cache(Config({'base': {'cache_backend': 'memcached'}}), Arguments(), {'k': 'v'})

    mock_memcache.side_effect = Exception
    save_cache(Config({'base': {'cache_backend': 'memcached'}}), Arguments(), {'k': 'v'})
    mocker.stopall()


# noinspection PyShadowingNames
def test_process_cache_artifact(mocker):
    config = Config()
    data = {'group:artifact': (time.time() - 100, '1.0', 'key', '23.01.2025', ['1.0', '1.1'])}
    assert process_cache_artifact(config, Arguments({'cache_time': 0}), data, 'artifact', 'group', '1.0')
    assert not process_cache_artifact(config, Arguments({'cache_time': 50}), data, 'artifact', 'group', '1.1')

    mock = mocker.patch('logging.info')
    assert process_cache_artifact(config, Arguments({'cache_time': 0}), data, 'artifact', 'group', '1.1')
    mock.assert_called_once_with('*key: group:artifact, current:1.1 versions: 1.0, 1.1 updated: 23.01.2025')

    assert not process_cache_artifact(config, Arguments(), {}, 'artifact', 'group', '1.1')


def test_update_cache_artifact():
    cache_data = {}
    update_cache_artifact(cache_data, ['1.0'], 'artifact', 'group', '1.0', '16.01.2025', 'key')  # NOSONAR
    data = (pytest.approx(time.time()), '1.0', 'key', '16.01.2025', ['1.0'])
    assert cache_data == {'group:artifact': data}
