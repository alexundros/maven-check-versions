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
    get_artifact_name, get_dependency_identifiers, collect_dependencies,
    resolve_version, get_version
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
    mapping = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
    result = get_artifact_name(ET.fromstring(xml.lstrip()), mapping)

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
    mapping = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
    artifact_id, group_id = get_dependency_identifiers(dependency, mapping)

    assert artifact_id == 'artifactId'
    assert group_id == 'groupId'


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
    mapping = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
    result = collect_dependencies(root, mapping, mocker.Mock(), {'search_plugins': True})

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
    mapping = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
    version_text = resolve_version('${lib.version}', ET.fromstring(xml.lstrip()), mapping)
    assert version_text == '1.0'


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
    mapping = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
    deps = root.findall('.//xmlns:dependency', namespaces=mapping)

    version, skip_flag = get_version(mocker.Mock(), args, mapping, root, deps[0])
    assert version is None and skip_flag

    version, skip_flag = get_version(mocker.Mock(), args, mapping, root, deps[1])
    assert version == '1.0' and not skip_flag

    version, skip_flag = get_version(mocker.Mock(), args, mapping, root, deps[2])
    assert version == '${dependency.version}' and skip_flag
