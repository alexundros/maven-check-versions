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
    id: str  # noqa: A003,VNE003
    displayName: str = None  # noqa: N815
    title: str = None
    description: str = None
    cvssScore: float = None  # noqa: N815
    cvssVector: str = None  # noqa: N815
    cve: str = None
    cwe: str = None
    reference: str = None
    externalReferences: list[str] = ()  # noqa: N815
    versionRanges: list[str] = ()  # noqa: N815


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
            url = 'https://ossindex.sonatype.org/api/v3/component-report'
            url = _config.get_config_value(config, arguments, 'oss_index_url', 'vulnerability', default=url)
            user = _config.get_config_value(config, arguments, 'oss_index_user', 'vulnerability')
            token = _config.get_config_value(config, arguments, 'oss_index_token', 'vulnerability')
            response = requests.post(url, json={"coordinates": coordinates}, auth=HTTPBasicAuth(user, token))
            if response.status_code == 200:
                rgx = '^pkg:maven/(.+)/(.+)@(.+)$'  # NOSONAR
                for item in response.json():
                    if (match := re.match(rgx, item['coordinates'])) and (data := item.get('vulnerabilities')):
                        if len(data):
                            result.update({f"{match[1]}:{match[2]}": [Vulnerability(**cve) for cve in data]})
            else:
                logging.error(f"OSS Index API error: {response.status_code}")
        except Exception as e:
            logging.error(f"Failed to fetch_cve_data: {e}")
    return result
