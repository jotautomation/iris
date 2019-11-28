"""Base for all test cases"""

from abc import ABC, abstractmethod
import inspect


class TestCase(ABC):
    """Base for all test cases"""

    def __init__(self):
        self.results = {}

    @abstractmethod
    def test(self, instruments, dut):
        """Contains the test sequence"""

    def new_result(self, name, result):
        self.results[name] = result

    def result_handler(self, limits):
        """Checks if test is pass or fail. Can be overridden if needed"""

        tmp_result = {}

        for result in self.results.items():
            tmp_result[result[0]] = {"limit": inspect.getsource(limits[result[0]]),
                                     "measurement": result[1],
                                     "result": limits[result[0]](result[1])}

        return tmp_result



