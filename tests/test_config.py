#!/usr/bin/python3
"""Tests for package config functions"""

import os
import sys

# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

from maven_check_versions.config import (
    get_config, get_config_value, config_items
)


# noinspection PyShadowingNames
def test_get_config(mocker):
    mock_exists = mocker.patch('os.path.exists')
    mock_exists.side_effect = [False, True]
    mocker.patch('builtins.open', mocker.mock_open(read_data="base:"))
    mock_logging = mocker.patch('logging.info')
    get_config({})
    mock_logging.assert_called_once()
    mocker.stopall()


# noinspection PyShadowingNames
def test_get_config_value(mocker, monkeypatch):
    config = {'base': {'key': 'true'}}
    assert get_config_value(config, {}, 'key', value_type=bool) is True
    config = {'base': {'key': 'true'}}
    assert get_config_value(config, {'key': False}, 'key', value_type=bool) is False
    monkeypatch.setenv('CV_KEY', 'true')
    config = {'base': {'key': 'true'}}
    assert get_config_value(config, {'key': False}, 'key', value_type=bool) is True
    config = {'base': {'key': '123'}}
    assert get_config_value(config, {}, 'key', value_type=int) == 123
    config = {'base': {'key': '123.45'}}
    assert get_config_value(config, {}, 'key', value_type=float) == 123.45  # NOSONAR
    config = {'base': {'key': 'value'}}
    assert get_config_value(config, {}, 'key') == 'value'


def test_config_items():
    config = {'base': {'key': 'value'}}
    assert config_items(config, 'base') == [('key', 'value')]
    assert config_items(config, 'other') == []
    assert config_items(config, 'empty') == []
