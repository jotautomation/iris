"""Common definitions for all test sequencies"""
import os
import socket
from test_runner.test_position import TestPosition
from test_runner.dut import Dut
from test_runner.test_case import FlowControl

TEST_POSITIONS = [
    TestPosition('1', 'left'),
    TestPosition('2', 'middle'),
    TestPosition('3', 'right'),
]

DB_HANDLER_NAME = 'test_data_db'

# Update test limits and box parameters from database
UPDATE_PARAMS_FROM_DATABASE = True

# FlowControl.CONTINUE keeps testing even some test fails
# FlowControl.STOP_ON_FAIL stops on first fail

FLOW_CONTROL = FlowControl.CONTINUE

# PARALLEL, PER_DUT, PER_TEST_CASE
PARALLEL_EXECUTION = 'PARALLEL'

# MID, COMPLETED, BOTH
PARALLEL_SYNC_PER_TEST_CASE = 'MID'

# Thread syncing waiting timeout in seconds
# Mid test case thread syncing timeout is defined in test cases
PARALLEL_SYNC_COMPLETED_TEST_TIMEOUT = 10.0

LOOP_EXECUTION = True

LOOP_TIME_IN_SECONDS = 30 * 60

# Wait DUT serial number from UI
SN_FROM_UI = True

# Wait DUT from external source
SN_EXTERNALLY = False
# Use instrument (gaia) to receive DUT info
SN_FROM_INSTRUMENT = False
SN_INSTRUMENT_NAME = "gaia"

# Show operator introductions
OPERATOR_INTRODUCTIONS = False

# List of test sequences' directory names
TEST_SEQUENCES = os.listdir('test_definitions/sequences')

# List of possible running modes
RUNNING_MODES = ["Production", "Debug", "GageRR"]

# Gage R&R settings
GAGE_RR = {
    "operators": 3,
    "duts": 10,
    "trials": 3,
}

def parse_dut_info(info, test_position, order=""):
    return Dut(serial_number=info['sn'], test_position=test_position, order=order)


def get_my_ip(ext_url):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(ext_url)
        return sock.getsockname()[0]


# Use here the external url that want's to connect to to Iris
IRIS_IP = get_my_ip(("8.8.8.8", 80))
