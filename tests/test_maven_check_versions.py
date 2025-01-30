#!/usr/bin/python3
"""Tests for maven_check_versions package"""
import logging
import os
import sys
import time
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from configparser import ConfigParser
from pathlib import PurePath

import pytest
# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

# noinspection PyUnresolvedReferences
from maven_check_versions import (  # noqa: E402
    parse_command_line_arguments, load_cache, save_cache, get_artifact_name,
    get_dependency_identifiers, collect_dependencies, resolve_version,
    get_version, get_config_value, update_cache_data, process_cached_data,
    config_items, log_skip_if_required, log_search_if_required,
    log_invalid_if_required, fail_mode_if_required, pom_data, load_pom_tree,
    configure_logging, check_versions, service_rest, process_repository,
    process_repositories, process_modules_if_required, find_artifact,
    process_dependencies
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

    mocker.patch('os.path.exists', return_value=False)
    assert load_cache('test_cache.cache') == {}


def test_save_cache(mocker):
    mock_open = mocker.patch('builtins.open')
    mock_json = mocker.patch('json.dump')
    save_cache({'key': 'value'}, 'test_cache.cache')
    mock_open.assert_called_once_with('test_cache.cache', 'w')
    mock_open_rv = mock_open.return_value.__enter__.return_value
    mock_json.assert_called_once_with({'key': 'value'}, mock_open_rv)


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


def test_get_dependency_identifiers():
    dependency = ET.fromstring("""
    <?xml version="1.0" encoding="UTF-8"?>
    <dependency xmlns="http://maven.apache.org/POM/4.0.0">
        <groupId>groupId</groupId>
        <artifactId>artifactId</artifactId>
        <version>1.0</version>
    </dependency>
    """.lstrip())
    artifact, group = get_dependency_identifiers(dependency, ns_mappings)
    assert artifact == 'artifactId' and group == 'groupId'


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
    args = {'search_plugins': True}
    result = collect_dependencies(root, ns_mappings, mocker.Mock(), args)
    assert len(result) == 3


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


def test_get_version(mocker):
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
    args = {'empty_version': False}
    deps = root.findall('.//xmlns:dependency', namespaces=ns_mappings)
    version, skip_flag = get_version(mocker.Mock(), args, ns_mappings, root, deps[0])
    assert version is None and skip_flag

    version, skip_flag = get_version(mocker.Mock(), args, ns_mappings, root, deps[1])
    assert version == '1.0' and not skip_flag

    version, skip_flag = get_version(mocker.Mock(), args, ns_mappings, root, deps[2])
    assert version == '${dependency.version}' and skip_flag


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
    assert get_config_value(mock, {}, 'key', value_type=float) == 123.45

    mock.get.return_value = 'value'
    assert get_config_value(mock, {}, 'key') == 'value'


def test_update_cache_data():
    cache_data = {}
    update_cache_data(cache_data, ['1.0'], 'artifact', 'group', '1.0', '16.01.2025', 'key')
    data = (pytest.approx(time.time()), '1.0', 'key', '16.01.2025', ['1.0'])
    assert cache_data == {'group:artifact': data}


def test_process_cached_data(mocker):
    config_parser = ConfigParser()
    data = {'group:artifact': (time.time() - 100, '1.0', 'key', '23.01.2025', ['1.0', '1.1'])}
    assert process_cached_data({'cache_time': 0}, data, config_parser, 'artifact', 'group', '1.0')
    assert not process_cached_data({'cache_time': 50}, data, config_parser, 'artifact', 'group', '1.1')

    mock = mocker.patch('logging.info')
    assert process_cached_data({'cache_time': 0}, data, config_parser, 'artifact', 'group', '1.1')
    mock.assert_called_once_with('*key: group:artifact, current:1.1 versions: 1.0, 1.1 updated: 23.01.2025')


def test_config_items():
    config_parser = ConfigParser()
    config_parser.optionxform = str
    config_parser.read_string("[base]\nkey = value\n[empty]")
    assert config_items(config_parser, 'base') == [('key', 'value')]
    assert config_items(config_parser, 'other') == []
    assert config_items(config_parser, 'empty') == []


def test_log_skip_if_required(mocker):
    mock_logging = mocker.patch('logging.warning')
    args = {'show_skip': True}
    log_skip_if_required(mocker.Mock(), args, 'group', 'artifact', '1.0')
    mock_logging.assert_called_once_with("Skip: group:artifact:1.0")


def test_log_search_if_required(mocker):
    args = {'show_search': True}
    mock_logging = mocker.patch('logging.warning')
    log_search_if_required(mocker.Mock(), args, 'group', 'artifact', '${version}')
    mock_logging.assert_called_once_with("Search: group:artifact:${version}")

    mock_logging = mocker.patch('logging.info')
    log_search_if_required(mocker.Mock(), args, 'group', 'artifact', '1.0')
    mock_logging.assert_called_once_with("Search: group:artifact:1.0")


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
    pom_path = 'http://example.com/pom.pom'
    headers = {'Last-Modified': 'Wed, 18 Jan 2025 12:00:00 GMT'}
    mock_response = mocker.Mock(status_code=200, headers=headers)
    mock_requests = mocker.patch('requests.get', return_value=mock_response)
    is_valid, last_modified = pom_data((), True, 'artifact', '1.0', pom_path)
    assert is_valid is True and last_modified == '2025-01-18'

    mock_requests.return_value = mocker.Mock(status_code=404)
    is_valid, last_modified = pom_data((), True, 'artifact', '1.0', pom_path)
    assert is_valid is False and last_modified is None


def test_load_pom_tree(mocker):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <groupId>group</groupId>
        <artifactId>artifact</artifactId>
        <version>1.0</version>
    </project>
    """
    config_parser = ConfigParser()
    config_parser.optionxform = str
    config_parser.read_string("""
    [pom_http]
    auth = true
    """)
    mocker.patch('os.path.exists', return_value=True)
    mock_open = mocker.patch('builtins.open', mocker.mock_open(read_data=xml))
    tree = load_pom_tree('pom.xml', True, config_parser, {})
    mock_open.assert_called_once_with('pom.xml', 'rb')
    assert isinstance(tree, ET.ElementTree)

    mocker.patch('os.path.exists', return_value=False)
    with pytest.raises(FileNotFoundError):
        load_pom_tree('pom.xml', True, config_parser, {})

    pom_path = 'http://example.com/pom.pom'
    mock_response = mocker.Mock(status_code=200, text=xml)
    mock_requests = mocker.patch('requests.get', return_value=mock_response)
    assert isinstance(load_pom_tree(pom_path, True, config_parser, {}), ET.ElementTree)

    mock_requests.return_value.status_code = 404
    with pytest.raises(FileNotFoundError):
        load_pom_tree(pom_path, True, config_parser, {})


def test_configure_logging(mocker):
    mock_logging = mocker.patch('logging.basicConfig')
    configure_logging({'logfile_off': False})
    mock_logging.assert_called_once_with(
        level=logging.INFO, handlers=[mocker.ANY, mocker.ANY],
        format='%(asctime)s %(levelname)s: %(message)s'
    )
    handlers = mock_logging.call_args[1]['handlers']
    assert isinstance(handlers[0], logging.StreamHandler)
    assert isinstance(handlers[1], logging.FileHandler)
    assert PurePath(handlers[1].baseFilename).name == 'maven_check_versions.log'


def test_check_versions(mocker):
    _check_versions = lambda pa, data, item, vers: check_versions(
        data, mocker.Mock(), pa, 'group', 'artifact', item,
        'repo_section', 'path', (), True, vers, mocker.Mock()
    )

    mock_pom_data = mocker.patch('maven_check_versions.pom_data')
    mock_pom_data.return_value = (True, '2025-01-25')
    args = {
        'skip_current': True, 'fail_mode': True,
        'fail_major': 0, 'fail_minor': 1
    }
    cache_data = {}
    assert _check_versions(args, cache_data, '1.1', ['1.1'])
    assert cache_data['group:artifact'][1] == '1.1'

    with pytest.raises(AssertionError):
        args['fail_minor'] = 0
        assert _check_versions(args, cache_data, '1.1', ['1.2'])

    args['fail_mode'] = False
    assert _check_versions(args, cache_data, '1.1', ['1.2'])

    mock_pom_data.return_value = (False, None)
    assert not _check_versions(args, cache_data, '1.1', ['1.2'])


def test_service_rest(mocker):
    _service_rest = lambda: service_rest(
        {}, mocker.Mock(), {}, 'group', 'artifact', '1.0', 'section',
        'repository', 'http://example.com/pom.pom', (), True
    )

    mock_check_versions = mocker.patch('maven_check_versions.check_versions')
    mock_check_versions.return_value = True
    mock_requests = mocker.patch('requests.get')
    mock_requests.return_value = mocker.Mock(status_code=200, text="""
    <?xml version="1.0" encoding="UTF-8"?>
    <root>
        <version>1.0</version>
        <version>1.1</version>
    </root>
    """.lstrip())
    assert _service_rest()

    text = '<html><body><table><a>1.0</a><a>1.1</a></table></body></html>'
    mock_response = mocker.Mock(status_code=200, text=text)
    mock_requests.side_effect = [mocker.Mock(status_code=404), mock_response]
    assert _service_rest()

    mock_response = mocker.Mock(status_code=404)
    mock_requests.side_effect = [mock_response, mock_response]
    assert not _service_rest()


def test_process_repository(mocker):
    config_parser = ConfigParser()
    config_parser.optionxform = str
    config_parser.read_string("""
    [section]
    base = https://repo1.maven.org
    path = maven2
    repo = maven-central
    service_rest = true
    auth = true
    """)
    args = {'user': 'user', 'password': 'pass'}
    _process_repository = lambda: process_repository(
        {}, config_parser, args, 'group', 'artifact', '1.0',
        'repository', 'section', True
    )

    mock_requests = mocker.patch('requests.get')
    mock_requests.return_value = mocker.Mock(status_code=200, text="""
    <?xml version="1.0" encoding="UTF-8"?>
    <metadata>
        <versioning>
            <versions>
                <version>1.0</version>
                <version>1.1</version>
            </versions>
        </versioning>
    </metadata>
    """.lstrip())
    mock_check_versions = mocker.patch('maven_check_versions.check_versions')
    mock_check_versions.return_value = True
    assert _process_repository()

    mock_requests.return_value = mocker.Mock(status_code=404)
    mock_service_rest = mocker.patch('maven_check_versions.service_rest')
    mock_service_rest.return_value = True
    assert _process_repository()

    config_parser.set('section', 'service_rest', 'false')
    assert not _process_repository()


def test_process_repositories(mocker):
    config_parser = ConfigParser()
    config_parser.optionxform = str
    config_parser.read_string("""
    [repositories]
        repo1 = maven-central
        repo2 = custom-repo
    [maven-central]
        base = https://repo1.maven.org
        path = maven2
    [custom-repo]
        base = https://custom.repo
        path = maven2
    """)
    mock_process_repository = mocker.patch('maven_check_versions.process_repository')
    mock_process_repository.return_value = True
    assert process_repositories('artifact', {}, config_parser, 'group', {}, True, '1.0')

    config_parser.remove_section('repositories')
    config_parser.read_string("[repositories]")
    assert not process_repositories('artifact', {}, config_parser, 'group', {}, True, '1.0')


def test_process_modules_if_required(mocker):
    config_parser = ConfigParser()
    config_parser.optionxform = str
    config_parser.read_string("[base]\nprocess_modules = true")
    root = ET.fromstring("""
    <?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <modules>
            <module>module1</module>
            <module>module2</module>
        </modules>
    </project>
    """.lstrip())
    mocker.patch('os.path.exists', return_value=True)
    mock_process_pom = mocker.patch('maven_check_versions.process_pom')
    process_modules_if_required({}, config_parser, {}, root, 'pom.xml', ns_mappings)
    assert mock_process_pom.call_count == 2


def test_find_artifact(mocker):
    config_parser = ConfigParser()
    config_parser.optionxform = str
    config_parser.read_string("""
    [base]
        show_search = true
    [repositories]
        repo1 = maven-central
        repo2 = custom-repo
    [maven-central]
        base = https://repo1.maven.org
        path = maven2
    [custom-repo]
        base = https://custom.repo
        path = maven2
    """)
    mock_logging = mocker.patch('logging.info')
    mock_process_repository = mocker.patch('maven_check_versions.process_repository')
    mock_process_repository.return_value = True
    find_artifact(None, config_parser, {}, 'group:artifact:1.0')
    mock_logging.assert_called_once_with('Search: group:artifact:1.0')
    mock_process_repository.assert_called_once()

    mock_logging = mocker.patch('logging.warning')
    mock_process_repository.return_value = False
    find_artifact(None, config_parser, {}, 'group:artifact:1.0')
    mock_logging.assert_called_once_with('Not Found: group:artifact, current:1.0')


def test_process_dependencies(mocker):
    config_parser = ConfigParser()
    config_parser.optionxform = str
    config_parser.read_string("""
    [base]
        empty_version = true
        show_skip = true
    """)
    root = ET.fromstring("""
        <?xml version="1.0" encoding="UTF-8"?>
        <project xmlns="http://maven.apache.org/POM/4.0.0">
            <dependencies>
                <dependency xmlns="http://maven.apache.org/POM/4.0.0">
                    <artifactId>artifact</artifactId>
                    <groupId>group</groupId>
                    <version>1.0</version>
                </dependency>
            </dependencies>
        </project>
        """.lstrip())
    dependencies = collect_dependencies(root, ns_mappings, config_parser, {})
    _process_dependencies = lambda data=None: process_dependencies(
        data, config_parser, {}, dependencies, ns_mappings, root, True
    )

    mock_gdi = mocker.patch('maven_check_versions.get_dependency_identifiers')
    mock_gdi.return_value = ('artifact', None)
    mock_logging = mocker.patch('logging.error')
    _process_dependencies()
    mock_logging.assert_called_once()

    mock_gdi.return_value = ('artifact', 'group')
    mock_get_version = mocker.patch('maven_check_versions.get_version')
    mock_get_version.return_value = ('1.0', True)
    mock_logging = mocker.patch('logging.warning')
    _process_dependencies()
    mock_logging.assert_called_once()

    mock_get_version.return_value = ('1.0', False)
    mocker.patch('maven_check_versions.process_cached_data', return_value=True)
    _process_dependencies({'group:artifact': ()})

    mocker.patch('maven_check_versions.process_repositories', return_value=False)
    mock_logging = mocker.patch('logging.warning')
    _process_dependencies()
    mock_logging.assert_called_once()
