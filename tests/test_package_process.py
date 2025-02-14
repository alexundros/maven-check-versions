#!/usr/bin/python3
"""Tests for package process"""

import os
import sys

# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

# noinspection PyUnresolvedReferences
from maven_check_versions.process import process_main  # noqa: E402


# noinspection PyShadowingNames
def test_process_main(mocker, monkeypatch):
    monkeypatch.setenv('HOME', os.path.dirname(__file__))
    mock_exists = mocker.patch('os.path.exists')
    mock_exists.side_effect = [False, True]
    mocker.patch('builtins.open', mocker.mock_open(read_data="""
    [base]
        cache_off = false
    """))
    mocker.patch('maven_check_versions.cache.load_cache', return_value={})
    mocker.patch('maven_check_versions.process_pom')
    mocker.patch('maven_check_versions.cache.save_cache')
    process_main({'pom_file': 'pom.xml'})

    mock_exists.side_effect = [False, True]
    mocker.patch('maven_check_versions.process_artifact')
    process_main({'find_artifact': 'pom.xml'})

    mock_exists.side_effect = [False, True]
    mock_config_items = mocker.patch('maven_check_versions.config.config_items')
    mock_config_items.return_value = [('key', 'pom.xml')]
    process_main({})
