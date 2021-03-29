from setuptools import setup, find_packages
import glob
import os
import tarfile
import pathlib


"""
To publish:
1. Make sure you have all the dependencies (Activate virtual env. Import Docker will fail silently, if missing!)
2. python setup.py bdist_wheel
3. twine upload dist/*

"""


def get_ui():
    try:
        import docker
    except ImportError:
        return
    file_stream = open('ui.tar', 'wb')
    client = docker.from_env()
    client.images.pull('ci.jot.local:5000/iris_ui')
    ctnr = client.containers.create('ci.jot.local:5000/iris_ui', name='iris_ui')
    api_client = docker.APIClient()
    bits, stat = api_client.get_archive('iris_ui', '/usr/src/app/build')

    for chunk in bits:
        file_stream.write(chunk)
    file_stream.close()
    ctnr.remove()
    tar = tarfile.open("ui.tar")
    tar.extractall('ui')
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
    name="jot-iris",
    version="0.14.8",
    license="MIT License",
    author="JOT Automation Ltd.",
    author_email="rami.rahikkala@jotautomation.com",
    description="Super simple test sequencer for production testing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://www.jotautomation.com",
    packages=find_packages(),
    # Package_data will add files to package(s) defined in previous file.
    # Here we add files to ui/build and to additional_dist_files
    # This way we get UI and other non-python files distributed
    package_data={
        "ui": package_files("ui/build/"),
        "additional_dist_files": package_files('additional_dist_files/'),
    },
    scripts=["iris.py"],
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
