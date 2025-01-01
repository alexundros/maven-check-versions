#!/usr/bin/python3
"""This script processes Maven POM files and checks for dependencies versions"""

import configparser
import datetime
import json
import logging
import math
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from argparse import ArgumentParser
from configparser import ConfigParser
from pathlib import Path, PurePath

# Modules from PACKAGES Env or local packages
lpd = os.path.dirname(__file__)
lsp = os.path.join(lpd, '.site-packages')
sys.path.append(lsp)
if os.getenv('PACKAGES'):
    evp = os.getenv('PACKAGES')
    sys.path.append(evp)
    if not os.path.exists(evp):
        print('Invalid PACKAGES environment')
        sys.exit(1)

import dateutil.parser as parser
import requests
import urllib3
from bs4 import BeautifulSoup


def cli_args() -> dict:
    """
    Parse command line arguments.

    Returns:
        dict: A dictionary containing command line arguments and their values.
    """
    ap = ArgumentParser()
    ap.add_argument('-ci', '--ci_mode', help='CI Mode', action='store_true')
    ap.add_argument('-pf', '--pom', help='POM File')
    ap.add_argument('-fa', '--find', help='Find artifact')
    # override config
    ap.add_argument('-co', '--cache_off', help='Dont use Cache', action='store_true')
    ap.add_argument('-lfo', '--logfile_off', help='Dont use Log file', action='store_true')
    ap.add_argument('-cf', '--config', help='Config File')
    ap.add_argument('-fm', '--fail_mode', help='Fail Mode', action='store_true')
    ap.add_argument('-mjv', '--fail_major', help='Fail Major delta')
    ap.add_argument('-mnv', '--fail_minor', help='Fail Minor delta')
    ap.add_argument('-sp', '--plugins', help='Search plugins', action='store_true')
    ap.add_argument('-sm', '--modules', help='Process modules', action='store_true')
    ap.add_argument('-sk', '--show_skip', help='Show Skip', action='store_true')
    ap.add_argument('-ss', '--show_search', help='Show Search', action='store_true')
    ap.add_argument('-ev', '--empty_version', help='Empty Version', action='store_true')
    ap.add_argument('-si', '--show_invalid', help='Show Invalid', action='store_true')
    ap.add_argument('-un', '--user', help='Basic Auth user')
    ap.add_argument('-up', '--password', help='Basic Auth password')
    return vars(ap.parse_args())


def main_process(args: dict) -> None:
    """
    Main processing function.

    Args:
        args (dict): Dictionary of command line arguments and their values.
    """
    os.chdir(os.path.dirname(__file__))

    cfg = ConfigParser()
    cfg.optionxform = str
    if (cf := args.get('config')) is None:
        cf = Path(__file__).stem + '.cfg'
    if os.path.exists(cf):
        cfg.read(cf)

    if not config_get(cfg, args, 'warnings', 'urllib3', vt=bool):
        urllib3.disable_warnings()

    co = config_get(cfg, args, 'cache_off')
    cfile = Path(__file__).stem + '.cache'
    cache = load_cache(cfile) if not co else None

    if pom := args.get('pom'):
        pom_process(cache, cfg, args, pom)
    elif find := args.get('find'):
        find_process(cache, cfg, args, find)
    else:
        for key, pom in config_items(cfg, 'pom'):
            pom_process(cache, cfg, args, pom)

    if_cache_save(cache, cfile)


def load_cache(file: str) -> dict:
    """
    Load cache from a file.

    Args:
        file (str): Path to the cache file.

    Returns:
        dict: A dictionary representing the loaded cache.
    """
    if os.path.exists(file):
        logging.info(f"Load Cache: {PurePath(file).name}")
        with open(file, 'r') as cf:
            return json.load(cf)
    return dict()


def if_cache_save(cache: dict, file: str) -> None:
    """
    Save cache to a file.

    Args:
        cache (dict): The cache data to be saved.
        file (str): Path to the file where the cache will be saved.
    """
    if cache is not None:
        logging.info(f"Save Cache: {PurePath(file).name}")
        with open(file, 'w') as cf:
            json.dump(cache, cf)


