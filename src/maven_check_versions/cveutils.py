#!/usr/bin/python3
"""This file provides cve functions"""

import logging
import re
# noinspection PyPep8Naming
from dataclasses import dataclass

import maven_check_versions.config as _config
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


def _oss_index_config(config: dict, arguments: dict):  # pragma: no cover
    """Get OSS Index parameters.

    Args:
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.

    Returns:
        tuple: OSS Index parameters.
    """
    url = 'https://ossindex.sonatype.org/api/v3/component-report'
    url = _config.get_config_value(config, arguments, 'oss_index_url', 'vulnerability', default=url)
    user = _config.get_config_value(config, arguments, 'oss_index_user', 'vulnerability')
    token = _config.get_config_value(config, arguments, 'oss_index_token', 'vulnerability')

    return token, url, user


# WIP for CVE Checking
def fetch_cve_data(  # pragma: no cover
        coordinates: list[str], config: dict, arguments: dict
) -> dict[str, list[Vulnerability]]:
    """
    Get CVE data for coordinates.

    Args:
        coordinates (list[str]): Coordinates.
        config (dict): Parsed YAML as dict.
        arguments (dict): Command-line arguments.

    Returns:
        dict[str, list[Vulnerability]]: CVE Data.
    """
    result = {}
    if _config.get_config_value(
            config, arguments, 'oss_index_enabled', 'vulnerability', value_type=bool, default='false'
    ):
        try:
            token, url, user = _oss_index_config(config, arguments)
            auth = HTTPBasicAuth(user, token)
            response = requests.post(url, json={"coordinates": coordinates}, auth=auth)
            if response.status_code == 200:
                rgx = '^pkg:maven/(.+)/(.+)@(.+)$'  # NOSONAR
                for item in response.json():
                    if (match := re.match(rgx, item['coordinates'])) and len(data := item.get('vulnerabilities')):
                        result.update({f"{match[1]}:{match[2]}": [Vulnerability(**cve) for cve in data]})
            else:
                logging.error(f"OSS Index API error: {response.status_code}")
        except Exception as e:
            logging.error(f"Failed to fetch_cve_data: {e}")
    return result
