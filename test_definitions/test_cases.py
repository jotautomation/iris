from test_case import TestCase


class second(TestCase):

    def test(self, instruments):
        print("At second test case")
        self.new_result("Measurement1", 123)
        instruments['G5'].do_something_with_instrument()
        self.new_result("Measurement2", [123, 456, 1, 3])
