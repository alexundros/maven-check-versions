#!/usr/bin/python3
"""Tests for package process"""

import os
import sys
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from typing import Optional

# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

# noinspection PyUnresolvedReferences
from maven_check_versions.process import (  # noqa: E402
    process_rest, process_repository, process_repositories,
    process_modules_if_required, process_artifact,
    process_dependency, process_pom, process_main
)

# noinspection PyUnresolvedReferences
from maven_check_versions.logutils import (  # noqa: E402
    configure_logging, log_skip_if_required,
    log_search_if_required, log_invalid_if_required
)

# noinspection PyUnresolvedReferences
from maven_check_versions.config import (  # noqa: E402
    get_config_value, config_items, Arguments, Config
)

# noinspection PyUnresolvedReferences
from maven_check_versions.utils import (  # noqa: E402
    get_dependency_identifiers, collect_dependencies,
    resolve_version, get_version,
)

ns_mappings = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}  # NOSONAR


# noinspection PyShadowingNames
def test_process_main(mocker, monkeypatch):
    monkeypatch.setenv('HOME', os.path.dirname(__file__))
    mock_exists = mocker.patch('os.path.exists')
    mock_exists.side_effect = [False, False, True]
    mocker.patch('builtins.open', mocker.mock_open(read_data="base.cache_off: false"))
    mocker.patch('maven_check_versions.cache.load_cache', return_value={})
    mocker.patch('maven_check_versions.process.process_pom')
    mocker.patch('maven_check_versions.cache.save_cache')
    process_main(Arguments({'pom_file': 'pom.xml'}))

    mock_exists.side_effect = [False, False, True]
    mocker.patch('maven_check_versions.process.process_artifact')
    process_main(Arguments({'find_artifact': 'pom.xml'}))

    mock_exists.side_effect = [False, False, True]
    mock_config_items = mocker.patch('maven_check_versions.config.config_items')
    mock_config_items.return_value = [('key', 'pom.xml')]
    process_main(Arguments())


# noinspection PyShadowingNames
def test_process_rest(mocker):
    def _service_rest():
        return process_rest(
            {}, Config(), Arguments(), 'group', 'artifact', '1.0', 'section',
            'repository', 'http://example.com/pom.pom', None, True  # NOSONAR
        )

    mock_check_versions = mocker.patch('maven_check_versions.utils.check_versions')
    mock_check_versions.return_value = True
    mock_requests = mocker.patch('requests.Session.get')
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
    config = Config({
        'section': {
            'base': 'https://repo1.maven.org',
            'path': 'maven2',
            'repo': 'maven-central',
            'service_rest': True,
            'auth': True,
        }})
    args = Arguments({'user': 'user', 'password': 'pass'})  # NOSONAR

    def _process_repository():
        return process_repository(
            {}, config, args, 'group', 'artifact', '1.0',
            'repository', 'section', True
        )

    mock_requests = mocker.patch('requests.Session.get')
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
    mock_check_versions = mocker.patch('maven_check_versions.utils.check_versions')
    mock_check_versions.return_value = True
    assert _process_repository()

    mock_requests.return_value = mocker.Mock(status_code=404)
    mock_process_rest = mocker.patch('maven_check_versions.process.process_rest')
    mock_process_rest.return_value = True
    assert _process_repository()

    config['section']['service_rest'] = False
    assert not _process_repository()


# noinspection PyShadowingNames
def test_process_repositories(mocker):
    config = Config({
        'repositories': {
            'repo1': 'maven-central',
            'repo2': 'custom-repo',
        },
        'maven-central': {
            'base': 'https://repo1.maven.org',
            'path': 'maven2',
        },
        'custom-repo': {
            'base': 'https://custom.repo',
            'path': 'maven2',
        }
    })
    mock_process_repository = mocker.patch('maven_check_versions.process.process_repository')
    mock_process_repository.return_value = True
    assert process_repositories('artifact', {}, config, 'group', Arguments(), True, '1.0')

    config = Config({'repositories': {}})
    assert not process_repositories('artifact', {}, config, 'group', Arguments(), True, '1.0')


