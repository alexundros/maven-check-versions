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
    parse_command_line,
    get_config_value,
    get_artifact_name
)

ns_mappings = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}


# noinspection PyShadowingNames
def test_parse_command_line(mocker):
    mocker.patch(
        'argparse.ArgumentParser.parse_args',
        return_value=mocker.Mock(
            ci_mode=True,
            pom_file='pom.xml',
            find_artifact='artifact',
            cache_off=True,
            cache_file='cache.json',
            cache_time=3600,
            logfile_off=True,
            log_file='log.txt',
            config_file='config.cfg',
            fail_mode=True,
            fail_major=1,
            fail_minor=2,
            search_plugins=True,
            process_modules=True,
            show_skip=True,
            show_search=True,
            empty_version=True,
            show_invalid=True,
            user='user',
            password='password'
        ))
    args = parse_command_line()
    assert args['ci_mode'] is True
    assert args['pom_file'] == 'pom.xml'
    assert args['find_artifact'] == 'artifact'
    assert args['cache_off'] is True
    assert args['cache_file'] == 'cache.json'
    assert args['cache_time'] == 3600
    assert args['logfile_off'] is True
    assert args['log_file'] == 'log.txt'
    assert args['config_file'] == 'config.cfg'
    assert args['fail_mode'] is True
    assert args['fail_major'] == 1
    assert args['fail_minor'] == 2
    assert args['search_plugins'] is True
    assert args['process_modules'] is True
    assert args['show_skip'] is True
    assert args['show_search'] is True
    assert args['empty_version'] is True
    assert args['show_invalid'] is True
    assert args['user'] == 'user'
    assert args['password'] == 'password'


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
