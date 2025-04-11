#!/usr/bin/python3
"""Tests for package cve check functions"""
import os
import sys
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET

import pytest
# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

from maven_check_versions.config import Config, Arguments
from maven_check_versions.cveutils import Vulnerability, log_vulnerability, get_cve_data
from maven_check_versions.utils import collect_dependencies


# noinspection PyShadowingNames
def test_log_vulnerability(mocker):
    cves = {'pkg:maven/group/artifact@1.0': [Vulnerability(id='1', cvssScore=1)]}
    mock_logging = mocker.patch('logging.warning')
    config = Config({'vulnerability': {'fail_score': 2.0, 'cve_reference': True}})
    log_vulnerability(config, Arguments(), 'group', 'artifact', '1.0', cves)
    msg = 'Vulnerability for group:artifact:1.0: cvssScore=1 cve=None cwe=None None None'
    mock_logging.assert_called_once_with(msg)

    with pytest.raises(AssertionError):
        mock_logging = mocker.patch('logging.error')
        config = Config({'vulnerability': {'fail_score': 1.0}})
        log_vulnerability(config, Arguments(), 'group', 'artifact', '1.0', cves)
        mock_logging.assert_called_once_with('cvssScore=1 >= fail-score=1')


# noinspection PyShadowingNames
def test_get_cve_data(mocker):
    root = ET.fromstring("""
    <?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <dependencies>
            <dependency>
                <groupId>group1</groupId>
                <artifactId>artifact</artifactId>
                <version>1.0</version>
            </dependency>
            <dependency>
                <groupId>group2</groupId>
                <artifactId>artifact</artifactId>
                <version>1.0</version>
            </dependency>
            <dependency>
                <groupId>group3</groupId>
                <artifactId>artifact</artifactId>
                <version>${version}</version>
            </dependency>
            <dependency>
                <groupId>group4</groupId>
                <artifactId>artifact</artifactId>
                <version>1.0</version>
            </dependency>
        </dependencies>
    </project>
    """.lstrip())
    ns_mappings = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}  # NOSONAR
    config = Config({'vulnerability': {
        'oss_index_enabled': True, 'skip_no_versions': True,
        'skip_checks': ['group2.*']
    }})
    deps = collect_dependencies(root, ns_mappings, config, Arguments())
    mock_load_cache = mocker.patch('maven_check_versions.cache.load_cache')
    mock_load_cache.return_value = {'pkg:maven/group4/artifact@1.0': []}
    mocker.patch('maven_check_versions.cache.save_cache')
    mock_requests = mocker.patch(
        'requests.Session.post',
        return_value=mocker.Mock(status_code=200, json=lambda: [{
            'coordinates': 'pkg:maven/group1/artifact@1.0',
            'vulnerabilities': [{'id': '1', 'cvssScore': 1}]
        }]))
    assert get_cve_data(config, Arguments(), deps, root, ns_mappings) == {
        'pkg:maven/group1/artifact@1.0': [Vulnerability(id='1', cvssScore=1)],
        'pkg:maven/group4/artifact@1.0': []
    }

    mock_load_cache.return_value = {}
    mock_requests.return_value.status_code = 404
    assert get_cve_data(config, Arguments(), deps, root, ns_mappings) == {}

    mock_requests.return_value = Exception()
    assert get_cve_data(config, Arguments(), deps, root, ns_mappings) == {}
