#! /usr/bin/python
"""
Test sequencer for any production testing
"""

import os
import argparse
import sys
import threading
from queue import Queue
from test_runner import runner
import listener.listener as listener
import logging
import tornado
import json
import pathlib
import yaml
import logging.config


PORT = 4321

PARSER = argparse.ArgumentParser(description="Iris test sequencer.")
PARSER.add_argument("--single_run", "-s", help="Run only once", action="store_true")
PARSER.add_argument(
    "--create",
    "-c",
    metavar='path',
    type=str,
    nargs=1,
    help="Creates empty/example test COMMON_definitions",
)
PARSER.add_argument("--report_off", "-r", help="Don't create test report", action="store_true")
PARSER.add_argument(
    "--listener",
    "-l",
    help="Creates HTTP listener. Testing is then started through REST API.",
    action="store_true",
)

PARSER.add_argument(
    "-d",
    "--dry-run",
    help="Replaces instruments with mock objects.",
    action="store_true",
)

PARSER.add_argument(
    "-m",
    "--mock",
    help=r"""Replaces listed instruments with mock objects. Usage: iris.py -m INSTRUMENT1 INSTRUMENT2 ...""",
    nargs='+'
)

PARSER.add_argument(
    "-i",
    "--inverse-mock",
    help=r"""Replaces all but listed instruments with mock objects. Usage: iris.py -m INSTRUMENT1 INSTRUMENT2 ...""",
    nargs='+'
)

PARSER.add_argument(
    "-v",
    "--verbose",
    help="Increase output verbosity. Sets root logger to debug level.",
    action="store_true",
)

PARSER.add_argument(
    "-b",
    "--no-browser",
    help="Don't try to open web browser.",
    action="store_true",
)

PARSER.add_argument(
    "--list-applications",
    "-a",
    help="Lists available application on the connected Gaia tester (G5 or other). Gaia instrument must be defined and available.",
    action="store_true",
)

PARSER.add_argument('-p', '--port', help="Set port to listen", type=int)
PARSER.add_argument(
    "-plc",
    "--plc-module",
    help=r"""Starting plc instrument to specific module and station. Usage: iris.py -plc MODULE STATION""",
    nargs='+'
)

ARGS = PARSER.parse_args()


LOG_SETTINGS_FILE = pathlib.Path('test_definitions/common/logging.yaml')


if LOG_SETTINGS_FILE.is_file():
    with LOG_SETTINGS_FILE.open() as _f:
        LOG_CONF = yaml.safe_load(_f.read())
    pathlib.Path(LOG_CONF['log_file_path']).mkdir(parents=True, exist_ok=True)
    logging.config.dictConfig(LOG_CONF)
    logging.info('Logging with configuration from %s', LOG_SETTINGS_FILE)
else:
    logging.basicConfig(level=logging.INFO)
    logging.warning('Cannot find logging settings. Logging with basicConfig.')

if ARGS.verbose:
    logging.getLogger().setLevel(logging.DEBUG)

LOGGER = logging.getLogger(__name__)

LOGGER.debug("Logging initialized")
LOGGER.info("Logging initialized")

if ARGS.create:

    from distutils.dir_util import copy_tree
    from test_definition_template.sequences import example_sequence
    from test_definition_template import test_case_pool

    TEST_DEF_PATH = os.path.join("./test_definitions/sequences", ARGS.create[0])

    if os.path.isdir(TEST_DEF_PATH):
        LOGGER.warning("Test sequence " + ARGS.create[0] + " already exists")
        sys.exit(-1)

    copy_tree(example_sequence.__path__[0], TEST_DEF_PATH)
    copy_tree(test_case_pool.__path__[0], './test_definitions/test_case_pool')

    if not os.path.isdir('./test_definitions/common'):
        from test_definition_template import common

        copy_tree(common.__path__[0], './test_definitions/common')

        import additional_dist_files
        from shutil import copyfile

        copyfile(additional_dist_files.__path__[0] + '/Dockerfile', './Dockerfile')
        copyfile(additional_dist_files.__path__[0] + '/docker-compose.yml', './docker-compose.yml')
    else:
        LOGGER.info('./test_definitions/common already exists. Not copying it.')

    sys.exit(0)

