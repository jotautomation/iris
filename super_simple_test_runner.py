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
import tornado
import json

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
    "--list-applications",
    "-a",
    help="Lists available application on the connected Gaia tester (G5 or other). Gaia instrument must be defined and available.",
    action="store_true",
)

PARSER.add_argument('-p', '--port', help="Set port to listen", type=int)

ARGS = PARSER.parse_args()

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
    else:
        print('./test_definitions/common already exists. Not copying it.')

    if not os.path.isdir('./ui'):
        import ui

        copy_tree(ui.__path__[0], './ui')
    else:
        print('./ui already exists. Not copying it.')

    print("Test definition template created")

    sys.exit()


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
