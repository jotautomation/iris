"""Runs the tests"""
import sys
import os
import json
from test_runner import exceptions
import threading


def get_test_control():
    """Returns default test control dictionary"""
    return {
        'single_run': False,
        'step': False,
        'skip': None,
        'loop_all': False,
        'loop': None,
        'retest_on_fail': 0,
        'terminate': False,
        'run': threading.Event(),
    }


def run_test_runner(test_control):
    """Starts the testing"""

    sys.path.append(os.getcwd())
    sys.path.append(os.path.join(os.getcwd(), 'test_definitions'))

    try:
        import test_definitions
    except ImportError:
        print("No test definitions defined. Create empty definitions with --create argument.")
        sys.exit(-1)

    test_definitions.boot_up()

    tests = [t for t in test_definitions.TESTS if t not in test_definitions.SKIP]

    while not test_control['terminate']:
        # Wait until you are allowed to run again i.e. pause
        test_control['run'].wait()

        results = {}
        overall_results = True

        try:
            dut = test_definitions.prepare_test()

            results["DUT"] = dut

            for test_case in tests:
                test_instance = getattr(test_definitions, test_case)()
                test_instance.test(test_definitions.INSTRUMENTS, dut)
                results[test_case] = test_instance.result_handler(
                    test_definitions.LIMITS[test_case]
                )
                if not all([r[1]["result"] for r in results[test_case].items()]):
                    overall_results = False

            test_definitions.finalize_test(overall_results, dut, test_definitions.INSTRUMENTS)

            results["Overall result"] = overall_results

        except exceptions.Error as e:
            # TODO: write error to report
            raise
        else:
            pass
        finally:
            pass

        test_definitions.create_report(json.dumps(results), dut)

        if test_control['single_run']:
            test_control['terminate'] = True

    test_definitions.shutdown()
