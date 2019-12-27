#! /usr/bin/python
"""
Test sequencer for any production testing
"""

import os
import json
import argparse
import sys
from distutils.dir_util import copy_tree
from test_runner import exceptions


PARSER = argparse.ArgumentParser(description="Super simple test sequencer.")
PARSER.add_argument("--single_run", "-s", help="Run only once", action="store_true")
PARSER.add_argument(
    "--create", "-c", help="Creates empty/example test definitions", action="store_true"
)

ARGS = PARSER.parse_args()

if ARGS.create:
    if os.path.isdir("./test_definitions"):
        print("test_definitions folder already exists")
        sys.exit(-1)

    import empty_test_definitions

    copy_tree(empty_test_definitions.__path__[0], "./test_definitions")
    print("Empty test definitions created")

    sys.exit()


sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'test_definitions'))

try:
    import test_definitions
except ImportError:
    print("No test definitions defined. Create empty definitions with --create argument.")
    sys.exit(-1)

test_definitions.boot_up()

TESTS = [t for t in test_definitions.TESTS if t not in test_definitions.SKIP]

RUN = True

while RUN:

    RESULTS = {}
    OVERALL_RESULTS = True

    try:
        DUT = test_definitions.prepare_test()

        RESULTS["DUT"] = DUT

        for test_case in TESTS:
            test_instance = getattr(test_definitions, test_case)()
            test_instance.test(test_definitions.INSTRUMENTS, DUT)
            RESULTS[test_case] = test_instance.result_handler(test_definitions.LIMITS[test_case])
            if not all([r[1]["result"] for r in RESULTS[test_case].items()]):
                OVERALL_RESULTS = False

        test_definitions.finalize_test(OVERALL_RESULTS, DUT, test_definitions.INSTRUMENTS)

        RESULTS["Overall result"] = OVERALL_RESULTS

    except exceptions.Error as e:
        # TODO: write error to report
        raise
    else:
        pass
    finally:
        pass

    test_definitions.create_report(json.dumps(RESULTS), DUT)

    if ARGS.single_run:
        RUN = False

test_definitions.shutdown()
