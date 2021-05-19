from test_runner.test_case import TestCase


class First(TestCase):
    def pre_test(self):
        # pre_test() will be run always before test().
        # Use "First_pre" to specify when pre_test of this class is started.
        # If "First_pre" is not specified, pre_test will be run just before the test.
        pass

    def test(self):
        self.logger.info("At first test case")
        self.show_operator_instructions("Ínstructions for the operator")
        with open('test_data.txt', 'w') as test_data_file:
            test_data_file.write("Sample data inside the file")

        self.store_test_data_file(
            'test_data.txt',
            'Measurement1_data',
            any_additional_data="Is added as parameter",
            one_more_parameter="sample parameter",
        )

        self.new_measurement("Measurement1", 123)
        # instruments["G5"].do_something_with_instrument()
        self.new_measurement("Measurement2", [123, 456, 1, 3])

        import time

        time.sleep(2)

    def post_test(self):
        # post_test will be run always on background after the test
        pass
