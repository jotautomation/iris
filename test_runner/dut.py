class Dut:
    def __init__(self, serial_number, test_position, hw_id=None, patch=None, additional_info=None):
        self.test_position = test_position
        self.serial_number = serial_number
        self.hw_id = hw_id
        self.patch = patch
        self.additional_info = additional_info
        self.test_cases = {}
        self.pass_fail_result = True
        self.failed_steps = []
