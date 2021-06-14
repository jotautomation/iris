"""Instrument definitions"""
import time
import gaiaclient
import requests
from common import mongodb_handler
import pymongo


# This definition will also run when new test sequence is created.
# Thus it is not good idea to connect to instrument here
# connect at instrument_initialization instead.

INSTRUMENTS = {'gaia': None, 'test_data_db': None}


def instrument_initialization(progress):
    """Connect and initialize instruments"""
    progress.set_instrument_status('test_data_db', 'Not initialized')
    _connect_to_gaia(progress)
    _connect_to_db(progress)


def get_tester_info():
    # Tester info
    return {"name": "First delivery", "type": "G5", "serial": "1234abc"}


def handle_instrument_status(progress):
    """Reconnect to instrument, do other error resolving or any other status triggered task.
    Called in the beginning of each test run."""
    if progress.instrument_status['gaia'] != "MagicMock":

        # Reconnect until connection is ok
        while progress.instrument_status['gaia'] != "OK":

            _connect_to_gaia(progress)

            time.sleep(10)

    if progress.instrument_status['test_data_db'] != "MagicMock":

        # Reconnect until connection is ok
        while progress.instrument_status['test_data_db'] != "OK":

            _connect_to_db(progress)

            time.sleep(10)


def _connect_to_gaia(progress):
    try:
        INSTRUMENTS["gaia"] = gaiaclient.Client("http://localhost:1234")
    except requests.exceptions.ConnectionError as e:
        progress.set_instrument_status('gaia', "Connection error")
    else:
        progress.set_instrument_status('gaia', "OK")


def _connect_to_db(progress):
    try:
        INSTRUMENTS['test_data_db'] = mongodb_handler.DatabaseHandler(
            'mongodb://JOTUser:YOURPASSWORDHERE@localhost:2701/production_testing',
            'production_testing',
        )
        INSTRUMENTS['test_data_db'].db_client.server_info()

    except pymongo.errors.OperationFailure as err:
        progress.set_instrument_status('test_data_db', err.details['errmsg'])
    except pymongo.errors.ServerSelectionTimeoutError:
        progress.set_instrument_status('test_data_db', 'Connection error')
    else:
        progress.set_instrument_status('test_data_db', "OK")
