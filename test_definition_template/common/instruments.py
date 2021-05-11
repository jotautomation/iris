"""Instrument definitions"""
import time
import gaiaclient
import requests


# This definition will also run when new test sequence is created.
# Thus it is not good idea to connect to instrument here
# connect at instrument_initialization instead.

INSTRUMENTS = {"gaia": None}


def instrument_initialization(progress):
    """Connect and initialize instruments"""

    _connect_to_gaia(progress)


def handle_instrument_status(progress):
    """Reconnect to instrument, do other error resolving or any other status triggered task.
    Called in the beginning of each test run."""
    if progress.instrument_status['gaia'] == "MagicMock":
        return

    # Reconnect until connection is ok
    while progress.instrument_status['gaia'] != "OK":

        _connect_to_gaia(progress)

        time.sleep(10)


def _connect_to_gaia(progress):
    try:
        INSTRUMENTS["gaia"] = gaiaclient.Client("http://localhost:1234")
    except requests.exceptions.ConnectionError as e:
        progress.set_instrument_status('gaia', "Connection error")
    else:
        progress.set_instrument_status('gaia', "OK")
