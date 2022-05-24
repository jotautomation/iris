class Dut:
    def __init__(self, serial_number, test_position, hw_id=None, order=None, additional_info=None):
        self.test_position = test_position
        self.serial_number = serial_number
        self.hw_id = hw_id
        self.order = order
        self.additional_info = additional_info
        self.test_cases = {}
        self.pass_fail_result = 'testing'
        self.failed_steps = []
        self.error_steps = []

    def get_dut_dict(self):

        return {
            'test_position': self.test_position,
            'serial_number': self.serial_number,
            'hw_id': self.hw_id,
            'order': self.order,
            'additional_info': self.additional_info,
            'test_cases': self.test_cases,
            'result': self.pass_fail_result,
            'failed_steps': self.failed_steps,
            'error_steps': self.error_steps,
        }
