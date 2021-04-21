from test_runner.test_case import TestCase


class Second(TestCase):
    def pre_test(self):
        pass

    def test(self):
        print("At second test case")
        self.new_measurement("Measurement1", 123)
        # instruments["G5"].do_something_with_instrument()
        self.new_measurement("Measurement2", [123, 456, 1, 3])
        import time
        time.sleep(2)

    def post_test(self):
        pass
