from setuptools import setup, find_packages
import glob
import os

"""
Commands to publish
python setup.py sdist bdist_wheel
twine upload dist/*

"""


def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths


with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="super_simple_test_sequencer",
    version="0.6.0",
    license="MIT License",
    author="JOT Automation Ltd.",
    author_email="rami.rahikkala@jotautomation.com",
    description="Super simple test sequencer for production testing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://www.jotautomation.com",
    packages=find_packages(),
    package_data={"ui": package_files("ui/build/")},
    # packages=["test_definition_template/common", "test_definition_template/example_sequence", "test_runner/", "listener"],
    scripts=["super_simple_test_runner.py"],
    #    py_modules=['super_simple_test_runner', 'test_case', 'test_report_writer' 'test_report_writer'],
    install_requires=[
        "wheel",
        "json2html",
        "tornado",
        "gaiaclient",
        "PyYAML",
        "coloredlogs",
        "colorama",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
