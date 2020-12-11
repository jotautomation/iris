"""Base for all test cases"""

from abc import ABC, abstractmethod
import inspect
import logging


class TestCase(ABC):
    """Base for all test cases"""

    def __init__(self):
        self.results = {}
        self.logger = logging.getLogger('test_case')

    @abstractmethod
    def test(self, instruments, dut):
        """Defines the test case."""

    def new_result(self, name, result):
        """Adds new result to result array"""
        self.results[name] = result

    def result_handler(self, limits, error=None):
        """Checks if test is pass or fail. Can be overridden if needed."""

        tmp_result = {}

        if error:
            tmp_result['Error'] = {"limit": None, "measurement": error, "result": False}
        elif limits:
            for result in self.results.items():
                tmp_result[result[0]] = {
                    "limit": inspect.getsource(limits[result[0]]),
                    "measurement": result[1],
                    "result": limits[result[0]](result[1])
                }
        else:
            tmp_result['Success'] = {"limit": None, "measurement": None, "result": True}

        return tmp_result
