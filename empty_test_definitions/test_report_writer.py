"""
Handles the creation of the result files and directories
"""

import datetime
import pathlib
import json2html


def create_report(json_report, dut):
    """Creates and stores report for DUT(s)"""

    current = datetime.datetime.now()

    report_path = (
        pathlib.Path.cwd() / 'results' / str(current.year) / str(current.month) / str(current.day)
    )
    report_path.mkdir(parents=True, exist_ok=True)

    report_file_path = report_path / (dut + '.html')

    report_file_path.write_text(json2html.json2html.convert(json=json_report))