def pom_process(cache: dict, cfg: ConfigParser, args: dict, pom: str, pfx: str = None) -> None:
    """
    Process POM files.

    Args:
        cache (dict): Cache data for dependencies.
        cfg (ConfigParser): Configuration data.
        args (dict): Command line arguments.
        pom (str): Path or URL to the POM file to process.
        pfx (str, optional): Prefix for the artifact name. Defaults to None.
    """
    verify = config_get(cfg, args, 'verify', 'requests', vt=bool)

    if pom.startswith('http'):
        auth = ()
        if config_get(cfg, args, 'auth', 'pom_http', vt=bool):
            usr = config_get(cfg, args, 'user')
            pwd = config_get(cfg, args, 'password')
            auth = (usr, pwd)

        rsp = requests.get(pom, auth=auth, verify=verify)

        if rsp.status_code != 200:
            raise FileNotFoundError(f'{pom} not found')
        tree = ET.ElementTree(ET.fromstring(rsp.text))
    else:
        if not os.path.exists(pom):
            raise FileNotFoundError(f'{pom} not found')
        tree = ET.parse(pom)

    root = tree.getroot()
    ns = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}

    name = root.find('./xmlns:artifactId', namespaces=ns).text
    fnd = root.find('./xmlns:groupId', namespaces=ns)
    name = (fnd.text + ':' if fnd is not None else '') + name
    if pfx is not None:
        name = f"{pfx} / {name}"

    logging.info(f"=== Processing: {name} ===")

    deps = root.findall('.//xmlns:dependency', namespaces=ns)

    if config_get(cfg, args, 'plugins', vt=bool):
        xp = './/xmlns:plugins/xmlns:plugin'
        plugins = root.findall(xp, namespaces=ns)
        for item in plugins:
            deps.append(item)

    deps_process(cache, cfg, args, deps, ns, root, verify)

    if config_get(cfg, args, 'modules', vt=bool):
        dpath = os.path.dirname(pom)
        xp = './/xmlns:modules/xmlns:module'

        for item in root.findall(xp, namespaces=ns):
            mf = f"{dpath}/{item.text}/pom.xml"
            if os.path.exists(mf):
                pom_process(cache, cfg, args, mf, name)


def deps_process(cache: dict, cfg: ConfigParser, args: dict, items: list, ns: dict, root: ET.Element, verify: bool) -> None:
    """
    Process dependencies in a POM file.

    Args:
        cache (dict): Cache object to store dependencies.
        cfg (ConfigParser): Configuration object.
        args (dict): Command-line arguments.
        deps (list): List of dependencies from the POM file.
        ns (dict): XML namespace mapping.
        root (ET.Element): Root XML element of the POM file.
        verify (bool): Whether to verify HTTPS certificates.
    """
    for item in items:
        artifact = item.find('xmlns:artifactId', namespaces=ns)
        if artifact is None:
            continue
        artifact = artifact.text

        group = item.find('xmlns:groupId', namespaces=ns)
        if group is None:
            logging.error(f"Empty groupId in {artifact}")
            continue
        group = group.text

        ver, skip = get_version(cfg, args, group, artifact, ns, root, item)

        if skip is True:
            if config_get(cfg, args, 'show_skip', vt=bool):
                logging.warning(f"Skip: {group}:{artifact}:{ver}")
            continue

        if config_get(cfg, args, 'show_search', vt=bool):
            if ver is None or re.match('^\\${([^}]+)}$', ver):
                logging.warning(f"Search: {group}:{artifact}:{ver}")
            else:
                logging.info(f"Search: {group}:{artifact}:{ver}")

        if (cache is not None and
                cache.get(f"{group}:{artifact}") is not None):

            ct, cv, ck, cd, cvs = cache.get(f"{group}:{artifact}")
            if cv == ver:
                continue

            cct = config_get(cfg, args, 'cache_time', vt=int)

            if cct == 0 or time.time() - ct < cct:
                mf = '*{}: {}:{}, current:{} versions: {} updated: {}'
                cd = cd if cd is not None else ''
                logging.info(mf.format(ck, group, artifact, ver, ', '.join(cvs), cd).rstrip())
                continue

        found = False
        for key, sec in config_items(cfg, 'repositories'):
            if found := process_sec(*(cache, cfg, args, group, artifact, ver, key, sec, verify)):
                break
        if not found:
            logging.warning(f"Not Found: {group}:{artifact}, current:{ver}")


