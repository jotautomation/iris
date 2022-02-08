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
import gaiaclient


def get_common_definitions():
    """Returns test definitions"""

    return helpers.import_by_name(
        'common',
        "No test definitions defined? Create definition template with --create argument.",
        logging.getLogger("common_definitions"),
    )


def get_test_cases(logger):

    test_cases = {}
    for sequence in get_common_definitions().TEST_SEQUENCES:
        test_definitions = helpers.get_test_definitions(sequence, logger)
        test_cases[sequence] = [
            {'name': t}
            for t in test_definitions.TESTS
            if t not in test_definitions.SKIP and '_pre' not in t and '_post' not in t
        ]
    return test_cases


def get_test_control(logger):
    """Returns default test control dictionary"""
    return {
        'single_run': False,
        'step': False,
        'skip': None,
        'loop_all': False,
        'loop': None,
        'retest_on_fail': 0,
        'terminate': False,
        'abort': False,
        'report_off': False,
        'run': threading.Event(),
        'get_sn_from_ui': get_common_definitions().SN_FROM_UI,
        'get_sn_externally': get_common_definitions().SN_EXTERNALLY,
        'test_sequences': get_common_definitions().TEST_SEQUENCES,
        'running_mode': get_common_definitions().RUNNING_MODES,
        'gage_rr': get_common_definitions().GAGE_RR,
        'dry_run': False,
        'start_time_monotonic': 0,
        'stop_time_monotonic': 0,
        'test_time': 0,
        'test_cases': get_test_cases(logger),
    }


def get_sn_from_ui(dut_sn_queue, logger):
    """Returns serial numbers from UI"""

    sequence_name = None
    test_cases = None
    operator = "Not available"
    common_definitions = get_common_definitions()
    external_selection = False
    running_mode = common_definitions.RUNNING_MODES[0]
    gage_rr = common_definitions.GAGE_RR
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
                if msg['sequence'] in common_definitions.TEST_SEQUENCES:
                    sequence_name = msg['sequence']
            if 'running_mode' in msg:
                if msg['running_mode'] in common_definitions.RUNNING_MODES:
                    running_mode = msg['running_mode']
            if 'external_selection' in msg and msg['external_selection']:
                external_selection = bool(msg['external_selection'])
            if 'testCases' in msg and msg['testCases']:
                test_cases = msg['testCases']
            if 'gage_rr' in msg and msg['gage_rr']:
                gage_rr = msg['gage_rr']
            if 'operator' in msg and msg['operator']:
                operator = msg['operator']

        except (AttributeError, json.decoder.JSONDecodeError):
            pass

        sequence_duts = None
        if sequence_name is not None:
            test_definitions = helpers.get_test_definitions(sequence_name, logger)
            if hasattr(test_definitions, 'DUTS'):
                # TODO: Might import wrong sequence DUTS-attr
                if isinstance(test_definitions.DUTS, int):
                    sequence_duts = test_definitions.DUTS

        # Loop until all test_positions have received a serial number
        received_duts = 0
        if sequence_duts is not None:
            received_duts = len([duts_sn[dut]['sn'] for dut in duts_sn if duts_sn[dut]['sn']])

        for dut in duts_sn:
            if sequence_duts:
                if received_duts < sequence_duts:
                    break
            else:
                if not duts_sn[dut]['sn']:
                    break
        else:
            logger.info("All DUT serial numbers received from UI")
            if sequence_name not in ['None', None]:
                logger.info("Selected test %s", sequence_name)
            else:
                logger.info("No selected sequence from UI.")
            break

    return (
        duts_sn,
        sequence_name,
        {"name": operator},
        test_cases,
        external_selection,
        running_mode,
        gage_rr
    )


