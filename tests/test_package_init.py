#!/usr/bin/python3
"""Tests for package init"""

import os
import sys

# noinspection PyUnresolvedReferences
from pytest_mock import mocker

os.chdir(os.path.dirname(__file__))
sys.path.append('../src')

# noinspection PyUnresolvedReferences
from maven_check_versions import main  # noqa: E402


# noinspection PyShadowingNames
def test_main(mocker):
    mock_pcl = mocker.patch('maven_check_versions.utils.parse_command_line')
    mock_pcl.return_value = {'ci_mode': False}
    mock_process_main = mocker.patch('maven_check_versions.process.process_main')
    mock_input = mocker.patch('builtins.input', return_value='')
    mocker.patch('maven_check_versions.logutils.configure_logging')
    mocker.patch('sys.exit')
    main()
    mock_process_main.side_effect = FileNotFoundError
    main()
    mock_process_main.side_effect = AssertionError
    main()
    mock_process_main.side_effect = KeyboardInterrupt
    main()
    mock_process_main.side_effect = SystemExit
    main()
    mock_process_main.side_effect = Exception
    main()
    mock_input.side_effect = KeyboardInterrupt
    main()
