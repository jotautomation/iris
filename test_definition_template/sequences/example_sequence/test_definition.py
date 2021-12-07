"""Defines tests and their order"""

# Set order of tests
# Use "_pre" to specify when pre-test is started
# If "_pre" is not specified, pre-test will be run before the test
# Post-test will be run always on background after the test
TESTS = ["Second_pre", "First", "Second", "Third", "Fourth", "PoolTestCase"]

SKIP = ["Third", "Fourth"]

# Amount of DUTs to be tested for specific sequence. If not defined, defaults to 1.
DUTS = 1
