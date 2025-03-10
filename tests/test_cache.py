#!/usr/bin/python3
"""Tests for package cache functions"""

import os
import sys
import time

import pytest
# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

from maven_check_versions.cache import (
    load_cache, save_cache, update_cache, process_cache
)


# noinspection PyShadowingNames
def test_load_cache(mocker):
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', mocker.mock_open(read_data='{"k": "v"}'))
    assert load_cache({}, {}) == {'k': 'v'}

    mocker.patch('os.path.exists', return_value=False)
    assert load_cache({}, {}) == {}

    mock_redis = mocker.patch('redis.Redis')
    mock_redis.return_value.hgetall.return_value = {'key': '{"k":"v"}'}
    assert load_cache({'base': {'cache_backend': 'redis'}}, {}) == {'key': {'k': 'v'}}

    mock_redis.side_effect = Exception
    assert load_cache({'base': {'cache_backend': 'redis'}}, {}) == {}

    mock_tarantool = mocker.patch('tarantool.connect')
    space = mock_tarantool.return_value.space
    space.return_value.select.return_value = [('key', '{"k":"v"}')]
    assert load_cache({'base': {'cache_backend': 'tarantool'}}, {}) == {'key': {'k': 'v'}}

    mock_tarantool.side_effect = Exception
    assert load_cache({'base': {'cache_backend': 'tarantool'}}, {}) == {}
    mocker.stopall()


# noinspection PyShadowingNames
def test_save_cache(mocker):
    mock_open = mocker.patch('builtins.open')
    mock_json = mocker.patch('json.dump')
    save_cache({}, {}, {'k': 'v'})
    mock_open.assert_called_once_with('maven_check_versions.cache.json', 'w')
    mock_open_rv = mock_open.return_value.__enter__.return_value
    mock_json.assert_called_once_with({'k': 'v'}, mock_open_rv)

    mock_redis = mocker.patch('redis.Redis')
    save_cache({'base': {'cache_backend': 'redis'}}, {}, {'k': 'v'})

    mock_redis.side_effect = Exception
    save_cache({'base': {'cache_backend': 'redis'}}, {}, {'k': 'v'})

    mock_tarantool = mocker.patch('tarantool.connect')
    save_cache({'base': {'cache_backend': 'tarantool'}}, {}, {'k': 'v'})

    mock_tarantool.side_effect = Exception
    save_cache({'base': {'cache_backend': 'tarantool'}}, {}, {'k': 'v'})
    mocker.stopall()


# noinspection PyShadowingNames
def test_process_cache(mocker):
    config = dict()
    data = {'group:artifact': (time.time() - 100, '1.0', 'key', '23.01.2025', ['1.0', '1.1'])}
    assert process_cache(config, {'cache_time': 0}, data, 'artifact', 'group', '1.0')
    assert not process_cache(config, {'cache_time': 50}, data, 'artifact', 'group', '1.1')

    mock = mocker.patch('logging.info')
    assert process_cache(config, {'cache_time': 0}, data, 'artifact', 'group', '1.1')
    mock.assert_called_once_with('*key: group:artifact, current:1.1 versions: 1.0, 1.1 updated: 23.01.2025')


def test_update_cache():
    cache_data = {}
    update_cache(cache_data, ['1.0'], 'artifact', 'group', '1.0', '16.01.2025', 'key')  # NOSONAR
    data = (pytest.approx(time.time()), '1.0', 'key', '16.01.2025', ['1.0'])
    assert cache_data == {'group:artifact': data}
