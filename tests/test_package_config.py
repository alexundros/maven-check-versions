#!/usr/bin/python3
"""Tests for package config functions"""

import os
import sys
from configparser import ConfigParser

# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

from maven_check_versions.config import (
    get_config_parser, get_config_value, config_items
)


# noinspection PyShadowingNames
def test_get_config_parser(mocker):
    mock_exists = mocker.patch('os.path.exists')
    mock_exists.side_effect = [False, True]
    mocker.patch('builtins.open', mocker.mock_open(read_data="[base]"))
    mock_logging = mocker.patch('logging.info')
    config_parser = get_config_parser({})
    assert isinstance(config_parser, ConfigParser)
    mock_logging.assert_called_once()
    mocker.stopall()


# noinspection PyShadowingNames
def test_get_config_value(mocker, monkeypatch):
    mock = mocker.Mock()
    mock.get.return_value = 'true'
    assert get_config_value(mock, {}, 'key', value_type=bool) == True

    mock.get.return_value = 'true'
    assert get_config_value(mock, {'key': False}, 'key', value_type=bool) == False

    monkeypatch.setenv('CV_KEY', 'true')
    assert get_config_value(mock, {'key': False}, 'key', value_type=bool) == True

    mock.get.return_value = '123'
    assert get_config_value(mock, {}, 'key', value_type=int) == 123

    mock.get.return_value = '123.45'
    assert get_config_value(mock, {}, 'key', value_type=float) == 123.45  # NOSONAR

    mock.get.return_value = 'value'
    assert get_config_value(mock, {}, 'key') == 'value'


def test_config_items():
    config_parser = ConfigParser()
    config_parser.optionxform = str
    config_parser.read_string("[base]\nkey = value\n[empty]")
    assert config_items(config_parser, 'base') == [('key', 'value')]
    assert config_items(config_parser, 'other') == []
    assert config_items(config_parser, 'empty') == []