# noinspection PyShadowingNames
def test_process_modules_if_required(mocker):
    config = Config({
        'base': {
            'process_modules': True,
            'threading': True,
            'max_threads': 1
        }
    })
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
    mock_process_pom = mocker.patch('maven_check_versions.process.process_pom')
    process_modules_if_required({}, config, Arguments(), root, 'pom.xml', ns_mappings)
    assert mock_process_pom.call_count == 2

    config['base']['threading'] = False
    mock_process_pom = mocker.patch('maven_check_versions.process.process_pom')
    process_modules_if_required({}, config, Arguments(), root, 'pom.xml', ns_mappings)
    assert mock_process_pom.call_count == 2


# noinspection PyShadowingNames
def test_process_artifact(mocker):
    config = Config({
        'base': {
            'show_search': 'true',
        },
        'repositories': {
            'repo1': 'maven-central',
            'repo2': 'custom-repo',
        },
        'maven-central': {
            'base': 'https://repo1.maven.org',
            'path': 'maven2',
        },
        'custom-repo': {
            'base': 'https://custom.repo',
            'path': 'maven2',
        }
    })
    mock_logging = mocker.patch('logging.info')
    mock_process_repository = mocker.patch('maven_check_versions.process.process_repository')
    mock_process_repository.return_value = True
    process_artifact(None, config, Arguments(), 'group:artifact:1.0')
    mock_logging.assert_called_once_with('Search: group:artifact:1.0')
    mock_process_repository.assert_called_once()

    mock_logging = mocker.patch('logging.warning')
    mock_process_repository.return_value = False
    process_artifact(None, config, Arguments(), 'group:artifact:1.0')
    mock_logging.assert_called_once_with('Not Found: group:artifact, current:1.0')


# noinspection PyShadowingNames
def test_process_dependency(mocker):
    config = Config({
        'base': {
            'empty_version': 'true',
            'show_skip': 'true',
        }
    })
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
    dependencies = collect_dependencies(root, ns_mappings, config, Arguments())

    def _process_dependencies(data: Optional[dict] = None) -> None:
        for dep in dependencies:
            process_dependency(data, config, Arguments(), dep, ns_mappings, root, True)

    mock_gdi = mocker.patch('maven_check_versions.utils.get_dependency_identifiers')
    mock_gdi.return_value = ('artifact', None)
    mock_logging = mocker.patch('logging.error')
    _process_dependencies()
    mock_logging.assert_called_once()

    mock_gdi.return_value = ('group', 'artifact')
    mock_get_version = mocker.patch('maven_check_versions.utils.get_version')
    mock_get_version.return_value = ('1.0', True)
    mock_logging = mocker.patch('logging.warning')
    _process_dependencies()
    mock_logging.assert_called_once()

    mock_get_version.return_value = ('1.0', False)
    mocker.patch('maven_check_versions.cache.process_cache_artifact', return_value=True)
    _process_dependencies({'group:artifact': ()})

    mocker.patch('maven_check_versions.process.process_repositories', return_value=False)
    mock_logging = mocker.patch('logging.warning')
    _process_dependencies()
    mock_logging.assert_called_once()


# noinspection PyShadowingNames
def test_process_pom(mocker):
    mock_get_pom_tree = mocker.patch('maven_check_versions.utils.get_pom_tree')
    mock_get_pom_tree.return_value = ET.ElementTree(ET.fromstring("""
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
    mock_pd = mocker.patch('maven_check_versions.process.process_dependency')
    mock_pm = mocker.patch('maven_check_versions.process.process_modules_if_required')
    config = Config({
        'base': {
            'threading': True,
            'max_threads': 4
        }
    })
    process_pom({}, config, Arguments(), 'pom.xml', 'prefix')
    mock_get_pom_tree.assert_called_once()
    mock_pd.assert_called_once()
    mock_pm.assert_called_once()

    config['base']['threading'] = False
    mock_pd = mocker.patch('maven_check_versions.process.process_dependency')
    process_pom({}, config, Arguments(), 'pom.xml', 'prefix')
    mock_pd.assert_called_once()
