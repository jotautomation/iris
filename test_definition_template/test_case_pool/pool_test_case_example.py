"""Example of test case defined at 'pool'. These cases are available
for all test sequences"""

from test_runner.test_case import TestCase


class PoolTestCase(TestCase):
    def pre_test(self, instruments, dut, parameters):
        pass

    def test(self, instruments, dut, parameters):
        print("Running test case from pool")
        print(
            "Parameters can be used to parametrize the testing: "
            + parameters.EXAMPLE_PARAMETER['dut1']
        )

    def post_test(self, instruments, dut, parameters):
        pass
