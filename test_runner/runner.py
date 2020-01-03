"""Runs the tests"""
import sys
import os
import json
import pprint
from test_runner import exceptions
import threading
from datetime import datetime


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
        'report_off': False,
        'run': threading.Event(),
    }


def run_test_runner(test_control, message_queue):
    """Starts the testing"""

    def report_progress(step, message=None, dut=None):

        if step == report_progress.previous_step:
            msg = step + " finished in " + str(datetime.now() - report_progress.start_time)
        else:
            msg = (step + " started at " + str(datetime.now()))
            report_progress.previous_step = step
            report_progress.start_time = datetime.now()

        if dut:
            msg = msg + " [DUT: " + str(dut) + "]"

        if message:
            msg = msg + ": " + message

        message_queue.put(msg)

    report_progress.start_time = None
    report_progress.previous_step = None

    sys.path.append(os.getcwd())
    sys.path.append(os.path.join(os.getcwd(), 'test_definitions'))

    try:
        import test_definitions
    except ImportError:
        print("No test definitions defined. Create empty definitions with --create argument.")
        sys.exit(-1)

    report_progress("Boot")
    test_definitions.boot_up()
    report_progress("Boot")

    tests = [t for t in test_definitions.TESTS if t not in test_definitions.SKIP]

    while not test_control['terminate']:
        # Wait until you are allowed to run again i.e. pause
        test_control['run'].wait()

        results = {}
        overall_results = True

        try:
            report_progress("Prepare")
            dut = test_definitions.prepare_test()
            report_progress("Prepare", dut=dut)

            results["DUT"] = dut

            for test_case in tests:

                report_progress(test_case, dut=dut)

                test_instance = getattr(test_definitions, test_case)()
                test_instance.test(test_definitions.INSTRUMENTS, dut)
                results[test_case] = test_instance.result_handler(
                    test_definitions.LIMITS[test_case]
                )
                if not all([r[1]["result"] for r in results[test_case].items()]):
                    overall_results = False

                report_progress(test_case, dut=dut, message=pprint.pformat(results[test_case]))

            report_progress("finalize", dut=dut, message="Overall result " + str(overall_results))
            test_definitions.finalize_test(overall_results, dut, test_definitions.INSTRUMENTS)
            report_progress("finalize", dut=dut, message="Overall result " + str(overall_results))

            results["Overall result"] = overall_results

        except exceptions.Error as e:
            # TODO: write error to report
            raise
        else:
            pass
        finally:
            pass

        report_progress("Create test report", dut=dut)
        if test_control['report_off']:
            report_progress("Create test report", dut=dut, message="Test report creation skipped")
        else:
            test_definitions.create_report(json.dumps(results), dut)
            report_progress("Create test report", dut=dut)

        if test_control['single_run']:
            test_control['terminate'] = True

    report_progress("Shutdown")

    test_definitions.shutdown()

    report_progress("Shutdown")
