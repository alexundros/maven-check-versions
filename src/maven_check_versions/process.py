#!/usr/bin/python3
"""This file provides process functions"""

import maven_check_versions as _init
import maven_check_versions.cache as _cache
import maven_check_versions.config as _config
import urllib3


def process_main(arguments: dict) -> None:
    """
    Main processing function.

    Args:
        arguments (dict): Dictionary of parsed command line arguments.
    """
    config_parser = _config.get_config_parser(arguments)

    if not _config.get_config_value(config_parser, arguments, 'warnings', 'urllib3', value_type=bool):
        urllib3.disable_warnings()

    cache_disabled = _config.get_config_value(config_parser, arguments, 'cache_off', value_type=bool)
    if (cache_file_path := arguments.get('cache_file')) is None:
        cache_file_path = 'maven_check_versions.cache'
    cache_data = _cache.load_cache(cache_file_path) if not cache_disabled else None

    if pom_file := arguments.get('pom_file'):
        _init.process_pom(cache_data, config_parser, arguments, pom_file)
    elif artifact_to_find := arguments.get('find_artifact'):
        _init.process_artifact(cache_data, config_parser, arguments, artifact_to_find)
    else:
        for key, pom in _config.config_items(config_parser, 'pom_files'):
            _init.process_pom(cache_data, config_parser, arguments, pom)

    if cache_data is not None:
        _cache.save_cache(cache_data, cache_file_path)