def find_process(cache: dict, cfg: ConfigParser, args: dict, find: str) -> None:
    """
    Process finding artifacts.

    Args:
        cache (dict): Cache data.
        cfg (ConfigParser): Configuration settings.
        args (dict): Command-line arguments.
        find (str): Artifact to search for.
    """
    verify = config_get(cfg, args, 'verify', 'requests', vt=bool)
    group, artifact, ver = find.split(sep=":", maxsplit=3)

    if config_get(cfg, args, 'show_search', vt=bool):
        logging.info(f"Search: {group}:{artifact}:{ver}")

    found = False
    for key, sec in config_items(cfg, 'repositories'):
        if found := process_sec(*(cache, cfg, args, group, artifact, ver, key, sec, verify)):
            break
    if not found:
        logging.warning(f"Not Found: {group}:{artifact}, current:{ver}")


def get_version(cfg: ConfigParser, args: dict, group: str, artifact: str, ns: dict, root: ET.Element, item: ET.Element) -> tuple[str | None, bool]:
    """
    Get version information.

    Args:
        cfg (ConfigParser): The configuration parser.
        args (dict): Dictionary containing the parsed command line arguments.
        group (str): The group ID of the artifact.
        artifact (str): The artifact ID.
        ns (dict): Namespace dictionary for XML parsing.
        root (ET.Element): Root element of the POM file.
        item (ET.Element): Dependency element from which to extract version.

    Returns:
        tuple[str | None, bool]: A tuple containing the resolved version and a boolean indicating if the version should be skipped.
    """
    ver = item.find('xmlns:version', namespaces=ns)

    if ver is None:
        if not config_get(cfg, args, 'empty_version', vt=bool):
            return None, True
    else:
        ver = ver.text
        var_ex = '^\\${([^}]+)}$'

        if m := re.search(var_ex, ver):
            xp = f"./xmlns:properties/xmlns:{m.group(1)}"
            fnd = root.find(xp, namespaces=ns)
            if fnd is not None:
                ver = fnd.text

        if ver == '${project.version}':
            pv = root.find('xmlns:version', namespaces=ns).text
            if m := re.search(var_ex, pv):
                xp = f"./xmlns:properties/xmlns:{m.group(1)}"
                fnd = root.find(xp, namespaces=ns)
                if fnd is not None:
                    pv = fnd.text
            ver = pv

        if re.match(var_ex, ver):
            if not config_get(cfg, args, 'empty_version', vt=bool):
                return ver, True

    return ver, False


def process_sec(cache: dict, cfg: ConfigParser, args: dict, group: str, artifact: str, ver: str, key: str, sec: str, verify: bool) -> bool:
    """
    Process a repository section.

    Args:
        cache (dict): The cache dictionary.
        cfg (ConfigParser): The configuration parser.
        args (dict): Dictionary containing the parsed command line arguments.
        group (str): The group ID of the artifact.
        artifact (str): The artifact ID.
        ver (str): The version of the artifact.
        key (str): The key for the repository section.
        sec (str): The repository section name.
        verify (bool): Whether to verify SSL certificates.

    Returns:
        bool: True if the dependency is found, False otherwise.
    """
    auth = ()
    if config_get(cfg, args, 'auth', sec, vt=bool):
        auth = (
            config_get(cfg, args, 'user'),
            config_get(cfg, args, 'password')
        )

    cbase = config_get(cfg, args, 'base', sec)
    cpath = config_get(cfg, args, 'path', sec)
    crepo = config_get(cfg, args, 'repo', sec)

    path = f"{cbase}/{cpath}"
    if crepo is not None:
        path = f"{path}/{crepo}"
    path = f"{path}/{group.replace('.', '/')}/{artifact}"

    url = path + '/maven-metadata.xml'
    rsp = requests.get(url, auth=auth, verify=verify)

    if rsp.status_code == 200:
        tree = ET.ElementTree(ET.fromstring(rsp.text))
        items = tree.getroot().findall('.//version')
        items = list(map(lambda v: v.text, items))

        if check_versions(*(cache, cfg, args, group, artifact, ver, key, path, auth, verify, items, rsp)):
            return True

    if config_get(cfg, args, 'service_rest', sec, vt=bool):
        return service_rest(*(cache, cfg, args, group, artifact, ver, key, sec, cbase, auth, verify))

    return False


