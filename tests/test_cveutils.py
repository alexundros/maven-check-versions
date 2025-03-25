#!/usr/bin/python3
"""Tests for package cve check functions"""

import os
import sys

import pytest
# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

from maven_check_versions.config import Config, Arguments
from maven_check_versions.cveutils import log_vulnerability, Vulnerability


# noinspection PyShadowingNames
def test_log_vulnerability(mocker):
    cve_data = {'pkg:maven/groupId/artifactId@1.0': [Vulnerability(id='1', cvssScore=1)]}
    mock_logging = mocker.patch('logging.warning')
    config = Config({'vulnerability': {'fail-score': 2.0}})
    log_vulnerability(config, Arguments(), 'groupId', 'artifactId', '1.0', cve_data)
    msg = 'Vulnerability for groupId:artifactId:1.0: cvssScore=1 cve=None cwe=None None None'
    mock_logging.assert_called_once_with(msg)

    with pytest.raises(AssertionError):
        mock_logging = mocker.patch('logging.error')
        config = Config({'vulnerability': {'fail-score': 1.0}})
        log_vulnerability(config, Arguments(), 'groupId', 'artifactId', '1.0', cve_data)
        mock_logging.assert_called_once_with('cvssScore=1 >= fail-score=1')
