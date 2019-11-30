#! /usr/bin/python
from distutils.dir_util import copy_tree
from test_runner import exceptions
import os
import json
from test_runner import test_report_writer
import argparse
import sys


parser = argparse.ArgumentParser(description="Super simple test sequencer.")
parser.add_argument("--single_run", "-s", help="Run only once", action="store_true")


if not os.path.isdir("./test_definitions"):
    import empty_test_definitions

    copy_tree(empty_test_definitions.__path__[0], "./test_definitions")
    print("Empty test definitions created")
    import sys

    sys.exit()

args = parser.parse_args()

sys.path.append(os.getcwd())
from test_definitions import *

boot_up()

TESTS = [t for t in TESTS if t not in SKIP]

run = True

while run:

    results = {}
    overallresult = True

    try:
        DUT = prepare_test()

        results["DUT"] = DUT

        for test_case in TESTS:
            test_instance = globals()[test_case]()
            test_instance.test(INSTRUMENTS, DUT)
            results[test_case] = test_instance.result_handler(LIMITS[test_case])
            if not all([r[1]["result"] for r in results[test_case].items()]):
                overallresult = False

        finalize_test(overallresult, DUT, INSTRUMENTS)

        results["Overall result"] = overallresult

    except exceptions.Error as e:
        # TODO: write error to report
        raise
    else:
        pass
    finally:
        pass

    test_report_writer.create_report(json.dumps(results), "result.html")

    if args.single_run:
        run = False

shutdown()