def check_versions(
        cache: dict, cfg: ConfigParser, args: dict, group: str, artifact: str, ver: str, key: str,
        path: str, auth: tuple, verify: bool, versions: list[str], rsp: requests.Response) -> bool:
    """
    Check versions.

    Args:
        cache (dict): The cache dictionary.
        cfg (ConfigParser): The configuration parser.
        args (dict): Dictionary containing the parsed command line arguments.
        group (str): The group ID of the artifact.
        artifact (str): The artifact ID.
        ver (str): The version of the artifact.
        key (str): The key for the repository section.
        path (str): The path to the dependency in the repository.
        auth (tuple): Tuple containing basic authentication credentials.
        verify (bool): Whether to verify SSL certificates.
        versions (list[str]): List of available versions.
        rsp (requests.Response): The response object from the repository.

    Returns:
        bool: True if the current version is valid, False otherwise.
    """
    versions = list(filter(lambda v: re.match('^\\d+.+', v), versions))
    ended = versions[-1]
    versions.reverse()

    if versions[0] != ended:
        logging.warning(f"Last versions: {versions[0:5]}")

    mjv, mnv, vmjv, vmnv = 0, 0, 0, 0
    if config_get(cfg, args, 'fail_mode', vt=bool):
        mjv = int(config_get(cfg, args, 'fail_major'))
        mnv = int(config_get(cfg, args, 'fail_minor'))

        if vm := re.match('^(\\d+).(\\d+).+', ver):
            vmjv, vmnv = int(vm.group(1)), int(vm.group(2))

    skip_curr = config_get(cfg, args, 'skip_current', vt=bool)
    invalid = False

    for item in versions:
        if item == ver and skip_curr:
            if cache is not None:
                ts = math.trunc(time.time())
                cache[f"{group}:{artifact}"] = (ts, item, key, None, versions[0:3])
            return True

        ok, date = pom_data(auth, verify, artifact, item, path)
        if ok:
            mf = '{}: {}:{}, current:{} {} {}'
            logging.info(mf.format(key, group, artifact, ver, versions[0:3], date).rstrip())

            if cache is not None:
                ts = math.trunc(time.time())
                cache[f"{group}:{artifact}"] = (ts, item, key, date, versions[0:3])

            if config_get(cfg, args, 'fail_mode', vt=bool):
                imjv, imnv = 0, 0
                if im := re.match('^(\\d+).(\\d+).+', item):
                    imjv, imnv = int(im.group(1)), int(im.group(2))

                if imjv - vmjv > mjv or imnv - vmnv > mnv:
                    logging.warning(f"Fail version: {item} > {ver}")
                    raise AssertionError
            return True

        else:
            if config_get(cfg, args, 'show_invalid', vt=bool):
                if not invalid:
                    logging.info(rsp.url)
                logging.warning(f"Invalid: {group}:{artifact}:{item}")
            invalid = True

    return False


def service_rest(
        cache: dict, cfg: ConfigParser, args: dict, group: str, artifact: str, ver: str, key: str,
        sec: str, base: str, auth: tuple, verify: bool) -> bool:
    """
    Process REST services.

    Args:
        cache (dict): The cache dictionary.
        cfg (ConfigParser): The configuration parser.
        args (dict): Dictionary containing the parsed command line arguments.
        group (str): The group ID of the artifact.
        artifact (str): The artifact ID.
        ver (str): The version of the artifact.
        key (str): The key for the repository section.
        sec (str): The repository section name.
        base (str): The base URL of the repository.
        auth (tuple): Tuple containing basic authentication credentials.
        verify (bool): Whether to verify SSL certificates.

    Returns:
        bool: True if the dependency is found, False otherwise.
    """
    repo = config_get(cfg, args, 'repo', sec)
    path = f"{base}/service/rest/repository/browse/{repo}"
    path = f"{path}/{group.replace('.', '/')}/{artifact}"

    url = path + '/maven-metadata.xml'
    rsp = requests.get(url, auth=auth, verify=verify)

    if rsp.status_code == 200:
        tree = ET.ElementTree(ET.fromstring(rsp.text))
        items = tree.getroot().findall('.//version')
        items = list(map(lambda v: v.text, items))

        if check_versions(*(cache, cfg, args, group, artifact, ver, key, path, auth, verify, items, rsp)):
            return True

    rsp = requests.get(path + '/', auth=auth, verify=verify)

    if rsp.status_code == 200:
        html = BeautifulSoup(rsp.text, 'html.parser')
        items = html.find('table').find_all('a')
        items = list(map(lambda v: v.text, items))
        path = f"{base}/repository/{repo}/{group.replace('.', '/')}/{artifact}"

        if check_versions(*(cache, cfg, args, group, artifact, ver, key, path, auth, verify, items, rsp)):
            return True

    return False


