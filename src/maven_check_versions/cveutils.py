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
from maven_check_versions.config import Config, Arguments
from requests.auth import HTTPBasicAuth


@dataclass
class Vulnerability:
    """
    Vulnerability.
    """
    id: str  # NOSONAR # noqa: A003,VNE003
    displayName: str | None = None  # NOSONAR # noqa: N815
    title: str | None = None  # NOSONAR
    description: str | None = None  # NOSONAR
    cvssScore: float | None = None  # NOSONAR # noqa: N815
    cvssVector: str | None = None  # NOSONAR # noqa: N815
    cve: str | None = None  # NOSONAR
    cwe: str | None = None  # NOSONAR
    reference: str | None = None  # NOSONAR
    externalReferences: list | None = None  # NOSONAR # noqa: N815
    versionRanges: list | None = None  # NOSONAR # noqa: N815


def get_cve_data(  # pragma: no cover
        config: Config, arguments: Arguments, dependencies: list[ET.Element],
        root: ET.Element, ns_mapping: dict
) -> dict[str, list[Vulnerability]]:
    """
    Get CVE data for dependencies.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        dependencies (list[ET.Element]): Dependencies.
        root (ET.Element): Root element of the POM file.
        ns_mapping (dict): XML namespace mapping.

    Returns:
        dict[str, list[Vulnerability]]: CVE Data.
    """
    result = {}
    if _config.get_config_value(config, arguments, 'oss_index_enabled', 'vulnerability', default=False):
        coordinates = _get_coordinates(config, arguments, dependencies, ns_mapping, root)

        if cache_data := load_cache(config, arguments, 'vulnerability'):
            for item in coordinates:
                if cache_data.get(item) is not None:
                    coordinates.remove(item)

        for key, data in cache_data.items():
            cache_data.update({key: [Vulnerability(**item) for item in data]})

        if cve_data := _fetch_cve_data(config, arguments, coordinates):
            cache_data.update({key: cves for key, cves in cve_data.items()})
            save_cache(config, arguments, cache_data, 'vulnerability')

        result.update(cache_data)
    return result


def log_vulnerability(  # pragma: no cover
        config: Config, arguments: Arguments, group: str, artifact: str, version: str | None,
        cve_data: dict[str, list[Vulnerability]] | None
) -> None:
    """
    Log vulnerability.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        group (str): Group ID.
        artifact (str): Artifact ID.
        version (str | None): Dependency version.
        cve_data (dict[str, list[Vulnerability]] | None): CVE Data.
    """
    fail_score = _config.get_config_value(config, arguments, 'fail-score', 'vulnerability', default=0)

    if cve_data is not None and (cves := cve_data.get(f"pkg:maven/{group}/{artifact}@{version}")):
        for cve in cves:
            info = f"cvssScore={cve.cvssScore} cve={cve.cve} cwe={cve.cwe} {cve.reference} {cve.title}"
            logging.warning(f"Vulnerability for {group}:{artifact}:{version}: {info}")

            if fail_score and cve.cvssScore >= fail_score:
                logging.error(f"cvssScore={cve.cvssScore} >= fail-score={fail_score}")
                raise AssertionError


def _get_coordinates(config, arguments, dependencies, ns_mapping, root) -> list:  # pragma: no cover
    """
    Get Coordinates.

    Args:
        config (Config): Parsed YAML as dict.
        arguments (Arguments): Command-line arguments.
        dependencies (list[ET.Element]): Dependencies.
        root (ET.Element): Root element of the POM file.
        ns_mapping (dict): XML namespace mapping.

    Returns:
        list: Coordinates.
    """
    skip_no_versions = _config.get_config_value(
        config, arguments, 'skip-no-versions', 'vulnerability', default=False)
    combined = None
    if skip := _config.get_config_value(config, arguments, 'skip-checks', 'vulnerability'):
        combined = '(' + ')|('.join(skip) + ')'

    result: list = []
    for dependency in dependencies:
        (group, artifact) = _utils.get_dependency_identifiers(dependency, ns_mapping)
        (version, _) = _utils.get_version(config, arguments, ns_mapping, root, dependency)

        if skip_no_versions and version and re.match('^\\${[^}]+}$', version):
            continue
        if combined is None or not re.match(combined, f"{group}:{artifact}:{version}"):
            list.append(result, f"pkg:maven/{group}/{artifact}@{version}")

    return result


def _oss_index_config(config: Config, arguments: Arguments) -> tuple:  # pragma: no cover
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


def _fetch_cve_data(  # pragma: no cover
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

        for i in range(0, len(coordinates), batch_size):
            batch = coordinates[i:i + batch_size]
            response = requests.post(url, json={"coordinates": batch}, auth=auth)
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
        logging.error(f"Failed to fetch_cve_data: {e}")
    return result