CONTROL = runner.get_test_control(LOGGER)
COMMON_DEFINITIONS = runner.get_common_definitions()
SETTINGS_FILE = pathlib.Path('station_settings.yaml')

if SETTINGS_FILE.is_file():
    with SETTINGS_FILE.open() as _f:
        COMMON_DEFINITIONS.SETTINGS = yaml.safe_load(_f.read())

if ARGS.list_applications:
    # Print available applications and actions
    class GaiaJsonEncoder(json.JSONEncoder):
        '''Encode json properly'''

        def default(self, obj):
            if callable(obj):
                return obj.__name__
            # Let the base class default method raise the TypeError
            return json.JSONEncoder.default(self, obj)

    # Todo: Initialization not working like this anymore
    COMMON_DEFINITIONS.instrument_initialization()

    client = COMMON_DEFINITIONS.INSTRUMENTS['gaia']

    print(json.dumps(client.applications, indent=4, sort_keys=True, cls=GaiaJsonEncoder))
    print(json.dumps(client.state_triggers, indent=4, sort_keys=True, cls=GaiaJsonEncoder))
    sys.exit()

CONTROL['run'].set()

if ARGS.dry_run:
    CONTROL['dry_run'] = True

if ARGS.mock:
    CONTROL['mock'] = ARGS.mock

if ARGS.inverse_mock:
    CONTROL['inverse_mock'] = ARGS.inverse_mock

if ARGS.single_run:
    CONTROL['single_run'] = True

if ARGS.report_off:
    CONTROL['report_off'] = True

if ARGS.plc_module:
    CONTROL['plc_module'] = ARGS.plc_module

DUT_SN_QUEUE = Queue()
MESSAGE_QUEUE = Queue()
PROGRESS_QUEUE = Queue()
LISTENER_ARGS = {'database': None, 'download_path': None}

if hasattr(COMMON_DEFINITIONS, 'listener_args'):
        COMMON_DEFINITIONS.listener_args(LISTENER_ARGS)

RUNNER_THREAD = threading.Thread(
    target=runner.run_test_runner,
    args=(CONTROL, MESSAGE_QUEUE, PROGRESS_QUEUE, DUT_SN_QUEUE, LISTENER_ARGS),
    name='test_runner_thread',
)
RUNNER_THREAD.daemon = True
RUNNER_THREAD.start()


class MessageHandler:
    def __init__(self, message_queue, message_handler):
        while True:
            msg = message_queue.get()
            for handler in message_handler:
                handler(msg)


MESSAGE_HANDLER = []

# If you want to also print message, add print handler like this:
# MESSAGE_HANDLER = [print]

MESSAGE_THREAD = threading.Thread(
    target=MessageHandler, args=(MESSAGE_QUEUE, MESSAGE_HANDLER), name='message_thread'
)

PROGRESS_HANDLER = []

# If you want to also print message, add print handler like this:
# PROGRESS_HANDLER = [print]


PROGRESS_THREAD = threading.Thread(
    target=MessageHandler, args=(PROGRESS_QUEUE, PROGRESS_HANDLER), name='progress_thread'
)

PROGRESS_THREAD.daemon = True
MESSAGE_THREAD.daemon = True

PROGRESS_THREAD.start()
MESSAGE_THREAD.start()

if ARGS.listener:
    if ARGS.port:
        PORT = ARGS.port
    if not ARGS.no_browser:
        import webbrowser

        webbrowser.open("http://localhost:" + str(PORT))

    listener.create_listener(
        PORT,
        CONTROL,
        MESSAGE_HANDLER,
        PROGRESS_HANDLER,
        COMMON_DEFINITIONS,
        DUT_SN_QUEUE,
        LISTENER_ARGS,
    )
    tornado.ioloop.IOLoop.current().start()

# MESSAGE_HANDLER = print

RUNNER_THREAD.join()
