#!/usr/bin/python3
"""This file provides logging utilities"""

import datetime
import logging
import re
import sys
from configparser import ConfigParser

import requests
from .config import get_config_value


def configure_logging(arguments: dict) -> None:
    """
    Configure logging.

    Args:
        arguments (dict): Dictionary containing the parsed command line arguments.
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
        config_parser: ConfigParser, arguments: dict, group_id: str, artifact_id: str, version: str
) -> None:
    """
    Logs a warning message if a dependency is skipped based on configuration or command-line argument settings.

    Args:
        config_parser (ConfigParser): Configuration parser to fetch values from configuration files.
        arguments (dict): Dictionary of parsed command-line arguments to check runtime options.
        group_id (str): The group ID of the Maven artifact being processed.
        artifact_id (str): The artifact ID of the Maven artifact being processed.
        version (str): The version of the Maven artifact being processed.
    """
    if get_config_value(config_parser, arguments, 'show_skip', value_type=bool):
        logging.warning(f"Skip: {group_id}:{artifact_id}:{version}")


def log_search_if_required(
        config_parser: ConfigParser, arguments: dict, group_id: str, artifact_id: str, version: str
) -> None:
    """
    Logs a message indicating a search action for a dependency if specific conditions are met.

    Args:
        config_parser (ConfigParser): Configuration parser to fetch values from configuration files.
        arguments (dict): Dictionary of parsed command-line arguments to check runtime options.
        group_id (str): The group ID of the Maven artifact being processed.
        artifact_id (str): The artifact ID of the Maven artifact being processed.
        version (str): The version of the Maven artifact being processed; can be None or a property placeholder.
    """
    if get_config_value(config_parser, arguments, 'show_search', value_type=bool):
        if version is None or re.match('^\\${([^}]+)}$', version):
            logging.warning(f"Search: {group_id}:{artifact_id}:{version}")
        else:
            logging.info(f"Search: {group_id}:{artifact_id}:{version}")


def log_invalid_if_required(
        config_parser: ConfigParser, arguments: dict, response: requests.Response, group_id: str,
        artifact_id: str, item: str, invalid_flag: bool
) -> None:
    """
        Log invalid versions if required.

        Args:
            config_parser (ConfigParser): Configuration parser to fetch values from configuration files.
            arguments (dict): Dictionary of parsed command-line arguments to check runtime options.
            response (requests.Response): The response object from the repository.
            group_id (str): The group ID of the Maven artifact being processed.
            artifact_id (str): TThe artifact ID of the Maven artifact being processed.
            item (str): The version item.
            invalid_flag (bool): Flag indicating if invalid versions have been logged.
        """
    if get_config_value(config_parser, arguments, 'show_invalid', value_type=bool):
        if not invalid_flag:
            logging.info(response.url)
        logging.warning(f"Invalid: {group_id}:{artifact_id}:{item}")
