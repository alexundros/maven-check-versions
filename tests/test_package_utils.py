#!/usr/bin/python3
"""Tests for package utility functions"""

import os
import sys
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET

# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

# noinspection PyUnresolvedReferences
from maven_check_versions.utils import (  # noqa: E402
    get_config_value,
    get_artifact_name
)

ns_mappings = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}


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


def test_get_artifact_name():
    root = ET.fromstring("""
    <?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <groupId>groupId</groupId>
        <artifactId>artifactId</artifactId>
        <version>1.0</version>
    </project>
    """.lstrip())
    result = get_artifact_name(root, ns_mappings)
    assert result == "groupId:artifactId"
