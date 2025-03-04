#!/usr/bin/python3
"""This file provides logging utilities"""

import datetime
import logging
import re
import sys

import maven_check_versions.config as _config
import requests


def configure_logging(arguments: dict) -> None:
    """
    Configures logging.

    Args:
        arguments (dict): Command-line arguments.
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
        config: dict, arguments: dict, group_id: str, artifact_id: str, version: str
) -> None:
    """
    Logs a skipped dependency if required.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.
        group_id (str): Group ID.
        artifact_id (str): Artifact ID.
        version (str): Dependency version.
    """
    if _config.get_config_value(config, arguments, 'show_skip', value_type=bool):
        logging.warning(f"Skip: {group_id}:{artifact_id}:{version}")


def log_search_if_required(
        config: dict, arguments: dict, group_id: str, artifact_id: str, version: str
) -> None:
    """
    Logs a dependency search action if required.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.
        group_id (str): Group ID.
        artifact_id (str): Artifact ID.
        version (str): Dependency version (Maybe None or a placeholder).
    """
    if _config.get_config_value(config, arguments, 'show_search', value_type=bool):
        if version is None or re.match('^\\${([^}]+)}$', version):
            logging.warning(f"Search: {group_id}:{artifact_id}:{version}")
        else:
            logging.info(f"Search: {group_id}:{artifact_id}:{version}")


def log_invalid_if_required(
        config: dict, arguments: dict, response: requests.Response, group_id: str,
        artifact_id: str, item: str, invalid_flag: bool
) -> None:
    """
    Logs invalid versions if required.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.
        response (requests.Response): Repository response.
        group_id (str): Group ID.
        artifact_id (str): Artifact ID.
        item (str): Version being checked.
        invalid_flag (bool): Flag indicating invalid versions have been logged.
    """
    if _config.get_config_value(config, arguments, 'show_invalid', value_type=bool):
        if not invalid_flag:
            logging.info(response.url)
        logging.warning(f"Invalid: {group_id}:{artifact_id}:{item}")
