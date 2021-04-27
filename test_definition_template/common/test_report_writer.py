"""
Handles the creation of the result files and directories
"""

import datetime
import pathlib
import json2html


def create_report(report_json, report_dict, test_positions, parameters):
    """Creates and stores report for DUT(s)"""

    filename = '_'.join(
        [
            '%s-%s' % (test_position_name, test_position_value.dut.serial_number)
            for (test_position_name, test_position_value) in test_positions.items()
        ]
    )

    report_path = create_report_path()

    report_file_path = report_path / (filename + '.html')

    report_file_path.write_text(json2html.json2html.convert(json=report_json))


def create_report_path():
    current = datetime.datetime.now()

    report_path = (
        pathlib.Path.cwd() / 'results' / str(current.year) / str(current.month) / str(current.day)
    )
    report_path.mkdir(parents=True, exist_ok=True)

    return report_path