def pom_data(auth: tuple, verify: bool, artifact: str, ver: str, path: str) -> tuple[bool, str | None]:
    """
    Get POM data.

    Args:
        auth (tuple): Tuple containing basic authentication credentials.
        verify (bool): Whether to verify SSL certificates.
        artifact (str): The artifact ID.
        ver (str): The version of the artifact.
        path (str): The path to the dependency in the repository.

    Returns:
        tuple[bool, str | None]: A tuple containing a boolean indicating if the data was retrieved successfully and the date of the last modification.
    """
    url = f"{path}/{ver}/{artifact}-{ver}.pom"
    rsp = requests.get(url, auth=auth, verify=verify)

    if rsp.status_code == 200:
        hlm = rsp.headers.get('Last-Modified')
        return True, parser.parse(hlm).date().isoformat()

    return False, None


def config_get(cfg: ConfigParser, args: dict, key: str, section: str = 'base', vt=None) -> any | None:
    """
    Get configuration value with optional type conversion.

    Args:
        cfg (ConfigParser): Configuration data.
        args (dict): Command line arguments.
        section (str): Configuration section name.
        option (str, optional): Configuration option name. Defaults to None.
        vt (type, optional): Value type for conversion. Defaults to str.

    Returns:
        Any: Value of the configuration option or None if not found.
    """
    try:
        if section == 'base' and key in args:
            if args.get(key):
                return args[key]

            ek = 'CV_' + key.upper()
            if ev := os.environ.get(ek):
                return ev

        val = cfg.get(section, key)

        if vt == bool:
            return val.lower() == 'true'
        if vt == int:
            return int(val)
        if vt == float:
            return float(val)

        return val
    except configparser.Error:
        return None


def config_items(cfg: ConfigParser, section: str) -> list[tuple[str, str]]:
    """
    Retrieve all items from a configuration section.

    Args:
        cfg (ConfigParser): The configuration parser.
        section (str): The section of the configuration file.

    Returns:
        list[tuple[str, str]]: A list of tuples containing the key-value pairs for the specified section.
    """
    try:
        return cfg.items(section)
    except configparser.Error:
        return []


def configure_logging(args: dict) -> None:
    """
    Configure logging.
    
    Args:
        args (dict): Dictionary containing the parsed command line arguments.
    """
    handlers = [logging.StreamHandler(sys.stdout)]

    if not args.get('logfile_off'):
        lfd = os.path.dirname(__file__)
        lf = os.path.join(lfd, Path(__file__).stem + '.log')
        handlers.append(logging.FileHandler(lf, 'w'))

    logging.Formatter.formatTime = lambda self, record, fmt=None: \
        datetime.datetime.fromtimestamp(record.created)

    logging.basicConfig(
        level=logging.INFO, handlers=handlers,
        format='%(asctime)s %(levelname)s: %(message)s'
    )


def main() -> None:
    is_ex = False
    ci_mode = False

    try:
        start = time.time()
        args = cli_args()
        configure_logging(args)
        ci_mode = args.get('ci_mode')

        main_process(args)

        end = f"{time.time() - start:.2f} sec."
        logging.info(f"Processing is completed, {end}")

    except FileNotFoundError as ex:
        is_ex = True
        logging.exception(ex)

    except AssertionError:
        is_ex = True

    except KeyboardInterrupt:
        is_ex = True
        logging.warning('Processing is interrupted')

    except SystemExit:  # NOSONAR
        is_ex = True

    except Exception as ex:
        is_ex = True
        logging.exception(ex)

    try:
        if not ci_mode:
            input('Press Enter to continue')
    except KeyboardInterrupt:
        pass
    except UnicodeDecodeError:
        pass
    sys.exit(1 if is_ex else 0)


if __name__ == '__main__':
    main()
