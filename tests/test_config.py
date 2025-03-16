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
def test_get_config_value(monkeypatch):
    config = {'base': {'key': True}}
    assert get_config_value(config, {}, 'key') is True
    assert get_config_value(config, {}, 'val', default=True) is True
    assert get_config_value(config, {'key': False}, 'key') is False
    assert get_config_value(config, {}, 'val') is None
    monkeypatch.setenv('CV_KEY', 'true')
    assert get_config_value(config, {'key': False}, 'key') is True
    monkeypatch.setenv('CV_KEY', 'false')
    assert get_config_value(config, {'key': True}, 'key') is False
    config = {'base': {'key': 123}}
    assert get_config_value(config, {}, 'key') == 123
    assert get_config_value(config, {}, 'val', default=123) == 123
    config = {'base': {'key': 123.45}}
    assert get_config_value(config, {}, 'key') == 123.45  # NOSONAR
    assert get_config_value(config, {}, 'val', default=123.45) == 123.45  # NOSONAR
    config = {'base': {'key': 'value'}}
    assert get_config_value(config, {}, 'key') == 'value'
    assert get_config_value(config, {}, 'val', default='value') == 'value'
    assert get_config_value(config, {}, 'val', default=[]) == []
    assert get_config_value(config, {}, 'val', default=()) == ()
    assert get_config_value(config, {}, 'val', default={'k': 'v'}) == {'k': 'v'}


def test_config_items():
    config = {'base': {'key': 'value'}}
    assert config_items(config, 'base') == [('key', 'value')]
    assert config_items(config, 'other') == []
    assert config_items(config, 'empty') == []
