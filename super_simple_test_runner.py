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
import listener
import tornado

PORT = 4321

PARSER = argparse.ArgumentParser(description="Super simple test sequencer.")
PARSER.add_argument("--single_run", "-s", help="Run only once", action="store_true")
PARSER.add_argument(
    "--create", "-c", help="Creates empty/example test definitions", action="store_true"
)
PARSER.add_argument("--report_off", "-r", help="Don't create test report", action="store_true")
PARSER.add_argument(
    "--listener",
    "-l",
    help="Creates HTTP listener. Testing is then started through REST API.",
    action="store_true",
)
PARSER.add_argument('-p', '--port', help="Set port to listen", type=int)

ARGS = PARSER.parse_args()

if ARGS.create:
    if os.path.isdir("./test_definitions"):
        print("test_definitions folder already exists")
        sys.exit(-1)

    import empty_test_definitions

    copy_tree(empty_test_definitions.__path__[0], "./test_definitions")
    print("Empty test definitions created")

    sys.exit()


CONTROL = runner.get_test_control()
DEFINITIONS = runner.get_test_definitions()

CONTROL['run'].set()

if ARGS.single_run:
    CONTROL['single_run'] = True

if ARGS.report_off:
    CONTROL['report_off'] = True

MESSAGE_QUEUE = Queue()
PROGRESS_QUEUE = Queue()

RUNNER_THREAD = threading.Thread(
    target=runner.run_test_runner,
    args=(CONTROL, MESSAGE_QUEUE, PROGRESS_QUEUE),
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

    listener.create_listener(PORT, CONTROL, MESSAGE_HANDLER, PROGRESS_HANDLER, DEFINITIONS)
    tornado.ioloop.IOLoop.current().start()

MESSAGE_HANDLER = print

RUNNER_THREAD.join()
