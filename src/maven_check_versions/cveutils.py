#!/usr/bin/python3
"""This file provides cve functions"""

import logging
import re
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from itertools import islice
from typing import Optional

import maven_check_versions.cache as _cache
import maven_check_versions.config as _config
import maven_check_versions.utils as _utils
import requests
from maven_check_versions.config import Config, Arguments
from requests.auth import HTTPBasicAuth


@dataclass
class Vulnerability:
    """
    Vulnerability.
    """
    id: str  # NOSONAR # noqa: A003,VNE003
    displayName: Optional[str] = None  # NOSONAR # noqa: N815
    title: Optional[str] = None  # NOSONAR
    description: Optional[str] = None  # NOSONAR
    cvssScore: Optional[float] = None  # NOSONAR # noqa: N815
    cvssVector: Optional[str] = None  # NOSONAR # noqa: N815
    cve: Optional[str] = None  # NOSONAR
    cwe: Optional[str] = None  # NOSONAR
    reference: Optional[str] = None  # NOSONAR
    externalReferences: Optional[list] = None  # NOSONAR # noqa: N815
    versionRanges: Optional[list] = None  # NOSONAR # noqa: N815


def get_cve_data(
        config: Config, arguments: Arguments, dependencies: list[ET.Element],
        root: ET.Element, ns_mapping: dict
) -> dict[str, list[Vulnerability]]:
    """
    Retrieves CVE (Common Vulnerabilities and Exposures) data for the given dependencies
    using the OSS Index API, with caching support if enabled.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        dependencies (list[ET.Element]): Dependencies.
        root (ET.Element): Root element of the POM file.
        ns_mapping (dict): XML namespace mapping.

    Returns:
        dict[str, list[Vulnerability]]: CVE Data.
    """
    if not _config.get_config_value(config, arguments, 'oss_index_enabled', 'vulnerability', default=False):
        return {}

    coordinates = _get_coordinates(config, arguments, dependencies, ns_mapping, root)
    cve_data = _cache.load_cache(config, arguments, 'vulnerability') or {}

    for key, data in cve_data.items():
        cve_data[key] = [Vulnerability(**item) for item in data]

    coordinates = [coord for coord in coordinates if coord not in cve_data]

    if new_cve_data := _fetch_cve_data(config, arguments, coordinates):
        cve_data.update(new_cve_data)
        _cache.save_cache(config, arguments, cve_data, 'vulnerability')

    return cve_data


def log_vulnerability(
        config: Config, arguments: Arguments, group: str, artifact: str, version: Optional[str],
        cve_data: Optional[dict[str, list[Vulnerability]]]
) -> None:
    """
    Log vulnerability.

    Args:
        config (Config): Configuration dictionary parsed from YAML.
        arguments (Arguments): Command-line arguments.
        group (str): Group ID.
        artifact (str): Artifact ID.
        version (Optional[str]): Dependency version.
        cve_data (dict[str, Optional[list[Vulnerability]]]): CVE Data.
    """
    fail_score = _config.get_config_value(config, arguments, 'fail_score', 'vulnerability', default=0)
    cve_ref = _config.get_config_value(config, arguments, 'cve_reference', 'vulnerability', default=False)

    if cve_data is not None and (cves := cve_data.get(f"pkg:maven/{group}/{artifact}@{version}")):
        for cve in cves:
            info = f"cvssScore={cve.cvssScore} cve={cve.cve} cwe={cve.cwe} {cve.title}"
            if cve_ref:
                info = f"{info} {cve.reference}"
            logging.warning(f"Vulnerability for {group}:{artifact}:{version}: {info}")

            if cve.cvssScore and fail_score and cve.cvssScore >= fail_score:
                logging.error(f"cvssScore={cve.cvssScore} >= fail_score={fail_score}")
                raise AssertionError


def _get_coordinates(config, arguments, dependencies, ns_mapping, root) -> list[str]:
    """
    Get Coordinates.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        dependencies (list[ET.Element]): List of dependency elements from the POM file.
        root (ET.Element): The root element of the POM file's XML tree.
        ns_mapping (dict): A dictionary mapping XML namespaces for parsing.

    Returns:
        list[str]: Coordinates.
    """
    skip_no_versions = _config.get_config_value(
        config, arguments, 'skip_no_versions', 'vulnerability', default=False)
    combined = None
    if skip := _config.get_config_value(config, arguments, 'skip_checks', 'vulnerability'):
        combined = '(' + ')|('.join(skip) + ')'

    result: list = []
    for dependency in dependencies:
        (group, artifact) = _utils.get_dependency_identifiers(dependency, ns_mapping)
        (version, _) = _utils.get_version(config, arguments, ns_mapping, root, dependency)

        if skip_no_versions and version and re.match(r'^\${[^}]+}$', version):
            continue
        if combined is None or not re.match(combined, f"{group}:{artifact}:{version}"):
            result.append(f"pkg:maven/{group}/{artifact}@{version}")

    return result


def _oss_index_config(config: Config, arguments: Arguments) -> tuple:
    """
    Get OSS Index parameters.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.

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
            config, arguments, 'oss_index_batch_size', 'vulnerability', default=128),
        _config.get_config_value(
            config, arguments, 'oss_index_keep_safe', 'vulnerability', default=False)
    )


def _fetch_cve_data(
        config: Config, arguments: Arguments, coordinates: list[str]
) -> dict[str, list[Vulnerability]]:
    """
    Get CVE data for coordinates.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        coordinates (list[str]): Coordinates.

    Returns:
        dict[str, list[Vulnerability]]: CVE Data.
    """
    result = {}
    try:
        url, user, token, batch_size, keep_safe = _oss_index_config(config, arguments)
        auth = HTTPBasicAuth(user, token)

        with requests.Session() as session:
            it = iter(coordinates)
            while batch := list(islice(it, batch_size)):
                response = session.post(url, json={"coordinates": batch}, auth=auth)
                if response.status_code != 200:
                    logging.error(f"OSS Index API error: {response.status_code}")
                    continue

                for item in response.json():
                    cves = []
                    if data := item.get('vulnerabilities'):
                        cves = [Vulnerability(**cve) for cve in data]
                    if len(cves) or keep_safe:
                        result.update({item['coordinates']: cves})

    except Exception as e:
        logging.error(f"Failed to _fetch_cve_data: {e}")
    return result
