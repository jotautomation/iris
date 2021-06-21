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
        self.instrument_status = None
        self.version_info = None

    def set_instrument_status(self, instrument, status):

        if self.instrument_status is None:
            self.instrument_status = {}

        self.instrument_status[instrument] = status
        self._report_progress()

    def set_version_info(self, version_name, version_value):

        if self.version_info is None:
            self.version_info = {}

        self.version_info[version_name] = version_value
        self._report_progress()

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
            "test_cases": self.test_control['test_cases'],
        }

        if self.overall_result:
            progress_json['overall_result'] = self.overall_result

        progress_json['statistics'] = self.statistics
        progress_json['instrument_status'] = self.instrument_status
        progress_json['version_info'] = self.version_info

        progress_json['operator_instructions'] = self.operator_instructions

        self.test_control['progress'] = progress_json
        self.progess_queue.put(json.dumps(progress_json, default=str))