def get_sn_externally(dut_sn_queue, logger):
    """Returns serial numbers from external source (HTTP POST)"""

    common_definitions = get_common_definitions()

    gaia = None
    if hasattr(common_definitions, 'SN_FROM_GAIA'):
        if common_definitions.SN_FROM_GAIA:
            for instrument in common_definitions.INSTRUMENTS.values():
                if isinstance(instrument, gaiaclient.Client):
                    gaia = instrument
                    break

    def _get_sn_from_gaia():
        while True:
            if len(gaia.duts) > 0:
                logger.info("Gaia client has DUTs %s", gaia.duts)
                duts_from_gaia = {"sequence": None}
                for idx, position in enumerate(gaia.duts):
                    for seq in common_definitions.TEST_SEQUENCES:
                        if seq in position.get("type"):
                            duts_from_gaia["sequence"] = seq
                            break
                    duts_from_gaia[str(common_definitions.TEST_POSITIONS[idx])] = position.get("SN")
                logger.info("Gaia client DUTs modified for Iris: %s", duts_from_gaia)
                dut_sn_queue.put(json.dumps(duts_from_gaia, default=str))
                break
            time.sleep(1)

    while True:
        sequence_name = None
        duts_sn = {
            test_position.name: {'sn': None} for test_position in common_definitions.TEST_POSITIONS
        }
        dut_count = 0
        duts = len(common_definitions.TEST_POSITIONS)
        logger.info(
            'Wait SNs from external source for test_positions: '
            + ", ".join([str(t) for t in common_definitions.TEST_POSITIONS])
        )

        if gaia:
            _get_sn_from_gaia()

        msg = dut_sn_queue.get()
        try:
            msg = json.loads(msg)

            for dut in msg:
                if dut in duts_sn:
                    logger.info("Received DUT pos. %s SN is %s", dut, msg[dut])
                    duts_sn[dut]['sn'] = msg[dut]
                    dut_count += 1
            if 'sequence' in msg:
                if msg['sequence'] in common_definitions.TEST_SEQUENCES:
                    sequence_name = msg['sequence']
        except (AttributeError, json.decoder.JSONDecodeError):
            pass

        test_definitions = helpers.get_test_definitions(sequence_name, logger)
        if hasattr(test_definitions, 'DUTS'):
            # TODO: Might import wrong sequence DUTS-attr
            if isinstance(test_definitions.DUTS, int):
                duts = test_definitions.DUTS

        sns = [duts_sn[dut]['sn'] for dut in duts_sn.keys() if duts_sn[dut]['sn']]
        unique_sns = set(sns)

        if len(sns) == 0:
            logger.error("At least one SN must be defined")
        elif sequence_name is None or sequence_name == "":
            logger.error("Sequence name is not defined")
        elif duts != dut_count:
            logger.error("DUT count mismatch. Excepted count %s, received count %s",
                duts,
                dut_count
            )
        elif len(sns) != len(unique_sns):
            logger.error("All given DUTs must have unique SN")
        else:
            logger.info("Received DUT SNs externally for sequence %s", sequence_name)
            break

    return (
        duts_sn,
        sequence_name,
        {"name": "external"}
    )

