import json2html


def create_report(json_report, filename):

    with open(filename, "w") as report_file:
        report_file.write(json2html.json2html.convert(json=json_report))
