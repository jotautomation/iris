"""Defines tests and their order"""

# Set order of tests
# Use "_pre" to specify when pre test is started
# If "_pre" is not specified, pre test will be run before the test
# Post test will be run alway on background after the test
TESTS = ["second_pre", "first", "second", "third", "fourth"]

SKIP = ["first", "third", "fourth"]

