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
        'get_sn_from_ui': False,
    }


def get_test_definitions():
    """Returns test definitions"""

    sys.path.append(os.getcwd())
    sys.path.append(os.path.join(os.getcwd(), 'test_definitions'))

    try:
        import test_definitions
    except ImportError:
        print("No test definitions defined. Create empty definitions with --create argument.")
        sys.exit(-1)

    return test_definitions


def get_sn_from_ui():
    # This will come from UI
    import uuid

    return {
        "left": {'sn': str(uuid.uuid4())},
        "right": {'sn': str(uuid.uuid4())},
        "middle": {'sn': str(uuid.uuid4())},
    }


def run_test_runner(test_control, message_queue, progess_queue):
    """Starts the testing"""

    def send_message(message):
        if message:
            message_queue.put(message)

    def report_progress(general_step, duts=None, overall_result=None):

        progress_json = {"general_state": general_step, "duts": duts}
        if overall_result:
            progress_json['overall_result'] = overall_result

        progess_queue.put(json.dumps(progress_json))

    report_progress.start_time = None
    report_progress.previous_step = None

    test_definitions = get_test_definitions()

    report_progress("Boot")
    test_definitions.boot_up()

    tests = [t for t in test_definitions.TESTS if t not in test_definitions.SKIP]

    while not test_control['terminate']:
        # Wait until you are allowed to run again i.e. pause
        test_control['run'].wait()

        results = {}
        overall_result = True
        dut_status = {}
        try:

            report_progress("Prepare")

            if test_control['get_sn_from_ui']:

                for dut in test_definitions.DUT:
                    dut_status[dut] = {'step': None, 'status': 'waiting_test', 'sn': None}

                report_progress("Prepare", duts=dut_status)

                duts = get_sn_from_ui()
            else:
                duts = test_definitions.prepare_test()

            for dut_key, dut_value in duts.items():
                dut_status[dut_key] = {
                    'step': None,
                    'status': 'waiting_test',
                    'sn': dut_value['sn'],
                }

            for test_case in tests:

                for dut_name, dut_value in duts.items():
                    dut_sn = dut_value['sn']
                    dut_status[dut_name]['step'] = test_case
                    dut_status[dut_name]['status'] = 'testing'

                    report_progress('testing', dut_status)

                    results[dut_sn] = {}
                    results[dut_sn]["test_position"] = dut_name

                    test_instance = getattr(test_definitions, test_case)()
                    test_instance.test(test_definitions.INSTRUMENTS, dut_sn)
                    results[dut_sn][test_case] = test_instance.result_handler(
                        test_definitions.LIMITS[test_case]
                    )
                    if not all([r[1]["result"] for r in results[dut_sn][test_case].items()]):
                        overall_result = False
                        dut_status[dut_name]['status'] = 'failed'
                        dut_status[dut_name]['failed_step'] = test_case

                    report_progress('testing', dut_status)

            report_progress('finalize', dut_status, overall_result=overall_result)
            test_definitions.finalize_test(overall_result, duts, test_definitions.INSTRUMENTS)

            results["Overall result"] = overall_result

        except exceptions.Error as e:
            # TODO: write error to report
            raise
        else:
            pass
        finally:
            pass

        report_progress("Create test report")
        if not test_control['report_off']:
            test_definitions.create_report(json.dumps(results), duts)

        if test_control['single_run']:
            test_control['terminate'] = True

    report_progress("Shutdown")

    test_definitions.shutdown()

    report_progress("Shutdown")
