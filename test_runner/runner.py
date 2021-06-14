"""Runs the test cases"""
import datetime
import time
import json
import threading
import logging
from unittest.mock import MagicMock
from test_runner import progress_reporter
from test_runner import helpers
from test_runner import exceptions


def get_common_definitions():
    """Returns test definitions"""

    return helpers.import_by_name(
        'common',
        "No test definitions defined? Create definition template with --create argument.",
        logging.getLogger("common_definitions"),
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


def get_sn_from_ui(dut_sn_queue, logger):
    """Returns serial numbers from UI"""

    sequence_name = None
    common_definitions = get_common_definitions()
    duts_sn = {
        test_position.name: {'sn': None} for test_position in common_definitions.TEST_POSITIONS
    }
    logger.info(
        'Wait SNs from UI for test_positions: '
        + ", ".join([str(t) for t in common_definitions.TEST_POSITIONS])
    )

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
            logger.info("All DUT serial numbers received from UI")
            logger.info("Selected test %s", sequence_name)
            break

    return (duts_sn, sequence_name, {"name": "Not available"})


def run_test_runner(test_control, message_queue, progess_queue, dut_sn_queue, listener_args):
    """Starts the testing"""

    logger = logging.getLogger('test_runner')

    def send_message(message):
        if message:
            message_queue.put(message)

    common_definitions = get_common_definitions()

    progress = progress_reporter.ProgressReporter(test_control, progess_queue)

    progress.set_progress(general_state="Boot")

    if test_control['dry_run']:

        for instrument in common_definitions.INSTRUMENTS.keys():
            common_definitions.INSTRUMENTS[instrument] = MagicMock()
            progress.set_instrument_status(instrument, 'MagicMock')

    elif 'mock' in test_control:

        try:
            common_definitions.instrument_initialization(progress)
        except Exception as e:
            pass

        for instrument in common_definitions.INSTRUMENTS.keys():
            if instrument in test_control['mock']:
                common_definitions.INSTRUMENTS[instrument] = MagicMock()
                progress.set_instrument_status(instrument, 'MagicMock')
    else:
        # Initialize all instruments
        common_definitions.instrument_initialization(progress)

    db_handler = common_definitions.INSTRUMENTS[common_definitions.DB_HANDLER_NAME]

    listener_args['database'] = db_handler

    # Execute boot_up defined for the test sequence
    common_definitions.boot_up(common_definitions.INSTRUMENTS, logger)

    test_positions = {}
    fail_reason_history = ''
    fail_reason_count = 0
    pass_count = 0

    # Start the actual test loop
    while not test_control['terminate']:
        # Wait until you are allowed to run again i.e. pause
        test_control['run'].wait()
        logger.info("Start new test run")

        try:
            background_pre_tasks = {}
            background_post_tasks = {}

            progress.set_progress(
                general_state="Prepare", overall_result=None, test_positions=test_positions
            )

            common_definitions.handle_instrument_status(progress)

            if db_handler:
                db_handler.clean_db()
                progress.set_progress(statistics=db_handler.get_statistics())

            # Create TestPosition instances
            for position in common_definitions.TEST_POSITIONS:
                test_positions[position.name] = position

            # Clear test positions
            for position_name, position in test_positions.items():
                position.prepare_for_new_test_run()

                progress.set_progress(general_state="Prepare", test_positions=test_positions)

            # DUT sn may come from UI
            if test_control['get_sn_from_ui']:

                (dut_sn_values, sequence_name, operator_info) = get_sn_from_ui(
                    dut_sn_queue, logger
                )

            else:
                # Or from prepare_test function
                (
                    dut_sn_values,
                    sequence_name,
                    operator_info,
                ) = common_definitions.indentify_DUTs(common_definitions.INSTRUMENTS, logger)

            common_definitions.prepare_test(
                common_definitions.INSTRUMENTS, logger, dut_sn_values, sequence_name
            )
            # Create dut instances
            for test_position, dut_info in dut_sn_values.items():
                if dut_info is None:
                    test_positions[test_position].dut = None
                else:
                    test_positions[test_position].dut = common_definitions.parse_dut_info(
                        dut_info, test_position
                    )

            results = {"operator": operator_info, "tester": common_definitions.get_tester_info()}

            # Fetch test definitions i.e. import module
            test_definitions = helpers.get_test_definitions(sequence_name, logger)

            # Fetch test case pool too
            test_pool = helpers.get_test_pool_definitions(logger)

            # Remove skipped test_case_names from test list
            test_case_names = [t for t in test_definitions.TESTS if t not in test_definitions.SKIP]

            start_time_epoch = time.time()
            start_time = datetime.datetime.now()
            start_time_monotonic = time.monotonic()
            test_run_id = str(start_time_epoch).replace('.', '_')

            # Run all test cases
            for test_case_name in test_case_names:
                # Loop for testing

                is_pre_test = False
                if '_pre' in test_case_name:
                    is_pre_test = True

                test_case_name = test_case_name.replace('_pre', '').replace('_pre', '')

                # Run test cases for each DUT in test position
                for test_position_name, test_position_instance in test_positions.items():

                    # Set sn to be none, if you don't want to run any test_case_names for the test position
                    # but want to keep showing the position on the UI
                    if not test_position_instance.dut or test_position_instance.stop_testing:
                        continue

                    # Fill DUT data
                    test_position_instance.step = test_case_name
                    test_position_instance.status = 'testing'

                    progress.set_progress(
                        general_state='testing',
                        test_positions=test_positions,
                        sequence_name=sequence_name,
                    )

                    def new_test_instance(the_case, the_position_instance):
                        if hasattr(test_definitions, the_case):
                            test_instance = getattr(test_definitions, the_case)(
                                test_definitions.LIMITS,
                                progress,
                                the_position_instance.dut,
                                test_definitions.PARAMETERS,
                                db_handler,
                                common_definitions,
                            )
                        elif hasattr(test_pool, the_case):
                            test_instance = getattr(test_pool, the_case)(
                                test_definitions.LIMITS,
                                progress,
                                the_position_instance.dut,
                                test_definitions.PARAMETERS,
                                db_handler,
                                common_definitions,
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
                    test_instance.test_run_id = test_run_id
                    try:
                        if is_pre_test:
                            # Start pre task and store it to dictionary
                            if test_case_name not in background_pre_tasks:
                                background_pre_tasks[test_case_name] = {}

                            background_pre_tasks[test_case_name][
                                test_position_name
                            ] = threading.Thread(target=test_instance.run_pre_test)
                            background_pre_tasks[test_case_name][test_position_name].start()
                        else:
                            # Wait for pre task
                            if (
                                test_case_name in background_pre_tasks
                                and test_position_name in background_pre_tasks[test_case_name]
                            ):
                                background_pre_tasks[test_case_name][test_position_name].join()
                            else:
                                # Or if pre task is not run, run it now
                                test_instance.run_pre_test()

                            test_position_instance.test_status = "Testing"
                            progress.set_progress(
                                general_state='testing',
                                test_position=test_positions,
                                sequence_name=sequence_name,
                            )
                            # Run the actual test case
                            test_instance.run_test()

                            progress.set_progress(
                                general_state='testing',
                                test_positions=test_positions,
                                sequence_name=sequence_name,
                            )
                            test_position_instance.test_status = "Idle"

                            # Start post task and store it to dictionary
                            if test_case_name not in background_post_tasks:
                                background_post_tasks[test_case_name] = {}

                            background_post_tasks[test_case_name][
                                test_position_name
                            ] = threading.Thread(target=test_instance.run_post_test)
                            background_post_tasks[test_case_name][test_position_name].start()

                    except Exception as err:

                        trace = []
                        trace_back = err.__traceback__
                        while trace_back is not None:
                            trace.append(
                                {
                                    "filename": trace_back.tb_frame.f_code.co_filename,
                                    "name": trace_back.tb_frame.f_code.co_name,
                                    "line": trace_back.tb_lineno,
                                }
                            )
                            trace_back = trace_back.tb_next

                        err_dict = {
                            'type': type(err).__name__,
                            'message': str(err),
                            'trace': trace,
                        }

                        test_instance.handle_error(error=err_dict)

                    else:
                        # No error and no active tests
                        test_position_instance.status = 'idle'
                        test_position_instance.step = None

                        progress.set_progress(
                            general_state='testing',
                            test_positions=test_positions,
                            sequence_name=sequence_name,
                        )

            for test_position_name, test_position_instance in test_positions.items():

                dut = test_position_instance.dut

                results[dut.serial_number] = test_position_instance.dut.test_cases

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

            progress.set_progress(
                general_state='finalize',
                test_positions=test_positions,
                overall_result=dut.pass_fail_result,
                sequence_name=sequence_name,
            )
            common_definitions.finalize_test(
                dut.pass_fail_result, test_positions, common_definitions.INSTRUMENTS, logger
            )

            results["start_time"] = start_time
            results["start_time_epoch"] = start_time_epoch
            results["end_time"] = datetime.datetime.now()
            results["test_run_id"] = test_run_id

            results["duration_s"] = round(time.monotonic() - start_time_monotonic, 2)

        except exceptions.IrisError as e:
            # TODO: write error to report
            logger.exception("Error on testsequence")
            raise
        else:
            pass
        finally:
            pass
        progress.set_progress(
            general_state="Create test report",
            test_positions=test_positions,
            overall_result=dut.pass_fail_result,
            sequence_name=sequence_name,
        )
        if not test_control['report_off']:
            common_definitions.create_report(
                json.dumps(results, indent=4, default=str),
                results,
                test_positions,
                test_definitions.PARAMETERS,
                db_handler,
                common_definitions,
                progress,
            )

        if test_control['single_run']:
            test_control['terminate'] = True

    progress.set_progress(general_state="Shutdown")

    common_definitions.shutdown(common_definitions.INSTRUMENTS)
