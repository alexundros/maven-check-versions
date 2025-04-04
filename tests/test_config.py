#!/usr/bin/python3
"""Tests for package config functions"""

import os
import sys

# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

from maven_check_versions.config import (
    get_config, get_config_value, config_items, Config, Arguments
)


# noinspection PyShadowingNames
def test_get_config(mocker):
    mock_exists = mocker.patch('os.path.exists')
    mock_exists.side_effect = [False, True]
    mocker.patch('builtins.open', mocker.mock_open(read_data="base:"))
    mock_logging = mocker.patch('logging.info')
    get_config(Arguments())
    mock_logging.assert_called_once()
    mocker.stopall()


# noinspection PyShadowingNames
def test_get_config_value(monkeypatch):
    config = Config({'base': {'key': True}, 'other': {'key': False}})
    assert get_config_value(config, Arguments(), 'key') is True
    assert get_config_value(config, Arguments(), 'val', default=True) is True
    assert get_config_value(config, Arguments({'key': False}), 'key') is False
    assert get_config_value(config, Arguments(), 'val') is None
    monkeypatch.setenv('CV_KEY', 'false')
    assert get_config_value(config, Arguments({'key': None}), 'key') is False
    monkeypatch.setenv('CV_KEY', 'true')
    assert get_config_value(config, Arguments({'key': None}), 'key') is True
    assert get_config_value(config, Arguments({'key': False}), 'key') is False
    monkeypatch.setenv('CV_OTHER_KEY', 'true')
    assert get_config_value(config, Arguments(), 'key', section='other') is True
    monkeypatch.undo()
    config = Config({'base': {'key': 123}})
    assert get_config_value(config, Arguments(), 'key') == 123
    assert get_config_value(config, Arguments(), 'val', default=123) == 123
    config = Config({'base': {'key': 123.45}})
    assert get_config_value(config, Arguments(), 'key') == 123.45  # NOSONAR
    assert get_config_value(config, Arguments(), 'val', default=123.45) == 123.45  # NOSONAR
    config = Config({'base': {'key': 'value'}})
    assert get_config_value(config, Arguments(), 'key') == 'value'
    assert get_config_value(config, Arguments(), 'val', default='value') == 'value'
    assert get_config_value(config, Arguments(), 'val', default=[]) == []
    assert get_config_value(config, Arguments(), 'val', default=()) == ()
    assert get_config_value(config, Arguments(), 'val', default={'k': 'v'}) == {'k': 'v'}


def test_config_items():
    config = Config({'base': {'key': 'value'}})
    assert config_items(config, 'base') == [('key', 'value')]
    assert config_items(config, 'other') == []
    assert config_items(config, 'empty') == []
