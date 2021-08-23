"""Base for all test cases"""
from abc import ABC, abstractmethod
import inspect
import logging
import datetime
import time

from enum import Enum
from pymongo import MongoClient
from pathlib import Path


class FlowControl(Enum):
    """Defines flow control options"""

    """Stop if result was fail"""
    STOP_ON_FAIL = 1

    """Continue always"""
    CONTINUE = 3


class TestCase(ABC):
    """Base for all test cases"""

    def __init__(self, limits, report_progress, dut, parameters, db_handler, common_definitions):
        self.flow_control = common_definitions.FLOW_CONTROL
        self.logger = logging.getLogger('test_case')
        self.parameters = parameters
        self.instruments = common_definitions.INSTRUMENTS
        self.dut = dut
        self.report_progress = report_progress
        self.limits = limits
        self.logger = logging.getLogger('test_case')
        self.start_time = None
        self.start_time_monotonic = None
        self.duration_s = None
        self.end_time = None
        self.test_position = None
        self.name = self.__class__.__name__
        self.db_handler = db_handler
        self.my_ip = common_definitions.IRIS_IP
        # Initialize measurement dictionary
        self.dut.test_cases[self.name] = {'result': True, 'measurements': {}}

    def show_operator_instructions(self, message, append=False):
        self.report_progress.show_operator_instructions(message, append)

    @abstractmethod
    def test(self):
        """Defines the test case."""

    def pre_test(self):
        """This method will be run on background before the actual test"""

    @abstractmethod
    def post_test(self):
        """This method will be run on background after the actual test"""

    def clean(self):
        """Called after all steps are done"""

    def clean_error(self):
        """Called after all steps are done"""

    def clean_pass(self):
        """Called after all steps are done if pass_fail_result is True"""

    def clean_fail(self):
        """Called after all steps are done if pass_fail_result is not True"""

    def new_measurement(self, name, measurement):
        """Adds new measurement to measurement array"""
        self.logger.debug("New measurement: %s:%s:%s", self.name, name, measurement)

        if name not in self.dut.test_cases[self.name]['measurements']:
            self.dut.test_cases[self.name]['measurements'][name] = {}

        self.dut.test_cases[self.name]['measurements'][name]['measurement'] = measurement

    def stop_testing(self):
        """Stops testing before going to next test step"""
        self.test_position.stop_testing = True

    def result_handler(self, error=None):
        """Checks if test is pass or fail. Can be overridden if needed."""

        case = self.dut.test_cases[self.name]

        for measurement_name, measurement_dict in self.dut.test_cases[self.name][
            'measurements'
        ].items():
            pass_fail_result = True
            limit = None
            unit = None
            try:
                case['measurements'][measurement_name]["error"] = None

                measurement_value = measurement_dict['measurement']

                if self.name in self.limits:
                    limit = self.limits[self.name][measurement_name].get(
                        'report_limit',
                        inspect.getsource(self.limits[self.name][measurement_name]['limit']),
                    )

                    pass_fail_result = self.limits[self.name][measurement_name]['limit'](
                        measurement_value
                    )

                    unit = self.limits[self.name][measurement_name].get('unit', '')

                case['measurements'][measurement_name]["unit"] = unit
                case['measurements'][measurement_name]["limit"] = limit
                case['measurements'][measurement_name]["result"] = pass_fail_result

            except Exception as exp:
                case['measurements'][measurement_name]["unit"] = unit
                case['measurements'][measurement_name]["limit"] = limit
                case['measurements'][measurement_name]["result"] = "ErrorOnLimits"
                case['measurements'][measurement_name]["error"] = str(type(exp)) + ': ' + str(exp)

            finally:
                if not pass_fail_result:

                    self.dut.pass_fail_result = False

                    self.dut.test_cases[self.name]['result'] = False

                    if self.name not in self.dut.failed_steps:
                        self.dut.failed_steps.append(self.name)

                    if self.flow_control == FlowControl.STOP_ON_FAIL:
                        self.stop_testing()

                if error:
                    case['result'] = 'error'
                    case['error'] = error
                    self.dut.pass_fail_result = 'error'
                    if self.flow_control == FlowControl.STOP_ON_FAIL:
                        self.stop_testing()

    def check_measurements_vs_limits(self):

        for limit_test_case_name, limit_test_case in self.limits.items():
            for limit in limit_test_case:

                if 'optional' in limit_test_case[limit] and limit_test_case[limit]['optional']:
                    continue

                if (
                    limit_test_case_name not in self.dut.test_cases
                    or limit
                    not in self.dut.test_cases[limit_test_case_name]['measurements'].keys()
                ):

                    self.dut.pass_fail_result = 'error'
                    self.dut.test_cases[limit_test_case_name]['result'] = 'error'
                    self.dut.test_cases[limit_test_case_name][
                        'error'
                    ] = f'Measurement "{limit}" missing'

                    if self.flow_control == FlowControl.STOP_ON_FAIL:
                        self.stop_testing()

    def run_pre_test(self):
        self.logger.debug("Running pre_test at %s", self.name)
        self.start_time = datetime.datetime.now()
        self.start_time_monotonic = time.monotonic()
        self.pre_test()
        self.evaluate_results()
        self.logger.debug("Pre_test done at %s", self.name)

    def run_test(self):
        self.logger.debug("Running test at %s", self.name)
        self.test()
        self.evaluate_results()
        self.logger.debug("Test done at %s", self.name)

    def run_post_test(self):
        self.logger.debug("Running post_test done at %s", self.name)
        self.post_test()

        self.evaluate_results()
        self.check_measurements_vs_limits()

        if self.dut.pass_fail_result:
            self.clean_pass()
        else:
            self.clean_fail()

        self.clean()

        self.end_time = datetime.datetime.now()
        self.duration_s = time.monotonic() - self.start_time_monotonic

        self.dut.test_cases[self.name].update(
            {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_s": round(self.duration_s, 2),
            }
        )
        self.logger.debug("Post_test done at %s", self.name)

    def handle_error(self, error):
        self.logger.warn("Error at %s: %s", self.name, error)
        self.result_handler(error)

        self.end_time = datetime.datetime.now()
        self.duration_s = time.monotonic() - self.start_time_monotonic

        self.dut.test_cases[self.name].update(
            {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_s": round(self.duration_s, 2),
            }
        )
        self.clean_error()

    def evaluate_results(self):

        self.result_handler()

    def store_test_data_file(self, source_file_path, dest_name, **kwargs):
        from common.test_report_writer import create_report_path

        dest_name = (
            self.name + '_' + self.dut.serial_number + '_' + self.test_run_id + '_' + dest_name
        )

        report_path = create_report_path()
        dest_path = Path(report_path, 'file_attachments')
        dest_path.mkdir(parents=True, exist_ok=True)
        dest_path = dest_path / dest_name
        Path(source_file_path).rename(dest_path)

        data = {
            'name': dest_name,
            'file_path': str(dest_path),
            'testRunId': self.test_run_id,
            'testCase': self.name,
            'dut': self.dut.serial_number,
            'added': datetime.datetime.now(),
            'size': Path(dest_path).stat().st_size,
            'expires': datetime.datetime.now() + datetime.timedelta(weeks=1),
            'url': f'http://{self.my_ip}/api/media/{dest_name}',
            **kwargs,
        }

        self._store_test_data_file_to_db(data)

        # Store data to test cases for reporting
        if 'media' not in self.dut.test_cases[self.name]:
            self.dut.test_cases[self.name]['media'] = []

        self.dut.test_cases[self.name]['media'].append(data)

    def _store_test_data_file_to_db(self, data):
        if self.db_handler:
            self.db_handler.store_test_data_file_to_db(**data)
