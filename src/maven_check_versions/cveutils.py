#!/usr/bin/python3
"""This file provides cve functions"""

import logging
import re
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import maven_check_versions.config as _config
import maven_check_versions.utils as _utils
import requests
from maven_check_versions.cache import save_cache, load_cache
from requests.auth import HTTPBasicAuth

MVN_PKG_REGEX = '^pkg:maven/(.+)/(.+)@(.+)$'  # NOSONAR


@dataclass
class Vulnerability:
    """
    Vulnerability.
    """
    id: str  # NOSONAR # noqa: A003,VNE003
    displayName: str = None  # NOSONAR # noqa: N815
    title: str = None  # NOSONAR
    description: str = None  # NOSONAR
    cvssScore: float = None  # NOSONAR # noqa: N815
    cvssVector: str = None  # NOSONAR # noqa: N815
    cve: str = None  # NOSONAR
    cwe: str = None  # NOSONAR
    reference: str = None  # NOSONAR
    externalReferences: list[str] = ()  # NOSONAR # noqa: N815
    versionRanges: list[str] = ()  # NOSONAR # noqa: N815


def get_cve_data(  # pragma: no cover
        config: dict, arguments: dict, dependencies: list[ET.Element], root: ET.Element,
        ns_mapping: dict
) -> dict[str, list[Vulnerability]]:
    """
    Get CVE data for dependencies.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.
        dependencies (list[ET.Element]): Dependencies.
        root (ET.Element): Root element of the POM file.
        ns_mapping (dict): XML namespace mapping.

    Returns:
        dict[str, list[Vulnerability]]: CVE Data.
    """
    result = {}
    if _config.get_config_value(
            config, arguments, 'oss_index_enabled', 'vulnerability', value_type=bool,
            default='false'
    ):
        coordinates = _get_coordinates(config, arguments, dependencies, ns_mapping, root)
        if len(cache_data := load_cache(config, arguments, 'vulnerability')):
            for item in coordinates:
                md = re.match(MVN_PKG_REGEX, item)
                if cache_data.get(f"{md[1]}:{md[2]}:{md[3]}") is not None:
                    coordinates.remove(item)

        cve_data = _fetch_cve_data(config, arguments, coordinates)
        if len(cve_data):
            save_cache(config, arguments, cve_data, 'vulnerability')

        result.update(cve_data)
    return result


def _get_coordinates(config, arguments, dependencies, ns_mapping, root) -> list:  # pragma: no cover
    """
        Get Coordinates.

        Args:
            config (dict): Parsed YAML as dict.
            arguments (dict): Command-line arguments.
            dependencies (list[ET.Element]): Dependencies.
            root (ET.Element): Root element of the POM file.
            ns_mapping (dict): XML namespace mapping.

        Returns:
            list: Coordinates.
        """
    coordinates = []
    for dependency in dependencies:  # pragma: no cover
        (artifact_id, group_id) = _utils.get_dependency_identifiers(dependency, ns_mapping)
        (version, _) = _utils.get_version(config, arguments, ns_mapping, root, dependency)
        list.append(coordinates, f"pkg:maven/{group_id}/{artifact_id}@{version}")
    return coordinates


def _oss_index_config(config: dict, arguments: dict) -> tuple:  # pragma: no cover
    """
    Get OSS Index parameters.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.

    Returns:
        tuple: OSS Index parameters.
    """
    return (
        _config.get_config_value(
            config, arguments, 'oss_index_url', 'vulnerability',
            default='https://ossindex.sonatype.org/api/v3/component-report'),
        _config.get_config_value(config, arguments, 'oss_index_user', 'vulnerability'),
        _config.get_config_value(config, arguments, 'oss_index_token', 'vulnerability'),
        _config.get_config_value(
            config, arguments, 'oss_index_batch_size', 'vulnerability', value_type=int,
            default='128'),
        _config.get_config_value(
            config, arguments, 'oss_index_keep_safe', 'vulnerability', value_type=bool,
            default='false')
    )


def _fetch_cve_data(  # pragma: no cover
        config: dict, arguments: dict, coordinates: list[str]
) -> dict[str, list[Vulnerability]]:
    """
    Get CVE data for coordinates.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.
        coordinates (list[str]): Coordinates.

    Returns:
        dict[str, list[Vulnerability]]: CVE Data.
    """
    result = {}
    try:
        url, user, token, batch_size, keep_safe = _oss_index_config(config, arguments)
        auth = HTTPBasicAuth(user, token)

        for i in range(0, len(coordinates), batch_size):
            batch = coordinates[i:i + batch_size]
            response = requests.post(url, json={"coordinates": batch}, auth=auth)
            if response.status_code != 200:
                logging.error(f"OSS Index API error: {response.status_code}")
                continue

            for item in response.json():
                cves = []
                md = re.match(MVN_PKG_REGEX, item['coordinates'])
                if len(data := item.get('vulnerabilities')):
                    cves = [Vulnerability(**cve) for cve in data]
                if len(cves) or keep_safe:
                    result.update({f"{md[1]}:{md[2]}:{md[3]}": cves})

    except Exception as e:
        logging.error(f"Failed to fetch_cve_data: {e}")
    return result
