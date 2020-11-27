from setuptools import setup, find_packages
import glob
import os
import tarfile
import pathlib


"""
Commands to publish
python3 setup.py bdist_wheel
twine upload dist/*

"""


def get_ui():
    try:
        import docker
    except ImportError:
        return
    file_stream = open('ui.tar', 'wb')
    client = docker.from_env()
    client.images.pull('ci.jot.local:5000/ssts_ui')
    ctnr = client.containers.create('ci.jot.local:5000/ssts_ui', name='ssts_ui')
    api_client = docker.APIClient()
    bits, stat = api_client.get_archive('ssts_ui', '/usr/src/app/build')

    for chunk in bits:
        file_stream.write(chunk)
    file_stream.close()
    ctnr.remove()
    tar = tarfile.open("ui.tar")
    tar.extractall('ui/build')
    tar.close()

    # Remove tar file
    pathlib.Path('ui.tar').unlink()


def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths


with open("README.md", "r") as fh:
    long_description = fh.read()

get_ui()

setup(
    name="super_simple_test_sequencer",
    version="0.11.1",
    license="MIT License",
    author="JOT Automation Ltd.",
    author_email="rami.rahikkala@jotautomation.com",
    description="Super simple test sequencer for production testing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://www.jotautomation.com",
    packages=find_packages(),
    package_data={"ui": package_files("ui/build/"), "dist_files": package_files('dist_files/')},
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
