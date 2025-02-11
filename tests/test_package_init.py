#!/usr/bin/python3
"""Tests for package init"""

import os
import sys
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
    get_dependency_identifiers, resolve_version,
    get_version, fail_mode_if_required, pom_data, load_pom_tree,
    check_versions, service_rest, process_repository,
    process_repositories, process_modules_if_required, find_artifact,
    process_dependencies, process_pom, main_process, main
)

# noinspection PyUnresolvedReferences
from maven_check_versions.logutils import (  # noqa: E402
    configure_logging, log_skip_if_required,
    log_search_if_required, log_invalid_if_required
)

# noinspection PyUnresolvedReferences
from maven_check_versions.config import (  # noqa: E402
    get_config_value, config_items
)

# noinspection PyUnresolvedReferences
from maven_check_versions.utils import (  # noqa: E402
    collect_dependencies
)

ns_mappings = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}


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


# noinspection PyShadowingNames
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


# noinspection PyShadowingNames
def test_fail_mode_if_required(mocker):
    mock_logging = mocker.patch('logging.warning')
    with pytest.raises(AssertionError):
        config_parser = ConfigParser()
        args = {'fail_mode': True, 'fail_major': 2, 'fail_minor': 2}
        fail_mode_if_required(config_parser, 1, 0, '4.0', 2, 2, args, '1.0')
    mock_logging.assert_called_once_with("Fail version: 4.0 > 1.0")


# noinspection PyShadowingNames
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


# noinspection PyShadowingNames
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


# noinspection PyShadowingNames
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


# noinspection PyShadowingNames
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


# noinspection PyShadowingNames
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


# noinspection PyShadowingNames
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


# noinspection PyShadowingNames
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


# noinspection PyShadowingNames
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


# noinspection PyShadowingNames
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
    mocker.patch('maven_check_versions.process_cache', return_value=True)
    _process_dependencies({'group:artifact': ()})

    mocker.patch('maven_check_versions.process_repositories', return_value=False)
    mock_logging = mocker.patch('logging.warning')
    _process_dependencies()
    mock_logging.assert_called_once()


# noinspection PyShadowingNames
def test_process_pom(mocker):
    mock_load_pom_tree = mocker.patch('maven_check_versions.load_pom_tree')
    mock_load_pom_tree.return_value = ET.ElementTree(ET.fromstring("""
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <artifactId>artifact</artifactId>
        <groupId>group</groupId>
        <version>1.0</version>
        <dependencies>
            <dependency>
                <artifactId>artifact</artifactId>
                <groupId>group</groupId>
                <version>1.0</version>
            </dependency>
        </dependencies>
    </project>
    """))
    mock_cd = mocker.patch('maven_check_versions.collect_dependencies')
    mock_pd = mocker.patch('maven_check_versions.process_dependencies')
    mock_pmir = mocker.patch('maven_check_versions.process_modules_if_required')
    process_pom({}, mocker.Mock(), {}, 'pom.xml', 'prefix')
    mock_load_pom_tree.assert_called_once()
    mock_cd.assert_called_once()
    mock_pd.assert_called_once()
    mock_pmir.assert_called_once()


# noinspection PyShadowingNames
def test_main_process(mocker, monkeypatch):
    monkeypatch.setenv('HOME', os.path.dirname(__file__))
    mock_exists = mocker.patch('os.path.exists')
    mock_exists.side_effect = [False, True]
    mocker.patch('builtins.open', mocker.mock_open(read_data="""
    [base]
        cache_off = false
    """))
    mocker.patch('maven_check_versions.load_cache', return_value={})
    mocker.patch('maven_check_versions.process_pom')
    mocker.patch('maven_check_versions.save_cache')
    main_process({'pom_file': 'pom.xml'})

    mock_exists.side_effect = [False, True]
    mocker.patch('maven_check_versions.find_artifact')
    main_process({'find_artifact': 'pom.xml'})

    mock_exists.side_effect = [False, True]
    mock_config_items = mocker.patch('maven_check_versions.config_items')
    mock_config_items.return_value = [('key', 'pom.xml')]
    main_process({})


# noinspection PyShadowingNames
def test_main(mocker):
    mock_pcla = mocker.patch('maven_check_versions.parse_command_line')
    mock_pcla.return_value = {'ci_mode': False}
    mock_main_process = mocker.patch('maven_check_versions.main_process')
    mock_input = mocker.patch('builtins.input', return_value='')
    mocker.patch('maven_check_versions.configure_logging')
    mocker.patch('sys.exit')
    main()
    mock_main_process.side_effect = FileNotFoundError
    main()
    mock_main_process.side_effect = AssertionError
    main()
    mock_main_process.side_effect = KeyboardInterrupt
    main()
    mock_main_process.side_effect = SystemExit
    main()
    mock_main_process.side_effect = Exception
    main()
    mock_input.side_effect = KeyboardInterrupt
    main()
