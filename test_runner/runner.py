"""Runs the tests"""
import datetime
import sys
import os
import json
import importlib
import threading
from test_runner import exceptions


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
        'get_sn_from_ui': get_common_definitions().SN_FROM_UI,
        'test_sequences': get_common_definitions().TEST_SEQUENCES,
    }


def get_common_definitions():
    """Returns test definitions"""

    sys.path.append(os.getcwd())
    sys.path.append(os.path.join(os.getcwd(), 'test_definitions'))

    try:
        import common

        # TODO: This hides also errors on nested imports
    except ImportError as err:
        print(err)
        print("No test definitions defined? Create definition template with --create argument.")
        sys.exit(-1)

    return common


def get_test_definitions(sequence_name):
    """Returns test definitions"""

    sys.path.append(os.getcwd())
    sys.path.append(os.path.join(os.getcwd(), 'test_definitions'))

    try:
        imp = importlib.import_module(sequence_name)
    except ImportError as err:
        print(
            "Error loading "
            + sequence_name
            + ". Remember, you can create new definition template with --create argument."
        )
        print(err)
        print(sys.exc_info()[0])
        sys.exit(-1)

    return imp


def get_sn_from_ui(dut_sn_queue):
    """Returns serial numbers from UI"""

    sequence = None
    common_definitions = get_common_definitions()
    duts_sn = {dut: {'sn': None} for dut in common_definitions.DUTS}
    print('Wait SNs from UI for duts: ' + str(common_definitions.DUTS))
    while True:
        msg = dut_sn_queue.get()

        try:
            msg = json.loads(msg)
            for dut in msg:
                if dut in duts_sn:
                    duts_sn[dut]['sn'] = msg[dut]
            if 'sequence' in msg:
                sequence = msg['sequence']

        except (AttributeError, json.decoder.JSONDecodeError):
            pass

        # Loop until all DUTs have received a serial number
        for dut in duts_sn:
            if not duts_sn[dut]['sn']:
                break
        else:
            print("All DUT serial numbers received from UI")
            print("Selected test sequence", sequence)
            break

    return (duts_sn, sequence)


