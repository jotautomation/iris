import datetime
import sys
import os
import json
import importlib
import threading
from test_runner import exceptions


def import_by_name(name, error_message):
    sys.path.append(os.getcwd())
    sys.path.append(os.path.join(os.getcwd(), 'test_definitions'))

    try:
        imp = importlib.import_module(name)

        # TODO: This hides also errors on nested imports
    except ImportError as err:
        print(err)
        print(error_message)
        sys.exit(-1)

    return imp


def get_test_pool_definitions():
    """Returns test definition pool"""

    return import_by_name('test_case_pool', "test_case_pool missing?")


def get_test_definitions(sequence_name):
    """Returns test definitions"""

    err = (
        "Error loading "
        + sequence_name
        + ". Remember, you can create new definition template with --create argument."
    )

    return import_by_name(sequence_name, err)


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


def get_test_instance(test_definitions, test_case, test_pool):
    test_case_name = test_case.replace('_pre', '').replace('_pre', '')
    if hasattr(test_definitions, test_case_name):
        test_instance = getattr(test_definitions, test_case_name)()
    elif hasattr(test_pool, test_case_name):
        test_instance = getattr(test_pool, test_case_name)()
    else:
        raise exceptions.TestCaseNotFound("Cannot find specified test case: " + test_case_name)
    return test_instance
