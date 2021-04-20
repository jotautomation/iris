"""Base for all test cases"""

from abc import ABC, abstractmethod
import inspect
import logging
import datetime
import time

from enum import Enum


class FlowControl(Enum):
    """Defines flow control options"""

    """Stop if result was fail"""
    STOP_ON_FAIL = 1

    """Continue always"""
    CONTINUE = 3


class TestCase(ABC):
    """Base for all test cases"""

    def __init__(self, limits, report_progress, dut, instruments, parameters, flow_control):
        self.flow_control = flow_control
        self.parameters = parameters
        self.instruments = instruments
        self.dut = dut
        self.report_progress = report_progress
        self.limits = limits
        self.results = {}
        self.logger = logging.getLogger('test_case')
        self.start_time = None
        self.start_time_monotonic = None
        self.duration_s = None
        self.end_time = None
        self.test_position = None
        self.name = self.__class__.__name__
        # Initialize measurement dictionary
        self.dut.measurements[self.name] = {}

    @abstractmethod
    def test(self):
        """Defines the test case."""

    def pre_test(self):
        """This method will be run on background before the actual test"""

    @abstractmethod
    def post_test(self):
        """This method will be run on background after the actual test"""

    def clean(self):
        """Called after all steps are done"""

    def clean_pass(self):
        """Called after all steps are done if pass_fail_result is True"""

    def clean_fail(self):
        """Called after all steps are done if pass_fail_result is not True"""

    def new_measurement(self, name, result):
        """Adds new result to result array"""
        self.dut.measurements[self.__class__.__name__][name] = result

    def stop_testing(self):
        """Stops testing before going to next test step"""
        self.test_position.stop_testing = True

    def result_handler(self, error=None):
        """Checks if test is pass or fail. Can be overridden if needed."""

        tmp_result = {}

        if error:
            tmp_result['Error'] = {"limit": None, "measurement": error, "result": False}
        elif self.limits:
            for result in self.dut.measurements[self.name].items():
                pass_fail_result = self.limits[self.name][result[0]](result[1])
                tmp_result[result[0]] = {
                    "limit": inspect.getsource(self.limits[self.name][result[0]]),
                    "measurement": result[1],
                    "result": pass_fail_result,
                }
                if not pass_fail_result:
                    self.dut.pass_fail_result = False
                    self.dut.failed_steps.append(self.name)
                    if self.flow_control == FlowControl.STOP_ON_FAIL:
                        self.stop_testing()

        else:
            tmp_result['no_limit_defined'] = {"limit": None, "measurement": None, "result": True}

        return tmp_result

    def run_pre_test(self):

        self.start_time = datetime.datetime.now()
        self.start_time_monotonic = time.monotonic()
        self.pre_test()
        self.evaluate_results()

    def run_test(self):
        self.test()
        self.evaluate_results()

    def run_post_test(self):
        self.post_test()

        self.evaluate_results()

        if self.dut.pass_fail_result:
            self.clean_pass()
        else:
            self.clean_fail()

        self.clean()

        self.end_time = datetime.datetime.now()
        self.duration_s = time.monotonic() - self.start_time_monotonic

    def handle_error(self, error):
        self.dut.results.update(self.result_handler(error))
        self.clean_error()

    def evaluate_results(self):
        self.dut.results.update(self.result_handler())
