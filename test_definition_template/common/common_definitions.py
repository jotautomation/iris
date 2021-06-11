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

# FlowControl.CONTINUE keeps testing even some test fails
# FlowControl.STOP_ON_FAIL stops on first fail

FLOW_CONTROL = FlowControl.CONTINUE

# Wait DUT serial number from UI
SN_FROM_UI = True


# List of test sequences' directory names
TEST_SEQUENCES = os.listdir('test_definitions/sequences')


def parse_dut_info(info, test_position):
    return Dut(serial_number=info['sn'], test_position=test_position)


def get_my_ip(ext_url):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(ext_url)
        return sock.getsockname()[0]


# Use here the external url that want's to connect to to Iris
IRIS_IP = get_my_ip(("8.8.8.8", 80))
