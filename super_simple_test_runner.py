#! /usr/bin/python
"""
Test sequencer for any production testing
"""

import os
import argparse
import sys
import threading
from queue import Queue
from distutils.dir_util import copy_tree
from test_runner import runner
import listener.listener as listener
import logging
import tornado
import json
import pathlib
import yaml
import coloredlogs
import logging.config

PORT = 4321

PARSER = argparse.ArgumentParser(description="Super simple test sequencer.")
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
    "-v",
    "--verbose",
    help="Increase output verbosity. Sets colored console logging to debug level.",
    action="store_true",
)

PARSER.add_argument(
    '--no_colored_logs', '-n', help='Disables colored logs on console.', action="store_true"
)

PARSER.add_argument(
    "--list-applications",
    "-a",
    help="Lists available application on the connected Gaia tester (G5 or other). Gaia instrument must be defined and available.",
    action="store_true",
)

PARSER.add_argument('-p', '--port', help="Set port to listen", type=int)

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

if not ARGS.no_colored_logs:
    HANDLERS = logging.getLogger().handlers
    CONSOLE_LOG_LEVEL = list(
        filter(lambda x: x and x.name and x.name.lower() == 'console', HANDLERS)
    )

    if CONSOLE_LOG_LEVEL:
        CONSOLE_LOG_LEVEL = CONSOLE_LOG_LEVEL[0].level
        if ARGS.verbose:
            CONSOLE_LOG_LEVEL = logging.DEBUG

        coloredlogs.install(level=CONSOLE_LOG_LEVEL, milliseconds=True)

LOGGER = logging.getLogger(__name__)

LOGGER.debug("Logging initialized")

if ARGS.create:

    from test_definition_template import example_sequence

    TEST_DEF_PATH = os.path.join("./test_definitions", ARGS.create[0])

    if os.path.isdir(TEST_DEF_PATH):
        print("test_definitions folder already exists")
        sys.exit(-1)

    copy_tree(example_sequence.__path__[0], TEST_DEF_PATH)

    if not os.path.isdir('./test_definitions/common'):
        from test_definition_template import common

        copy_tree(common.__path__[0], './test_definitions/common')

        import dist_files
        from shutil import copyfile
        copyfile(dist_files.__path__[0] + '/Dockerfile', './Dockerfile')
    else:
        print('./test_definitions/common already exists. Not copying it.')

    sys.exit(0)

CONTROL = runner.get_test_control()
COMMON_DEFINITIONS = runner.get_common_definitions()

if ARGS.list_applications:
    # Print available applications and actions
    class GaiaJsonEncoder(json.JSONEncoder):
        '''Encode json properly'''

        def default(self, obj):
            if callable(obj):
                return obj.__name__
            # Let the base class default method raise the TypeError
            return json.JSONEncoder.default(self, obj)

    COMMON_DEFINITIONS.instrument_initialization()

    client = COMMON_DEFINITIONS.INSTRUMENTS['gaia']

    print(json.dumps(client.applications, indent=4, sort_keys=True, cls=GaiaJsonEncoder))
    print(json.dumps(client.state_triggers, indent=4, sort_keys=True, cls=GaiaJsonEncoder))
    sys.exit()

CONTROL['run'].set()

if ARGS.single_run:
    CONTROL['single_run'] = True

if ARGS.report_off:
    CONTROL['report_off'] = True

DUT_SN_QUEUE = Queue()
MESSAGE_QUEUE = Queue()
PROGRESS_QUEUE = Queue()

RUNNER_THREAD = threading.Thread(
    target=runner.run_test_runner,
    args=(CONTROL, MESSAGE_QUEUE, PROGRESS_QUEUE, DUT_SN_QUEUE),
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


MESSAGE_HANDLER = [print]

MESSAGE_THREAD = threading.Thread(
    target=MessageHandler, args=(MESSAGE_QUEUE, MESSAGE_HANDLER), name='message_thread'
)

PROGRESS_HANDLER = [print]

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

    listener.create_listener(
        PORT, CONTROL, MESSAGE_HANDLER, PROGRESS_HANDLER, COMMON_DEFINITIONS, DUT_SN_QUEUE
    )
    tornado.ioloop.IOLoop.current().start()

MESSAGE_HANDLER = print

RUNNER_THREAD.join()
