"""Runs the test cases"""
import datetime
import time
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
        'dry_run': False,
    }


def get_sn_from_ui(dut_sn_queue):
    """Returns serial numbers from UI"""

    sequence_name = None
    common_definitions = get_common_definitions()
    duts_sn = {
        test_position.name: {'sn': None} for test_position in common_definitions.TEST_POSITIONS
    }
    print('Wait SNs from UI for test_positions: ' + str(common_definitions.TEST_POSITIONS))
    while True:
        msg = dut_sn_queue.get()

        try:
            msg = json.loads(msg)
            for dut in msg:
                if dut in duts_sn:
                    duts_sn[dut]['sn'] = msg[dut]
            if 'sequence' in msg:
                sequence_name = msg['sequence']

        except (AttributeError, json.decoder.JSONDecodeError):
            pass

        # Loop until all test_positions have received a serial number
        for dut in duts_sn:
            if not duts_sn[dut]['sn']:
                break
        else:
            print("All DUT serial numbers received from UI")
            print("Selected test sequence_name", sequence_name)
            break

    return (duts_sn, sequence_name)


def run_test_runner(test_control, message_queue, progess_queue, dut_sn_queue):
    """Starts the testing"""

    def send_message(message):
        if message:
            message_queue.put(message)

    def report_progress(
        general_step, test_positions=None, overall_result=None, sequence_name=None
    ):
        if test_positions:
            positions_dict = {}
            for position_name, position_value in test_positions.items():
                positions_dict[position_name] = {
                    'step': position_value.step,
                    'status': position_value.status,
                    'sn': None if position_value.dut is None else position_value.dut.serial_number,
                    'test_status': str(position_value.test_status),
                }

            test_positions = positions_dict

        progress_json = {
            "general_state": general_step,
            "duts": test_positions,
            "sequence_name": sequence_name,
            "get_sn_from_ui": test_control['get_sn_from_ui'],
            "test_sequences": test_control['test_sequences'],
        }

        if overall_result:
            progress_json['overall_result'] = overall_result

        test_control['progress'] = progress_json
        progess_queue.put(json.dumps(progress_json, default=str))

    common_definitions = get_common_definitions()

    report_progress("Boot")

    if test_control['dry_run']:
        import mock
        for instument in common_definitions.INSTRUMENTS.keys():
            common_definitions.INSTRUMENTS[instument] = mock.Mock()
    else:
        # Initialize all instruments
        common_definitions.instrument_initialization()

    # Execute boot_up defined for the test sequence
    common_definitions.boot_up()

    last_dut_status = {}
    test_positions = {}
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

            report_progress("Prepare", test_positions)

            # Create TestPosition instances
            for position in common_definitions.TEST_POSITIONS:
                test_positions[position.name] = position

            # Clear test positions
            for position_name, position in test_positions.items():
                position.prepare_for_new_test_run()

                report_progress("Prepare", test_positions=test_positions)

            # DUT sn may come from UI
            if test_control['get_sn_from_ui']:

                dut_sn_values, sequence_name = get_sn_from_ui(dut_sn_queue)

            else:
                # Or from prepare_test function
                dut_sn_values, sequence_name = common_definitions.prepare_test(
                    common_definitions.INSTRUMENTS
                )

            # Create dut instances
            for test_position, dut_info in dut_sn_values.items():
                if dut_info is None:
                    test_positions[test_position].dut = None
                else:
                    test_positions[test_position].dut = common_definitions.parse_dut_info(
                        dut_info, test_position
                    )

            common_definitions.prepare_test(common_definitions.INSTRUMENTS)

            results = {}

            # Fetch test definitions i.e. import module
            test_definitions = helpers.get_test_definitions(sequence_name)

            # Fetch test case pool too
            test_pool = helpers.get_test_pool_definitions()

            # Remove skipped test_case_names from test list
            test_case_names = [t for t in test_definitions.TESTS if t not in test_definitions.SKIP]

            start_time = datetime.datetime.now()
            start_time_monotonic = time.monotonic()

            # Run all test cases
            for test_case_name in test_case_names:
                # Loop for testing

                # Run test cases for each DUT in test position
                for test_position_name, test_position_instance in test_positions.items():

                    # Set sn to be none, if you don't want to run any test_case_names for the test position
                    # but want to keep showing the position on the UI
                    if not test_position_instance.dut or test_position_instance.stop_testing:
                        continue

                    # Fill DUT data
                    test_position_instance.step = test_case_name
                    test_position_instance.status = 'testing'

                    report_progress('testing', test_positions, sequence_name=sequence_name)

                    test_case_name = test_case_name.replace('_pre', '').replace('_pre', '')

                    def new_test_instance(the_case, the_position_instance):
                        if hasattr(test_definitions, the_case):
                            test_instance = getattr(test_definitions, the_case)(
                                test_definitions.LIMITS,
                                report_progress,
                                the_position_instance.dut,
                                common_definitions.INSTRUMENTS,
                                test_definitions.PARAMETERS,
                                common_definitions.FLOW_CONTROL
                            )
                        elif hasattr(test_pool, the_case):
                            test_instance = getattr(test_pool, the_case)(
                                test_definitions.LIMITS,
                                report_progress,
                                the_position_instance.dut,
                                common_definitions.INSTRUMENTS,
                                test_definitions.PARAMETERS,
                                common_definitions.FLOW_CONTROL
                            )
                        else:
                            raise exceptions.TestCaseNotFound(
                                "Cannot find specified test case: " + the_case
                            )
                        return test_instance

                    # Create test case instance
                    if test_case_name not in test_position_instance.test_case_instances:
                        test_position_instance.test_case_instances[
                            test_case_name
                        ] = new_test_instance(test_case_name, test_position_instance)

                    test_instance = test_position_instance.test_case_instances[test_case_name]
                    test_instance.test_position = test_position_instance

                    try:
                        if '_pre' in test_case_name:
                            # Start pre task and store it to dictionary

                            if test_case_name not in background_pre_tasks:
                                background_pre_tasks[test_case_name] = {}

                            background_pre_tasks[test_case_name][
                                test_position_name
                            ] = threading.Thread(target=test_instance.run_pre_test)
                            background_pre_tasks[test_case_name][test_position_name].start()
                        else:
                            # Wait for pre task
                            if test_case_name in background_pre_tasks:
                                background_pre_tasks[test_case_name][test_position_name].join()
                            else:
                                # Or if pre task is not run, run it now
                                test_instance.run_pre_test()

                            test_position_instance.test_status = "Testing"
                            report_progress('testing', test_positions, sequence_name=sequence_name)
                            # Run the actual test case
                            test_instance.run_test()

                            report_progress('testing', test_positions, sequence_name=sequence_name)
                            test_position_instance.test_status = "Idle"

                            # Start post task and store it to dictionary
                            if test_case_name not in background_post_tasks:
                                background_post_tasks[test_case_name] = {}

                            background_post_tasks[test_case_name][
                                test_position_name
                            ] = threading.Thread(target=test_instance.run_post_test)
                            background_post_tasks[test_case_name][test_position_name].start()

                    except Exception as err:
                        test_instance.result_handler(error=str(err.__class__) + ": " + str(err))

                    else:
                        # No error and no active tests
                        test_position_instance.status = 'idle'
                        test_position_instance.step = None

                        report_progress('testing', test_positions, sequence_name=sequence_name)

            for test_position_name, test_position_instance in test_positions.items():

                dut = test_position_instance.dut

                results[dut.serial_number] = test_position_instance.dut.results

                if not test_position_instance.dut:
                    continue

                if dut.pass_fail_result:
                    send_message(f"{dut.serial_number}: PASSED")
                    test_position_instance.test_status = 'pass'
                    pass_count = pass_count + 1
                else:
                    send_message(f"{dut.serial_number}: FAILED: {', '.join(dut.failed_steps)}")
                    test_position_instance.test_status = 'fail'

                    if fail_reason_history == dut.failed_steps:
                        fail_reason_count = fail_reason_count + 1
                    else:
                        fail_reason_count = 0
                        fail_reason_history = dut.failed_steps
                    pass_count = 0

            if fail_reason_count > 4 and pass_count < 5:
                send_message(f"WARNING: 5 or more consecutive fails on {fail_reason_history}")

            report_progress(
                'finalize',
                test_positions,
                overall_result=dut.pass_fail_result,
                sequence_name=sequence_name,
            )
            common_definitions.finalize_test(
                dut.pass_fail_result, test_positions, common_definitions.INSTRUMENTS
            )

            results["start_time"] = datetime.datetime.now()
            results["end_time"] = datetime.datetime.now()

            results["duration_s"] = time.monotonic() - start_time_monotonic

            results["overall_result"] = dut.pass_fail_result

        except exceptions.IrisError as e:
            # TODO: write error to report
            print(e)
            raise
        else:
            pass
        finally:
            pass
        report_progress(
            "Create test report",
            test_positions,
            overall_result=dut.pass_fail_result,
            sequence_name=sequence_name,
        )
        if not test_control['report_off']:
            common_definitions.create_report(
                json.dumps(results, indent=4, default=str),
                results,
                test_positions,
                test_definitions.PARAMETERS,
            )

        if test_control['single_run']:
            test_control['terminate'] = True

    report_progress("Shutdown")

    common_definitions.shutdown(common_definitions.INSTRUMENTS)

    report_progress("Shutdown")
