"""Common definitions for all test sequencies"""
import os
from test_runner.test_position import TestPosition
from test_runner.dut import Dut


TEST_POSITIONS = [TestPosition('1', 'left'), TestPosition('2', 'middle'), TestPosition('3', 'right')]

# Wait DUT serial number from UI
SN_FROM_UI = True

# List of test sequences' directory names
TEST_SEQUENCES = os.listdir('test_definitions')
if 'common' in TEST_SEQUENCES:
    TEST_SEQUENCES.remove('common')


def parse_dut_info(info, test_position):
    return Dut(serial_number=info['sn'], test_position=test_position)
