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
from requests.auth import HTTPBasicAuth


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
            config, arguments, 'oss_index_enabled', 'vulnerability', value_type=bool, default='false'
    ):
        coordinates = _get_coordinates(config, arguments, dependencies, ns_mapping, root)
        cve_data = _fetch_cve_data(config, arguments, coordinates)

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
            default='128')
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
        url, user, token, size = _oss_index_config(config, arguments)
        auth = HTTPBasicAuth(user, token)

        for i in range(0, len(coordinates), size):
            batch = coordinates[i:i + size]
            response = requests.post(url, json={"coordinates": batch}, auth=auth)
            if response.status_code == 200:
                rgx = '^pkg:maven/(.+)/(.+)@(.+)$'  # NOSONAR
                for item in response.json():
                    data = item.get('vulnerabilities')
                    if (match := re.match(rgx, item['coordinates'])) and len(data):
                        cves = [Vulnerability(**cve) for cve in data]
                        result.update({f"{match[1]}:{match[2]}": cves})
            else:
                logging.error(f"OSS Index API error: {response.status_code}")
    except Exception as e:
        logging.error(f"Failed to fetch_cve_data: {e}")
    return result
