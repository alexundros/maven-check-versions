#!/usr/bin/python3
"""Tests for package utility functions"""

import os
import sys

# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

# noinspection PyUnresolvedReferences
from maven_check_versions.utils import (  # noqa: E402
    get_config_value
)


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
