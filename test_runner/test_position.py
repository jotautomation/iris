class TestPosition:
    def __init__(self, name, ui_position):
        self.name = name
        self.ui_position = ui_position
        self.step = None
        self.status = None
        self.test_status = None
        self.test_case_instances = {}
        self.dut = None
        self.stop_testing = False
        self.stop_looping = False
        self.stop_reporting = False
        self.previous_dut = False

    def prepare_for_new_test_run(self):
        if self.dut:
            self.previous_dut = self.dut.get_dut_dict()

        self.step = None
        self.status = 'wait'
        self.dut = None
        self.test_case_instances = {}
        self.stop_testing = False
        self.stop_looping = False
        self.stop_reporting = False

        if not self.test_status:
            self.test_status = "Idle"

    def __str__(self):
        return self.name
