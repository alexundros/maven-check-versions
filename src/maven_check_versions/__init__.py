#!/usr/bin/python3
"""Main entry point for the package"""

import importlib.util
import logging
import os
import sys
import time

if importlib.util.find_spec('maven_check_versions') is None:  # pragma: no cover
    sys.path.append(os.path.dirname(__file__) + '/..')

import maven_check_versions.logutils as _logutils
import maven_check_versions.process as _process
import maven_check_versions.utils as _utils


# noinspection PyMissingOrEmptyDocstring
def main() -> None:
    exception_occurred = False
    ci_mode_enabled = False

    try:
        start_time = time.time()
        arguments = _utils.parse_command_line()
        _logutils.configure_logging(arguments)
        ci_mode_enabled = arguments.get('ci_mode')  # type: ignore

        _process.process_main(arguments)

        elapsed_time = f"{time.time() - start_time:.2f} sec."
        logging.info(f"Processing is completed, {elapsed_time}")

    except FileNotFoundError as ex:
        exception_occurred = True
        logging.exception(ex)

    except AssertionError:
        exception_occurred = True

    except KeyboardInterrupt:
        exception_occurred = True
        logging.warning('Processing is interrupted')

    except SystemExit:  # NOSONAR
        exception_occurred = True

    except Exception as ex:
        exception_occurred = True
        logging.exception(ex)

    try:
        if not ci_mode_enabled:
            input('Press Enter to continue')
    except (KeyboardInterrupt, UnicodeDecodeError):
        pass
    sys.exit(1 if exception_occurred else 0)


if __name__ == '__main__':
    main()
