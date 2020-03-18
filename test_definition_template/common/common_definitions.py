"""Common definitions for all test sequencies"""
import os

# This DUT definition is used only if SN input comes from UI.
# Otherwise DUT definition must come from prepare_test()
DUTS = ["left", "right", "middle"]

# Wait DUT serial number from UI
SN_FROM_UI = True

# List of test sequences' directory names
TEST_SEQUENCES = os.listdir('test_definitions')
if 'common' in TEST_SEQUENCES:
    TEST_SEQUENCES.remove('common')
