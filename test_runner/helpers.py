import datetime
import sys
import os
import json
import importlib
import threading
from test_runner import exceptions


def import_by_name(name, error_message):
    sys.path.append(os.getcwd())
    sys.path.append(os.path.join(os.getcwd(), 'test_definitions'))

    try:
        imp = importlib.import_module(name)

        # TODO: This hides also errors on nested imports
    except ImportError as err:
        print(err)
        print(error_message)
        sys.exit(-1)

    return imp


def get_test_pool_definitions():
    """Returns test definition pool"""

    return import_by_name('test_case_pool', "test_case_pool missing?")


def get_test_definitions(sequence_name):
    """Returns test definitions"""

    err = (
        "Error loading "
        + sequence_name
        + ". Remember, you can create new definition template with --create argument."
    )

    return import_by_name("sequences." + sequence_name, err)
