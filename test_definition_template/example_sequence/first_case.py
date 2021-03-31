from test_runner.test_case import TestCase


class first(TestCase):
    def pre_test(self, instruments, dut):
        pass
    def test(self, instruments, dut):
        print("At first test case")
        self.new_result("Measurement1", 123)
        # instruments["G5"].do_something_with_instrument()
        self.new_result("Measurement2", [123, 456, 1, 3])
        import time
        time.sleep(2)

    def post_test(self, instruments, dut):
        pass
