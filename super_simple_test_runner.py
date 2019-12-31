#! /usr/bin/python
"""
Test sequencer for any production testing
"""

import os
import argparse
import sys
import threading
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

if ARGS.single_run:
    CONTROL.single_run = True


RUNNER_THREAD = threading.Thread(
    target=runner.run_test_runner, args=(CONTROL,), name='test_runner_thread'
)

RUNNER_THREAD.start()

if ARGS.listener:
    if ARGS.port:
        PORT = ARGS.port

    listener.create_listener(PORT, CONTROL)
    tornado.ioloop.IOLoop.current().start()


RUNNER_THREAD.join()
