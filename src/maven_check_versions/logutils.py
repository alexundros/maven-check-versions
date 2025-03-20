#!/usr/bin/python3
"""This file provides logging utilities"""

import datetime
import logging
import re
import sys

import maven_check_versions.config as _config
import requests
from maven_check_versions.config import Config, Arguments


def configure_logging(arguments: Arguments) -> None:
    """
    Configures logging.

    Args:
        arguments (Arguments): Command-line arguments.
    """
    handlers = [logging.StreamHandler(sys.stdout)]

    if not arguments.get('logfile_off'):
        if (log_file_path := arguments.get('log_file')) is None:
            log_file_path = 'maven_check_versions.log'
        handlers.append(logging.FileHandler(log_file_path, 'w'))

    logging.Formatter.formatTime = lambda self, record, fmt=None: \
        datetime.datetime.fromtimestamp(record.created)

    frm = '%(asctime)s %(levelname)s: %(message)s'
    logging.basicConfig(level=logging.INFO, handlers=handlers, format=frm)  # NOSONAR


def log_skip_if_required(
        config: Config, arguments: Arguments, group: str, artifact: str, version: str
) -> None:
    """
    Logs a skipped dependency if required.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        group (str): Group ID.
        artifact (str): Artifact ID.
        version (str): Dependency version.
    """
    if _config.get_config_value(config, arguments, 'show_skip'):
        logging.warning(f"Skip: {group}:{artifact}:{version}")


def log_search_if_required(
        config: Config, arguments: Arguments, group: str, artifact: str, version: str
) -> None:
    """
    Logs a dependency search action if required.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        group (str): Group ID.
        artifact (str): Artifact ID.
        version (str): Dependency version (Maybe None or a placeholder).
    """
    if _config.get_config_value(config, arguments, 'show_search'):
        if version is None or re.match('^\\${([^}]+)}$', version):
            logging.warning(f"Search: {group}:{artifact}:{version}")
        else:
            logging.info(f"Search: {group}:{artifact}:{version}")


def log_invalid_if_required(
        config: Config, arguments: Arguments, response: requests.Response, group: str,
        artifact: str, item: str, invalid_flag: bool
) -> None:
    """
    Logs invalid versions if required.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        response (requests.Response): Repository response.
        group (str): Group ID.
        artifact (str): Artifact ID.
        item (str): Version being checked.
        invalid_flag (bool): Flag indicating invalid versions have been logged.
    """
    if _config.get_config_value(config, arguments, 'show_invalid'):
        if not invalid_flag:
            logging.info(response.url)
        logging.warning(f"Invalid: {group}:{artifact}:{item}")