def run_test_runner(test_control, message_queue, progess_queue, dut_sn_queue, listener_args):
    """Starts the testing"""

    logger = logging.getLogger('test_runner')

    def send_message(message):
        if message:
            message_queue.put(message)

    common_definitions = get_common_definitions()

    progress = progress_reporter.ProgressReporter(test_control, progess_queue)

    progress.set_progress(general_state="Boot")

    for instrument in common_definitions.INSTRUMENTS.keys():
        progress.set_instrument_status(instrument, 'Not initialized')

    if test_control['dry_run']:

        for instrument in common_definitions.INSTRUMENTS.keys():
            common_definitions.INSTRUMENTS[instrument] = MagicMock()
            progress.set_instrument_status(instrument, 'MagicMock')

    elif 'mock' in test_control:

        for instrument in common_definitions.INSTRUMENTS.keys():
            if instrument in test_control['mock']:
                common_definitions.INSTRUMENTS[instrument] = MagicMock()
                progress.set_instrument_status(instrument, 'MagicMock')

    elif 'inverse_mock' in test_control:

        for instrument in common_definitions.INSTRUMENTS.keys():
            if instrument not in test_control['inverse_mock']:
                common_definitions.INSTRUMENTS[instrument] = MagicMock()
                progress.set_instrument_status(instrument, 'MagicMock')

    logger.info("Initializing instruments")

    # Initialize all instruments
    common_definitions.handle_instrument_status(progress, logger)

    logger.info("All instruments initialized")

    db_handler = common_definitions.INSTRUMENTS[common_definitions.DB_HANDLER_NAME]

    listener_args['database'] = db_handler

    # Execute boot_up defined for the test sequence
    common_definitions.boot_up(common_definitions.INSTRUMENTS, logger)

    # Add possibility to controlling test_control
    common_definitions.set_events(test_control, common_definitions.INSTRUMENTS)

    test_positions = {}
    fail_reason_history = ''
    fail_reason_count = 0
    pass_count = 0

    for position in common_definitions.TEST_POSITIONS:
        test_positions[position.name] = position

    gage_progress = {
        "operator": 0,
        "dut": 0,
        "trial": 0,
        "completed": False
    }

    # Start the actual test loop
    while not test_control['terminate']:
        # Wait until you are allowed to run again i.e. pause
        test_control['run'].wait()
        logger.info("Start new test run")

        try:
            test_control['abort'] = False

            logger.info("Checking status of instruments")

            progress.set_progress(
                general_state="Checking status of instruments",
                overall_result=None,
                test_positions=test_positions,
            )

            logger.info("All instruments OK")

            common_definitions.handle_instrument_status(progress, logger)

            if db_handler:
                db_handler.clean_db()
                if isinstance(db_handler, MagicMock):
                    progress.set_progress(statistics={'statistics': 'mocked'})
                else:
                    progress.set_progress(statistics=db_handler.get_statistics())

            # Clear test positions
            for position_name, position in test_positions.items():
                position.prepare_for_new_test_run()

                progress.set_progress(general_state="Prepare", test_positions=test_positions)

            test_cases_override = None

            running_mode = common_definitions.RUNNING_MODES[0]
            if common_definitions.LOOP_EXECUTION is True:
                test_control['test_time'] = common_definitions.LOOP_TIME_IN_SECONDS

            # DUT sn may come from UI
            if test_control['get_sn_from_ui']:

                (
                    dut_sn_values,
                    sequence_name,
                    operator_info,
                    test_cases_override,
                    external_selection,
                    running_mode,
                    gage_rr
                ) = get_sn_from_ui(dut_sn_queue, logger)

                sequence_name_from_identify = common_definitions.identify_DUTs(
                    dut_sn_values, common_definitions.INSTRUMENTS, logger
                )

                # If sequence was not selected, get it from identify_DUTs
                if sequence_name is None or external_selection:
                    sequence_name = sequence_name_from_identify
                    if not isinstance(sequence_name, str):
                        sequence_name = sequence_name[1]
                    logger.info("Selected sequence %s with identify.", sequence_name)
                    progress.set_progress(
                        sequence_name=sequence_name,
                    )

                if (test_cases_override is not None and
                    sequence_name in test_cases_override and
                    test_cases_override[sequence_name]
                ):
                    test_cases_override = [t['name'] for t in test_cases_override[sequence_name]]
                else:
                    logger.info("No skipped test cases.")
                    test_cases_override = None

            elif test_control['get_sn_externally']:
                (
                    dut_sn_values,
                    sequence_name,
                    operator_info
                ) = get_sn_externally(dut_sn_queue, logger)

            else:
                # Or from identify_DUTs function
                (dut_sn_values, sequence_name, operator_info,) = common_definitions.identify_DUTs(
                    None, common_definitions.INSTRUMENTS, logger
                )

            common_definitions.prepare_test(
                common_definitions.INSTRUMENTS, logger, dut_sn_values, sequence_name
            )
            # Create dut instances
            for test_position, dut_info in dut_sn_values.items():
                if dut_info is None:
                    test_positions[test_position].dut = None
                elif "sn" in dut_info and (dut_info["sn"] is None or dut_info["sn"] == "null"):
                    test_positions[test_position].dut = None
                else:
                    test_positions[test_position].dut = common_definitions.parse_dut_info(
                        dut_info, test_position
                    )

            results = {
                "sequence": sequence_name,
                "operator": operator_info,
                "tester": common_definitions.get_tester_info()
            }

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
            test_control['start_time_monotonic'] = start_time_monotonic
            test_control['stop_time_monotonic'] = 0

            logger.info("Running mode: %s", running_mode)
            if 'gage' in running_mode.lower():
                logger.info("Gage R&R settings: %s", gage_rr)
                logger.info("Gage R&R progress: Operator %s, Dut %s, Trial %s.",
                    (gage_progress['operator'] + 1),
                    (gage_progress['dut'] + 1),
                    (gage_progress['trial'] + 1)
                )
                test_control['gage_rr'] = gage_rr

            def parallel_run(test_position_name, test_position_instance, sync_test_cases=False):
                background_pre_tasks = {}
                background_post_tasks = []

                # Run all test cases
                for test_case_name in test_case_names:
                    # Loop for testing

                    if test_control['abort']:

                        send_message("Test aborted")
                        logger.warning("Test aborted")
                        break

                    if test_cases_override and test_case_name not in test_cases_override:
                        continue

                    is_pre_test = False
                    if '_pre' in test_case_name:
                        is_pre_test = True

                    test_case_name = test_case_name.replace('_pre', '').replace('_pre', '')

                    # Set sn to be none, if you don't want to run any test_case_names
                    # for the test position but want to keep showing the position on the UI
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
                    if sync_test_cases and all_pos_mid_test_cases_completed is not None:
                        test_instance.thread_barrier = all_pos_mid_test_cases_completed
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

                            # Synchronize parallel per test case testing
                            if sync_test_cases and all_pos_test_cases_completed is not None:
                                if all_pos_test_cases_completed.parties > 1:
                                    logger.info(
                                        "Test case completed thread for test position "
                                        "%s is waiting for other %s threads.",
                                        test_position_instance.name,
                                        (
                                            all_pos_test_cases_completed.parties -
                                            all_pos_test_cases_completed.n_waiting
                                            - 1
                                        )
                                    )
                                i_thread_wait = all_pos_test_cases_completed.wait(
                                    common_definitions.PARALLEL_SYNC_COMPLETED_TEST_TIMEOUT
                                )
                                if i_thread_wait == 0:
                                    logger.info(
                                        "All threads have synced test case completion."
                                    )
                                    all_pos_test_cases_completed.reset()

                            progress.set_progress(
                                general_state='testing',
                                test_positions=test_positions,
                                sequence_name=sequence_name,
                            )

                            test_position_instance.test_status = (
                                "Aborting" if test_control['abort'] else "Idle"
                            )

                            # Start post task and store it to list

                            bg_task = threading.Thread(target=test_instance.run_post_test)
                            bg_task.start()

                            background_post_tasks.append(bg_task)

                    except Exception as err:

                        if isinstance(err, gaiaclient.GaiaError):
                            logger.error("Caught Gaia error, abort testing.")
                            test_control['abort'] = True

                        if sync_test_cases:
                            if all_pos_mid_test_cases_completed is not None:
                                logger.info(
                                    "Abort mid test case thread barrier."
                                )
                                all_pos_mid_test_cases_completed.abort()
                            if all_pos_test_cases_completed is not None:
                                logger.info(
                                    "Abort completed test case thread barrier."
                                )
                                all_pos_test_cases_completed.abort()

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
                        test_position_instance.status = (
                            "Aborting" if test_control['abort'] else "Idle"
                        )
                        test_position_instance.step = None

                        progress.set_progress(
                            general_state='testing',
                            test_positions=test_positions,
                            sequence_name=sequence_name,
                        )

                for task in background_post_tasks:
                    task.join()

            loop_testing = True  # Execute at least one loop
            while loop_testing:
                loop_testing = common_definitions.LOOP_EXECUTION is True
                logger.info("Start %s.", "test loop" if loop_testing else "test")
                background_test_runs = []
                sync_test_cases = common_definitions.PARALLEL_EXECUTION == 'PER_TEST_CASE'
                all_pos_test_cases_completed = None
                all_pos_mid_test_cases_completed = None

                if loop_testing:
                    common_definitions.prepare_loop(
                        common_definitions.INSTRUMENTS, logger, test_positions, sequence_name
                    )

                if common_definitions.PARALLEL_EXECUTION in ['PARALLEL', 'PER_TEST_CASE']:
                    # Run test cases for each DUT in test position fully parallel
                    for test_position_name, test_position_instance in test_positions.items():

                        if (
                            test_position_instance.stop_looping
                            or test_position_instance.dut is None
                        ):
                            test_position_instance.stop_looping = True
                            logger.info(
                                "Skip position %s from test loop",
                                test_position_instance.name
                            )
                            continue

                        background_test_run = threading.Thread(
                            target=parallel_run, args=(
                                test_position_name,
                                test_position_instance,
                                sync_test_cases
                            )
                        )
                        background_test_runs.append(background_test_run)

                    logger.debug("Amount of test threads: %s", len(background_test_runs))

                    if sync_test_cases:
                        if common_definitions.PARALLEL_SYNC_PER_TEST_CASE in ['MID', 'BOTH']:
                            all_pos_mid_test_cases_completed = threading.Barrier(
                                len(background_test_runs)
                            )
                        if common_definitions.PARALLEL_SYNC_PER_TEST_CASE in ['COMPLETED', 'BOTH']:
                            all_pos_test_cases_completed = threading.Barrier(
                                len(background_test_runs)
                            )
                        if (
                            all_pos_mid_test_cases_completed is None and
                            all_pos_test_cases_completed is None
                        ):
                            raise Exception(
                                "Unknown common_definiton.PARALLEL_SYNC_PER_TEST_CASE parameter"
                            )

                    for test_run in background_test_runs:
                        test_run.start()

                    for test_run in background_test_runs:
                        test_run.join()

                elif common_definitions.PARALLEL_EXECUTION == 'PER_DUT':

                    # Run test cases for each DUT so that
                    # all test cases are run first for one DUT and then continue to another

                    for test_position_name, test_position_instance in test_positions.items():

                        if (
                            test_position_instance.stop_looping
                            or test_position_instance.dut is None
                        ):
                            test_position_instance.stop_looping = True
                            logger.info(
                                "Skip position %s from test loop",
                                test_position_instance.name
                            )
                            continue

                        parallel_run(
                            test_position_name,
                            test_position_instance,
                            sync_test_cases
                        )

                else:
                    raise Exception("Unknown test test_control.parallel_execution parameter")

                if loop_testing:
                    common_definitions.finalize_loop(
                        common_definitions.INSTRUMENTS, logger, test_positions, sequence_name
                    )
                    loop_testing = any(
                        not position.stop_looping for position in list(test_positions.values())
                    )
                    if not loop_testing:
                        logger.info("All test positions have stopped loop testing.")
                    else:
                        current_time = time.monotonic() - test_control['start_time_monotonic']
                        remaining_time = common_definitions.LOOP_TIME_IN_SECONDS - current_time
                        if remaining_time <= 0:
                            logger.info("Current loop time %.2f s is over loop time limit %.2f.",
                                current_time,
                                common_definitions.LOOP_TIME_IN_SECONDS
                            )
                            loop_testing = False
                        else:
                            logger.info("Current loop time %.2f s. Remaining time %.2f s.",
                                current_time, remaining_time
                            )
                    if not loop_testing:
                        logger.info("End loop testing.")
                if test_control['abort']:
                    loop_testing = False

            for test_position_name, test_position_instance in test_positions.items():

                if not test_position_instance.dut:
                    continue

                dut = test_position_instance.dut
                results[dut.serial_number] = dut.test_cases

                if test_control['abort']:
                    dut.pass_fail_result = 'abort'

                if dut.pass_fail_result == 'error':
                    errors = [
                        f"{case_name}: {case['error']}"
                        for case_name, case in dut.test_cases.items()
                        if case['result'] == 'error' and 'error' in case
                    ]

                    send_message(f"{dut.serial_number}: ERROR: " + ', '.join(errors))
                    test_position_instance.test_status = 'error'
                elif dut.pass_fail_result == 'pass':
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

            test_control['stop_time_monotonic'] = time.monotonic()

            # Don't create report if aborted
            if test_control['abort']:
                logger.warning("Test aborted. Finalize test as fail.")
                progress.set_progress(
                    general_state='abort',
                    test_positions=test_positions,
                    overall_result=dut.pass_fail_result,
                    sequence_name=sequence_name,
                )
                common_definitions.test_aborted(common_definitions.INSTRUMENTS, logger)
                continue

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
            results["running_mode"] = running_mode
            results["duration_s"] = round(time.monotonic() - start_time_monotonic, 2)

            if 'gage' in running_mode.lower():
                results["gage_rr"] = gage_progress.copy()

                if gage_progress['trial'] < gage_rr['trials'] - 1:
                    gage_progress['trial'] += 1
                elif gage_progress['dut'] < gage_rr['duts'] - 1:
                    gage_progress['dut'] += 1
                    gage_progress['trial'] = 0
                elif gage_progress['operator'] < gage_rr['operators'] - 1:
                    gage_progress['operator'] += 1
                    gage_progress['dut'] = 0
                    gage_progress['trial'] = 0
                else:
                    gage_progress['completed'] = True
                    gage_progress['operator'] = 0
                    gage_progress['dut'] = 0
                    gage_progress['trial'] = 0
                    logger.info("Gage R&R sequence has been completed.")
                progress.set_progress(
                    gage_progress=gage_progress
                )

        except exceptions.IrisError as ex:
            # TODO: write error to report
            logger.exception("Error on testsequence")
            logger.exception(str(ex))
            continue
        except Exception as ex:
            # TODO: write error to report
            logger.exception("Error on testsequence")
            logger.exception(str(ex))
            continue

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
        try:
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
        except Exception as e:
            progress.set_progress(general_state="Error")
            send_message("Error while generating a test report")
            send_message(str(e))
            logger.error("Error while generating a test report")
            logger.exception(e)

        if test_control['single_run']:
            test_control['terminate'] = True

    progress.set_progress(general_state="Shutdown")

    common_definitions.shutdown(common_definitions.INSTRUMENTS, logger)
