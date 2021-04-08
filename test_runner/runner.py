"""Runs the tests"""
import datetime
import json
import threading
from test_runner import helpers
from test_runner import exceptions


def get_common_definitions():
    """Returns test definitions"""

    return helpers.import_by_name(
        'common', "No test definitions defined? Create definition template with --create argument."
    )


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

    # Initialize all instruments
    common_definitions.instrument_initialization()

    # Execute boot_up defined for the test sequence
    common_definitions.boot_up()

    last_dut_status = {}
    dut_status = {}
    failed_steps = {}
    fail_reason_history = ''
    fail_reason_count = 0
    pass_count = 0

    # Start the actual test loop
    while not test_control['terminate']:
        # Wait until you are allowed to run again i.e. pause
        test_control['run'].wait()
        try:
            background_pre_tasks = {}
            background_post_tasks = {}

            report_progress("Prepare", dut_status)

            # DUT sn may come from UI
            if test_control['get_sn_from_ui']:

                for dut in common_definitions.DUTS:
                    dut_status[dut] = {'step': None, 'status': 'wait', 'sn': None}
                    if dut in failed_steps and 'failed_step' in failed_steps[dut]:
                        dut_status[dut]['failed_step'] = failed_steps[dut]['failed_step']
                    if dut in last_dut_status:
                        dut_status[dut]['test_status'] = last_dut_status[dut]['test_status']
                    else:
                        dut_status[dut]['test_status'] = 'idle'

                report_progress("Prepare", duts=dut_status)

                duts, sequence = get_sn_from_ui(dut_sn_queue)
                common_definitions.prepare_test(common_definitions.INSTRUMENTS)
            else:
                # Or from prepare_test function
                duts, sequence = common_definitions.prepare_test(common_definitions.INSTRUMENTS)

            results = {}
            overall_result = True

            # Fetch test definitions i.e. import module
            test_definitions = helpers.get_test_definitions(sequence)

            # Fetch test case pool too
            test_pool = helpers.get_test_pool_definitions()

            # Remove skipped tests from test list
            tests = [t for t in test_definitions.TESTS if t not in test_definitions.SKIP]

            # Here we will store failed steps
            failed_steps = {}

            # Create DUT status dictionary
            # If this is not first round, clear almost all parameters,
            # but keep showing failed steps on test position
            for test_position, dut_sn in duts.items():
                if dut_sn:
                    dut_status[test_position] = {
                        'step': None,
                        'status': 'idle',
                        'test_status': None,
                        'sn': dut_sn['sn'],
                    }
                    failed_steps[test_position] = {}
                elif test_position not in last_dut_status:
                    dut_status[test_position] = {
                        'step': None,
                        'status': 'idle',
                        'test_status': None,
                    }

            results["start_time"] = datetime.datetime.now()

            # Store results so that test cases can see results of the other cases
            result_history = {}

            test_instances = {}

            # Run all test cases
            for test_case in tests:
                # Loop for testing

                # Run test cases for each DUT in DUT position
                for test_position, dut_sn_dict in duts.items():

                    # Set sn_dict to be none, if you don't want to run any tests for the test position
                    # but want to keep showing the position on the UI
                    if not dut_sn_dict:
                        continue

                    # Extract SN from sn dict (sn dict may contain other data that is used by test case)
                    dut_sn = dut_sn_dict['sn']

                    # Fill DUT data
                    dut_status[test_position]['step'] = test_case
                    dut_status[test_position]['status'] = 'testing'

                    report_progress('testing', dut_status, sequence=sequence)

                    # Create results data structure
                    if dut_sn not in results:
                        results[dut_sn] = {}
                        result_history[dut_sn] = {}

                    results[dut_sn]["test_position"] = test_position

                    start_time = datetime.datetime.now()

                    test_case_name = test_case.replace('_pre', '').replace('_pre', '')

                    # Create test case instance
                    test_instance = helpers.get_test_instance(
                        test_definitions, test_case_name, test_pool
                    )

                    # And store it for later use
                    test_instances[test_case_name] = test_instance

                    if dut_sn in result_history:

                        test_instance.previous_results = result_history[dut_sn]

                    try:
                        if '_pre' in test_case:
                            # Start pre task and store it to dictionary

                            if test_case_name not in background_pre_tasks:
                                background_pre_tasks[test_case_name] = {}

                            background_pre_tasks[test_case_name][test_position] = threading.Thread(
                                target=test_instance.pre_test,
                                args=(
                                    common_definitions.INSTRUMENTS,
                                    dut_sn,
                                    test_definitions.PARAMETERS,
                                ),
                            )
                            background_pre_tasks[test_case_name][test_position].start()
                        else:
                            # Wait for pre task
                            if test_case in background_pre_tasks:
                                background_pre_tasks[test_case][test_position].join()
                            else:
                                # Or if pre task is not run, run it now
                                test_instance.pre_test(
                                    common_definitions.INSTRUMENTS,
                                    dut_sn,
                                    test_definitions.PARAMETERS,
                                )

                            # Run the actual test case
                            test_instance.test(
                                common_definitions.INSTRUMENTS,
                                dut_sn,
                                test_definitions.PARAMETERS,
                            )

                            # Start post task and store it to dictionary
                            if test_case not in background_post_tasks:
                                background_post_tasks[test_case] = {}

                            background_post_tasks[test_case][test_position] = threading.Thread(
                                target=test_instance.post_test,
                                args=(
                                    common_definitions.INSTRUMENTS,
                                    dut_sn,
                                    test_definitions.PARAMETERS,
                                ),
                            )
                            background_post_tasks[test_case][test_position].start()

                    except Exception as err:
                        results[dut_sn][test_case] = test_instance.result_handler(
                            None, error=str(err.__class__) + ": " + str(err)
                        )
                        # Call clean error method on test case on error
                        if hasattr(test_instance, 'clean_error'):
                            test_instance.clean_error(common_definitions.INSTRUMENTS, dut_sn)

                    # Evaluate test results first time (if no error)
                    # We will evaluate them again after post tasks are done
                    # Measurement can be added or changed at any time so
                    # the actual result may change still on post task.
                    else:
                        if test_case in test_definitions.LIMITS:
                            results[dut_sn][test_case] = test_instance.result_handler(
                                test_definitions.LIMITS[test_case]
                            )
                        else:
                            # Todo: "no-limit test" not working. Tjeu: Create test single test without limit
                            results[dut_sn][test_case] = test_instance.result_handler(None)

                        # Call clean method on test case if it exists
                        if hasattr(test_instance, 'clean'):
                            test_instance.clean(common_definitions.INSTRUMENTS, dut_sn)

                        result_history[dut_sn][test_case] = test_instance.results

                        # Set overall result to false if boolean false in any of results
                        if all(
                            [
                                r[1]["result"]
                                for r in results[dut_sn][test_case].items()
                                if isinstance(r[1]["result"], bool)
                            ]
                        ):
                            # If test case passed, call clean_pass method
                            if hasattr(test_instance, 'clean_pass'):
                                test_instance.clean_pass(common_definitions.INSTRUMENTS, dut_sn)
                        else:
                            overall_result = False

                            # Store failed step information for showing it on UI
                            if 'failed_step' in failed_steps[test_position]:
                                failed_steps[test_position]['failed_step'] = (
                                    failed_steps[test_position]['failed_step'] + ', ' + test_case
                                )
                            else:
                                failed_steps[test_position]['failed_step'] = test_case

                            # If test case failed, call clean_fail method
                            if hasattr(test_instance, 'clean_fail'):
                                test_instance.clean_fail(common_definitions.INSTRUMENTS, dut_sn)

                        results[dut_sn][test_case]["end_time"] = datetime.datetime.now()
                        results[dut_sn][test_case]["start_time"] = start_time

                        results[dut_sn][test_case]["duration_s"] = (
                            results[dut_sn][test_case]["end_time"]
                            - results[dut_sn][test_case]["start_time"]
                        ).total_seconds()

                        last_dut_status[test_position] = dut_status[test_position]
                        dut_status[test_position]['status'] = 'idle'
                        dut_status[test_position]['step'] = None

                        report_progress('testing', dut_status, sequence=sequence)

            for test_position, dut_value in duts.items():
                if not dut_value:
                    continue
                # Inform UI about the final results
                if 'failed_step' in failed_steps[test_position]:
                    dut_status[test_position]['test_status'] = 'fail'
                    dut_status[test_position]['failed_step'] = failed_steps[test_position][
                        'failed_step'
                    ]
                    send_message(
                        f"{dut_value['sn']}: FAILED: {dut_status[test_position]['failed_step']}"
                    )
                    if fail_reason_history == failed_steps[test_position]['failed_step']:
                        fail_reason_count = fail_reason_count + 1
                    else:
                        fail_reason_count = 0
                        fail_reason_history = failed_steps[test_position]['failed_step']
                    pass_count = 0

                else:
                    dut_status[test_position]['test_status'] = 'pass'
                    send_message(f"{dut_value['sn']}: PASSED")
                    pass_count = pass_count + 1

                last_dut_status[test_position] = dut_status[test_position]

            if fail_reason_count > 4 and pass_count < 5:
                send_message(f"WARNING: 5 or more consecutive fails on {fail_reason_history}")

            report_progress(
                'finalize', dut_status, overall_result=overall_result, sequence=sequence
            )
            common_definitions.finalize_test(overall_result, duts, common_definitions.INSTRUMENTS)

            results["end_time"] = datetime.datetime.now()

            results["duration_s"] = (results["end_time"] - results["start_time"]).total_seconds()

            results["overall_result"] = overall_result

        except exceptions.IrisError as e:
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
                json.dumps(results, indent=4, default=str),
                results,
                duts,
                test_definitions.PARAMETERS,
            )

        if test_control['single_run']:
            test_control['terminate'] = True

    report_progress("Shutdown")

    common_definitions.shutdown(common_definitions.INSTRUMENTS)

    report_progress("Shutdown")
