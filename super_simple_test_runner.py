from distutils.dir_util import copy_tree
import exceptions
import os
import json
import test_report_writer
import argparse

parser = argparse.ArgumentParser(description='Super simple test sequencer.')
parser.add_argument('--single_run', '-s',
                    help='Run only once', action="store_true")


if not os.path.isdir('./test_definitions'):
    my_dir = os.path.dirname(os.path.realpath(__file__))
    copy_tree(my_dir + '/empty_test_definitions', './test_definitions')
    print("Empty test definitions created")
    import sys
    sys.exit()

args = parser.parse_args()

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
            if not all([r[1]['result'] for r in results[test_case].items()]):
                overallresult = False


        finalize_test(overallresult, DUT, INSTRUMENTS)

        results['Overall result'] = overallresult

    except Error as e:
        # TODO: write error to report
        raise
    else:
        pass
    finally:
        pass

    test_report_writer.create_report(json.dumps(results), 'result.html')

    if args.single_run:
        run = False

shutdown()