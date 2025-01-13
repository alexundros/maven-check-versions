#!/usr/bin/python3
"""Tests for maven_check_versions package"""
import os
import sys

# noinspection PyUnresolvedReferences
from pytest_mock import mocker

# noinspection PyPep8Naming
import xml.etree.ElementTree as ET

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

# noinspection PyUnresolvedReferences
from maven_check_versions import (  # noqa: E402
    parse_command_line_arguments, load_cache, save_cache,
    get_artifact_name
)


# noinspection PyShadowingNames
def test_parse_command_line_arguments(mocker):
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
    args = parse_command_line_arguments()
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


def test_load_cache(mocker):
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', mocker.mock_open(read_data='{"key": "value"}'))

    assert load_cache('test_cache.cache') == {'key': 'value'}


def test_load_cache_if_path_not_exists(mocker):
    mocker.patch('os.path.exists', return_value=False)

    assert load_cache('test_cache.cache') == {}


def test_save_cache(mocker):
    mock_open = mocker.patch('builtins.open')
    mock_json_dump = mocker.patch('json.dump')

    cache_data = {'key': 'value'}
    save_cache(cache_data, 'test_cache.cache')

    mock_open.assert_called_once_with('test_cache.cache', 'w')
    mock_open_rv = mock_open.return_value.__enter__.return_value
    mock_json_dump.assert_called_once_with(cache_data, mock_open_rv)


def test_get_artifact_name():
    xml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <groupId>groupId</groupId>
        <artifactId>artifactId</artifactId>
        <version>1.0</version>
    </project>
    """
    root = ET.ElementTree(ET.fromstring(xml.lstrip())).getroot()
    result = get_artifact_name(root, {'xmlns': 'http://maven.apache.org/POM/4.0.0'})

    assert result == "groupId:artifactId"
