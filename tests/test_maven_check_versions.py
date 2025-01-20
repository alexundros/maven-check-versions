#!/usr/bin/python3
"""Tests for maven_check_versions package"""
import os
import sys
import time
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from configparser import ConfigParser

import pytest
# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

# noinspection PyUnresolvedReferences
from maven_check_versions import (  # noqa: E402
    parse_command_line_arguments, load_cache, save_cache, get_artifact_name,
    get_dependency_identifiers, collect_dependencies, resolve_version,
    get_version, get_config_value, update_cache_data, config_items,
    log_skip_if_required, log_search_if_required, log_invalid_if_required,
    fail_mode_if_required, pom_data
)

ns_mappings = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}


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
    result = get_artifact_name(ET.fromstring(xml.lstrip()), ns_mappings)
    assert result == "groupId:artifactId"


def test_get_dependency_identifiers():
    xml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <dependency xmlns="http://maven.apache.org/POM/4.0.0">
        <groupId>groupId</groupId>
        <artifactId>artifactId</artifactId>
        <version>1.0</version>
    </dependency>
    """
    dependency = ET.fromstring(xml.lstrip())
    artifact, group = get_dependency_identifiers(dependency, ns_mappings)
    assert artifact == 'artifactId' and group == 'groupId'


def test_collect_dependencies(mocker):
    xml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <dependencies>
            <dependency>
                <groupId>groupId</groupId>
                <artifactId>artifactId</artifactId>
            </dependency>
            <dependency>
                <groupId>groupId</groupId>
                <artifactId>artifactId</artifactId>
            </dependency>
        </dependencies> 
        <build>
            <plugins>
            <plugin>
                <groupId>groupId</groupId>
                <artifactId>artifactId</artifactId>
            </plugin>
            </plugins>
        </build>
    </project>
    """
    root = ET.fromstring(xml.lstrip())
    args = {'search_plugins': True}
    result = collect_dependencies(root, ns_mappings, mocker.Mock(), args)
    assert len(result) == 3


def test_resolve_version():
    xml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <properties>
            <lib.version>1.0</lib.version>
        </properties>
    </project>
    """
    root = ET.fromstring(xml.lstrip())
    version = resolve_version('${lib.version}', root, ns_mappings)
    assert version == '1.0'


def test_get_version(mocker):
    xml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <version>1.0</version>
        <dependencies>
            <dependency>
                <artifactId>dependency</artifactId>
            </dependency>
            <dependency>
                <artifactId>dependency</artifactId>
                <version>${project.version}</version>
            </dependency>
            <dependency>
                <artifactId>dependency</artifactId>
                <version>${dependency.version}</version>
            </dependency>
        </dependencies> 
    </project>
    """
    root = ET.fromstring(xml.lstrip())
    args = {'empty_version': False}
    deps = root.findall('.//xmlns:dependency', namespaces=ns_mappings)
    version, skip_flag = get_version(mocker.Mock(), args, ns_mappings, root, deps[0])
    assert version is None and skip_flag
    version, skip_flag = get_version(mocker.Mock(), args, ns_mappings, root, deps[1])
    assert version == '1.0' and not skip_flag
    version, skip_flag = get_version(mocker.Mock(), args, ns_mappings, root, deps[2])
    assert version == '${dependency.version}' and skip_flag


def test_get_config_value(mocker):
    mock = mocker.Mock()
    mock.get.return_value = 'true'
    assert get_config_value(mock, {}, 'key', value_type=bool) == True
    mock.get.return_value = 'true'
    assert get_config_value(mock, {'key': False}, 'key', value_type=bool) == False
    mock.get.return_value = '123'
    assert get_config_value(mock, {}, 'key', value_type=int) == 123
    mock.get.return_value = '123.45'
    assert get_config_value(mock, {}, 'key', value_type=float) == 123.45
    mock.get.return_value = 'value'
    assert get_config_value(mock, {}, 'key') == 'value'


def test_update_cache_data():
    cache_data = {}
    update_cache_data(cache_data, ['1.0'], 'artifact', 'group', '1.0', '16.01.2025', 'key')
    data = (pytest.approx(time.time()), '1.0', 'key', '16.01.2025', ['1.0'])
    assert cache_data == {'group:artifact': data}


def test_config_items():
    config_parser = ConfigParser()
    config_parser.optionxform = str
    config_parser.read_string("""
    [base]
    key = value
    """)
    assert config_items(config_parser, 'base') == [('key', 'value')]
    assert config_items(config_parser, 'other') == []


def test_log_skip_if_required(mocker):
    mock_logging = mocker.patch('logging.warning')
    args = {'show_skip': True}
    log_skip_if_required(mocker.Mock(), args, 'group', 'artifact', '1.0')
    mock_logging.assert_called_once_with("Skip: group:artifact:1.0")


def test_log_search_if_required(mocker):
    mock_logging = mocker.patch('logging.warning')
    args = {'show_search': True}
    log_search_if_required(mocker.Mock(), args, 'group', 'artifact', '${version}')
    mock_logging.assert_called_once_with("Search: group:artifact:${version}")


def test_log_invalid_if_required(mocker):
    mock_logging = mocker.patch('logging.warning')
    args = {'show_invalid': True}
    log_invalid_if_required(mocker.Mock(), args, mocker.Mock(), 'group', 'artifact', '1.0', False)
    mock_logging.assert_called_once_with("Invalid: group:artifact:1.0")


def test_fail_mode_if_required(mocker):
    mock_logging = mocker.patch('logging.warning')
    with pytest.raises(AssertionError):
        config_parser = ConfigParser()
        args = {'fail_mode': True, 'fail_major': 2, 'fail_minor': 2}
        fail_mode_if_required(config_parser, 1, 0, '4.0', 2, 2, args, '1.0')
    mock_logging.assert_called_once_with("Fail version: 4.0 > 1.0")


def test_pom_data(mocker):
    response = mocker.Mock(status_code=200, headers={'Last-Modified': 'Wed, 18 Jan 2025 12:00:00 GMT'})
    mocker.patch('requests.get', return_value=response)
    is_valid, last_modified = pom_data((), True, 'artifact', '1.0', 'http://example.com/pom.pom')
    assert is_valid is True and last_modified == '2025-01-18'
