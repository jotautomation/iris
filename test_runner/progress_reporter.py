import json


class ProgressReporter:
    def __init__(self, test_control, progess_queue):
        self.test_control = test_control
        self.statistics = None
        self.general_step = None
        self.test_positions = None
        self.overall_result = None
        self.sequence_name = None
        self.operator_instructions = None
        self.progess_queue = progess_queue

    def set_progress(self, **kwargs):
        # Store variable
        self.__dict__.update(kwargs)
        # Send new progress json
        self._report_progress()

    def show_operator_instructions(self, message, append=False):
        if append and self.operator_instructions:
            self.operator_instructions = self.operator_instructions + '\r\n' + message
        else:
            self.operator_instructions = message

        self._report_progress()

    def _report_progress(self):

        positions_dict = {}

        if self.test_positions:
            for position_name, position_value in self.test_positions.items():
                positions_dict[position_name] = {
                    'step': position_value.step,
                    'status': position_value.status,
                    'sn': None if position_value.dut is None else position_value.dut.serial_number,
                    'test_status': str(position_value.test_status),
                }

        progress_json = {
            "general_state": self.general_step,
            "duts": positions_dict,
            "sequence_name": self.sequence_name,
            "get_sn_from_ui": self.test_control['get_sn_from_ui'],
            "test_sequences": self.test_control['test_sequences'],
        }

        if self.overall_result:
            progress_json['overall_result'] = self.overall_result

        progress_json['statistics'] = self.statistics

        progress_json['operator_instructions'] = self.operator_instructions

        self.test_control['progress'] = progress_json
        self.progess_queue.put(json.dumps(progress_json, default=str))
