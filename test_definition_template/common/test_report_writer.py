"""
Handles the creation of the result files and directories
"""

import datetime
import pathlib
import json2html


def create_report(report_json, report_dict, duts):
    """Creates and stores report for DUT(s)"""

    current = datetime.datetime.now()

    filename = '_'.join(['%s-%s' % (key, value) for (key, value) in duts.items()])

    report_path = (
        pathlib.Path.cwd() / 'results' / str(current.year) / str(current.month) / str(current.day)
    )
    report_path.mkdir(parents=True, exist_ok=True)

    report_file_path = report_path / (filename + '.html')

    report_file_path.write_text(json2html.json2html.convert(json=report_json))
