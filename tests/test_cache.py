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
    mocker.patch('builtins.open', mocker.mock_open(read_data='{"key": "value"}'))
    assert load_cache('test_cache.cache') == {'key': 'value'}

    mocker.patch('os.path.exists', return_value=False)
    assert load_cache('test_cache.cache') == {}
    mocker.stopall()


# noinspection PyShadowingNames
def test_save_cache(mocker):
    mock_open = mocker.patch('builtins.open')
    mock_json = mocker.patch('json.dump')
    save_cache({'key': 'value'}, 'test_cache.cache')
    mock_open.assert_called_once_with('test_cache.cache', 'w')
    mock_open_rv = mock_open.return_value.__enter__.return_value
    mock_json.assert_called_once_with({'key': 'value'}, mock_open_rv)
    mocker.stopall()


# noinspection PyShadowingNames
def test_process_cache(mocker):
    config = dict()
    data = {'group:artifact': (time.time() - 100, '1.0', 'key', '23.01.2025', ['1.0', '1.1'])}
    assert process_cache({'cache_time': 0}, data, config, 'artifact', 'group', '1.0')
    assert not process_cache({'cache_time': 50}, data, config, 'artifact', 'group', '1.1')

    mock = mocker.patch('logging.info')
    assert process_cache({'cache_time': 0}, data, config, 'artifact', 'group', '1.1')
    mock.assert_called_once_with('*key: group:artifact, current:1.1 versions: 1.0, 1.1 updated: 23.01.2025')


def test_update_cache():
    cache_data = {}
    update_cache(cache_data, ['1.0'], 'artifact', 'group', '1.0', '16.01.2025', 'key')  # NOSONAR
    data = (pytest.approx(time.time()), '1.0', 'key', '16.01.2025', ['1.0'])
    assert cache_data == {'group:artifact': data}