def run_test_runner(test_control, message_queue, progess_queue, dut_sn_queue):
    """Starts the testing"""

    def send_message(message):
        if message:
            message_queue.put(message)

    def report_progress(general_step, duts=None, overall_result=None, sequence=None):

        progress_json = {
            "general_state": general_step,
            "duts": duts,
            "sequence": sequence,
            "get_sn_from_ui": test_control['get_sn_from_ui'],
            "test_sequences": test_control['test_sequences'],
        }

        if overall_result:
            progress_json['overall_result'] = overall_result

        test_control['progress'] = progress_json
        progess_queue.put(json.dumps(progress_json, default=str))

    common_definitions = get_common_definitions()

    report_progress("Boot")

    common_definitions.instrument_initialization()

    common_definitions.boot_up()

    last_dut_status = {}
    dut_status = {}

    while not test_control['terminate']:
        # Wait until you are allowed to run again i.e. pause
        test_control['run'].wait()

        try:

            report_progress("Prepare", dut_status)

            if test_control['get_sn_from_ui']:

                for dut in common_definitions.DUTS:
                    dut_status[dut] = {'step': None, 'status': 'wait', 'sn': None}
                    if dut in last_dut_status:
                        dut_status[dut]['test_status'] = last_dut_status[dut]['test_status']
                    else:
                        dut_status[dut]['test_status'] = 'idle'

                report_progress("Prepare", duts=dut_status)

                duts, sequence = get_sn_from_ui(dut_sn_queue)
            else:
                duts, sequence = common_definitions.prepare_test(common_definitions.INSTRUMENTS)

            results = {}
            overall_result = True

            test_definitions = get_test_definitions(sequence)

            tests = [t for t in test_definitions.TESTS if t not in test_definitions.SKIP]

            failed_steps = {}

            for dut_key, dut_value in duts.items():
                if dut_value:
                    dut_status[dut_key] = {
                        'step': None,
                        'status': 'idle',
                        'test_status': None,
                        'sn': dut_value['sn'],
                    }
                    failed_steps[dut_key] = {}


            results["start_time"] = datetime.datetime.now()


            for test_case in tests:

                for dut_name, dut_value in duts.items():
                    if not dut_value:
                        continue
                    dut_sn = dut_value['sn']
                    dut_status[dut_name]['step'] = test_case
                    dut_status[dut_name]['status'] = 'testing'

                    report_progress('testing', dut_status, sequence=sequence)

                    if dut_sn not in results:
                        results[dut_sn] = {}

                    results[dut_sn]["test_position"] = dut_name

                    start_time = datetime.datetime.now()

                    test_instance = getattr(test_definitions, test_case)()

                    test_instance.previous_results = results[dut_sn]

                    try:
                        test_instance.test(common_definitions.INSTRUMENTS, dut_sn)
                    except Exception as err:
                        results[dut_sn][test_case] = test_instance.result_handler(
                            None, error=str(err.__class__) + ": " + str(err)
                        )
                        # Clean error
                        if hasattr(test_instance, 'clean_error'):
                            test_instance.clean_error(common_definitions.INSTRUMENTS, dut_sn)
                    else:
                        if test_case in test_definitions.LIMITS:
                            results[dut_sn][test_case] = test_instance.result_handler(
                                test_definitions.LIMITS[test_case]
                            )
                        else:
                            # Todo: "no-limit test" not working. Tjeu: Create test single test without limit
                            results[dut_sn][test_case] = test_instance.result_handler(None)
                        # Clean
                        if hasattr(test_instance, 'clean'):
                            test_instance.clean(common_definitions.INSTRUMENTS, dut_sn)

                    if not all([r[1]["result"] for r in results[dut_sn][test_case].items()]):
                        overall_result = False
                        if 'failed_step' in failed_steps[dut_name]:
                            failed_steps[dut_name]['failed_step'] = (
                                failed_steps[dut_name]['failed_step'] + ', ' + test_case
                            )
                        else:
                            failed_steps[dut_name]['failed_step'] = test_case
                        if hasattr(test_instance, 'clean_fail'):
                            test_instance.clean_fail(common_definitions.INSTRUMENTS, dut_sn)

                    else:
                        if hasattr(test_instance, 'clean_pass'):
                            test_instance.clean_pass(common_definitions.INSTRUMENTS, dut_sn)

                    results[dut_sn][test_case]["end_time"] = datetime.datetime.now()
                    results[dut_sn][test_case]["start_time"] = start_time

                    results[dut_sn][test_case]["duration_s"] = (
                        results[dut_sn][test_case]["end_time"]
                        - results[dut_sn][test_case]["start_time"]
                    ).total_seconds()

                    last_dut_status[dut_name] = dut_status[dut_name]
                    dut_status[dut_name]['status'] = 'idle'
                    dut_status[dut_name]['step'] = None

                    report_progress('testing', dut_status, sequence=sequence)

            for dut_name, dut_value in duts.items():
                if not dut_value:
                    continue
                if 'failed_step' in failed_steps[dut_name]:
                    dut_status[dut_name]['test_status'] = 'fail'
                    dut_status[dut_name]['failed_step'] = failed_steps[dut_name]['failed_step']

                else:
                    dut_status[dut_name]['test_status'] = 'pass'

                last_dut_status[dut_name] = dut_status[dut_name]

            report_progress(
                'finalize', dut_status, overall_result=overall_result, sequence=sequence
            )
            common_definitions.finalize_test(overall_result, duts, common_definitions.INSTRUMENTS)

            results["end_time"] = datetime.datetime.now()

            results["duration_s"] = (results["end_time"] - results["start_time"]).total_seconds()

            results["Overall result"] = overall_result

        except exceptions.Error as e:
            # TODO: write error to report
            print(e)
            raise
        else:
            pass
        finally:
            pass

        report_progress("Create test report", sequence=sequence)
        if not test_control['report_off']:
            common_definitions.create_report(
                json.dumps(results, indent=4, default=str), results, duts
            )

        if test_control['single_run']:
            test_control['terminate'] = True

    report_progress("Shutdown")

    common_definitions.shutdown(common_definitions.INSTRUMENTS)

    report_progress("Shutdown")
