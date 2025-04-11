#!/usr/bin/python3
"""Tests for package utility functions"""

import os
import sys
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET

import pytest
# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

# noinspection PyUnresolvedReferences
from maven_check_versions.utils import (  # noqa: E402
    parse_command_line, get_artifact_name, collect_dependencies,
    get_dependency_identifiers, fail_mode_if_required, resolve_version,
    get_version, check_versions, get_pom_data, get_pom_tree
)
from maven_check_versions.config import Arguments, Config

ns_mappings = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}  # NOSONAR


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


# noinspection PyShadowingNames
def test_collect_dependencies(mocker):
    root = ET.fromstring("""
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
    """.lstrip())
    args = Arguments({'search_plugins': True})
    result = collect_dependencies(root, ns_mappings, Config(), args)
    assert len(result) == 3


def test_get_dependency_identifiers():
    dependency = ET.fromstring("""
    <?xml version="1.0" encoding="UTF-8"?>
    <dependency xmlns="http://maven.apache.org/POM/4.0.0">
        <groupId>groupId</groupId>
        <artifactId>artifactId</artifactId>
        <version>1.0</version>
    </dependency>
    """.lstrip())
    group, artifact = get_dependency_identifiers(dependency, ns_mappings)
    assert group == 'groupId' and artifact == 'artifactId'


# noinspection PyShadowingNames
def test_fail_mode_if_required(mocker):
    mock_logging = mocker.patch('logging.warning')
    with pytest.raises(AssertionError):
        config = Config()
        args = Arguments({'fail_mode': True, 'fail_major': 2, 'fail_minor': 2})
        fail_mode_if_required(config, 1, 0, '4.0', 2, 2, args, '1.0')
    mock_logging.assert_called_once_with("Fail version: 4.0 > 1.0")


def test_resolve_version():
    root = ET.fromstring("""
    <?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <properties>
            <lib.version>1.0</lib.version>
        </properties>
    </project>
    """.lstrip())
    version = resolve_version('${lib.version}', root, ns_mappings)
    assert version == '1.0'


def test_get_version():
    root = ET.fromstring("""
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
    """.lstrip())
    args = Arguments({'empty_version': False})
    deps = root.findall('.//xmlns:dependency', namespaces=ns_mappings)
    version, skip_flag = get_version(Config(), args, ns_mappings, root, deps[0])
    assert version is None and skip_flag

    version, skip_flag = get_version(Config(), args, ns_mappings, root, deps[1])
    assert version == '1.0' and not skip_flag

    version, skip_flag = get_version(Config(), args, ns_mappings, root, deps[2])
    assert version == '${dependency.version}' and skip_flag


# noinspection PyShadowingNames
def test_check_versions(mocker):
    def _check_versions(pa, data, item, vers):
        return check_versions(
            data, Config(), pa, 'group', 'artifact', item,
            'repo_section', 'path', None, True, vers, mocker.Mock()
        )

    mock_get_pom_data = mocker.patch('maven_check_versions.utils.get_pom_data')
    mock_get_pom_data.return_value = (True, '2025-01-25')
    args = Arguments({
        'skip_current': True, 'fail_mode': True,
        'fail_major': 0, 'fail_minor': 1
    })
    cache_data = {}
    assert _check_versions(args, cache_data, '1.1', ['1.1'])
    assert cache_data['group:artifact'][1] == '1.1'

    with pytest.raises(AssertionError):
        args['fail_minor'] = 0
        assert _check_versions(args, cache_data, '1.1', ['1.2'])

    args['fail_mode'] = False
    assert _check_versions(args, cache_data, '1.1', ['1.2'])

    mock_get_pom_data.return_value = (False, None)
    assert not _check_versions(args, cache_data, '1.1', ['1.2'])


# noinspection PyShadowingNames
def test_get_pom_data(mocker):
    pom_path = 'http://example.com/pom.pom'  # NOSONAR
    headers = {'Last-Modified': 'Wed, 18 Jan 2025 12:00:00 GMT'}
    mock_response = mocker.Mock(status_code=200, headers=headers)
    mock_requests = mocker.patch('requests.Session.get', return_value=mock_response)
    is_valid, last_modified = get_pom_data(None, True, 'artifact', '1.0', pom_path)
    assert is_valid is True and last_modified == '2025-01-18'

    mock_requests.return_value = mocker.Mock(status_code=404)
    is_valid, last_modified = get_pom_data(None, True, 'artifact', '1.0', pom_path)
    assert is_valid is False and last_modified is None


# noinspection PyShadowingNames
def test_get_pom_tree(mocker):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <groupId>group</groupId>
        <artifactId>artifact</artifactId>
        <version>1.0</version>
    </project>
    """
    config = Config({'pom_http': {'auth': 'true'}})
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.path.isfile', return_value=True)
    mock_open = mocker.patch('builtins.open', mocker.mock_open(read_data=xml))
    tree = get_pom_tree('pom.xml', True, config, Arguments())
    mock_open.assert_called_once_with('pom.xml', 'rb')
    assert isinstance(tree, ET.ElementTree)

    mocker.patch('os.path.exists', return_value=False)
    with pytest.raises(FileNotFoundError):
        get_pom_tree('pom.xml', True, config, Arguments())

    pom_path = 'http://example.com/pom.pom'  # NOSONAR
    mock_response = mocker.Mock(status_code=200, text=xml)
    mock_requests = mocker.patch('requests.Session.get', return_value=mock_response)
    assert isinstance(get_pom_tree(pom_path, True, config, Arguments()), ET.ElementTree)

    mock_requests.return_value.status_code = 404
    with pytest.raises(FileNotFoundError):
        get_pom_tree(pom_path, True, config, Arguments())
