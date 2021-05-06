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

    def __init__(
        self, limits, report_progress, dut, parameters, local_mongodb, common_definitions
    ):
        self.flow_control = common_definitions.FLOW_CONTROL
        self.parameters = parameters
        self.instruments = common_definitions.INSTRUMENTS
        self.dut = dut
        self.report_progress = report_progress
        self.limits = limits
        self.results = {}
        self.logger = logging.getLogger('test_case')
        self.start_time = None
        self.start_time_monotonic = None
        self.duration_s = None
        self.end_time = None
        self.test_position = None
        self.name = self.__class__.__name__
        self.local_mongodb = local_mongodb
        self.db_name = common_definitions.DB_NAME
        # Initialize measurement dictionary
        self.dut.measurements[self.name] = {}

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

    def clean_pass(self):
        """Called after all steps are done if pass_fail_result is True"""

    def clean_fail(self):
        """Called after all steps are done if pass_fail_result is not True"""

    def new_measurement(self, name, measurement):
        """Adds new measurement to measurement array"""
        self.dut.measurements[self.__class__.__name__][name] = measurement

    def stop_testing(self):
        """Stops testing before going to next test step"""
        self.test_position.stop_testing = True

    def result_handler(self, error=None):
        """Checks if test is pass or fail. Can be overridden if needed."""

        tmp_result = {}

        if error:
            tmp_result['Error'] = {"limit": None, "measurement": error, "result": False}
        elif self.limits:

            for measurement in self.dut.measurements[self.name].items():
                try:
                    limit = ''
                    measurement_value = None
                    measurement_name = measurement[0]
                    measurement_value = measurement[1]

                    limit = self.limits[self.name][measurement_name].get(
                        'report_limit',
                        inspect.getsource(self.limits[self.name][measurement_name]['limit']),
                    )

                    pass_fail_result = self.limits[self.name][measurement_name]['limit'](
                        measurement_value
                    )

                    tmp_result[measurement_name] = {
                        "unit": self.limits[self.name][measurement_name].get('unit', ''),
                        "limit": limit,
                        "measurement": measurement_value,
                        "result": pass_fail_result,
                    }

                except Exception as exp:
                    tmp_result[measurement_name] = {
                        "unit": '',
                        "limit": limit,
                        "measurement": measurement_value,
                        "result": "ErrorOnLimits",
                        "error": exp,
                    }
                finally:
                    if not pass_fail_result:
                        self.dut.pass_fail_result = False
                        self.dut.failed_steps.append(self.name)
                        if self.flow_control == FlowControl.STOP_ON_FAIL:
                            self.stop_testing()

        else:
            tmp_result['no_limit_defined'] = {
                "limit": None,
                "measurement": None,
                "measurement": True,
            }

        return tmp_result

    def run_pre_test(self):

        self.start_time = datetime.datetime.now()
        self.start_time_monotonic = time.monotonic()
        self.pre_test()
        self.evaluate_results()

    def run_test(self):
        self.test()
        self.evaluate_results()

    def run_post_test(self):
        self.post_test()

        self.evaluate_results()

        if self.dut.pass_fail_result:
            self.clean_pass()
        else:
            self.clean_fail()

        self.clean()

        self.end_time = datetime.datetime.now()
        self.duration_s = time.monotonic() - self.start_time_monotonic

        self.dut.results[self.name].update(
            {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_s": round(self.duration_s, 2),
            }
        )

    def handle_error(self, error):
        self.dut.results.setdefault(self.name, {}).update(self.result_handler(error))
        self.clean_error()

    def evaluate_results(self):

        self.dut.results.setdefault(self.name, {}).update(self.result_handler())

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
        self._store_test_data_file_to_db(dest_path, **kwargs)

    def _store_test_data_file_to_db(self, file_path, **kwargs):
        if self.local_mongodb:
            self.local_mongodb[self.db_name].file_attachments.insert_one(
                {
                    'file_path': str(file_path),
                    'testRunId': self.test_run_id,
                    'testCase': self.name,
                    'dut': self.dut.serial_number,
                    'added': datetime.datetime.now(),
                    **kwargs,
                }
            )
