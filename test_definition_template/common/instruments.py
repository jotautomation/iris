"""Instrument definitions"""
import time
import gaiaclient
import requests
import pymongo


# This definition will also run when new test sequence is created.
# Thus it is not good idea to connect to instrument here
# connect at instrument_initialization instead.

INSTRUMENTS = {'gaia': None, 'test_data_db': None}


def get_tester_info():
    # Tester info
    return {"name": "First delivery", "type": "G5", "serial": "1234abc"}


def handle_instrument_status(progress, logger):
    """Reconnect to instrument, do other error resolving or any other status triggered task.
    Called in the beginning of each test run."""

    def _connect_to_db(logger):
        # This import doesn't work when creating new test sequence
        # so let's import it here when needed
        from common import mongodb_handler
        try:
            INSTRUMENTS['test_data_db'] = mongodb_handler.DatabaseHandler(
                'mongodb://JOTUser:YOURPASSWORDHERE@localhost:2701/production_testing',
                'production_testing',
            )
            INSTRUMENTS['Line test_data_db'].db_client.server_info()

        except pymongo.errors.OperationFailure as err:
            return err.details['errmsg']
        except pymongo.errors.ServerSelectionTimeoutError:
            return 'Connection error'
        else:
            return "OK"

    _connect_to('test_data_db', progress, _connect_to_db, logger)

    def _connect_to_gaia(logger):
        try:
            INSTRUMENTS['gaia'] = gaiaclient.Client("http://localhost:1234")

        except requests.exceptions.ConnectionError as e:
            return "Connection error"
        else:
            return "OK"

    _connect_to('gaia', progress, _connect_to_gaia, logger)


def _connect_to(name, progress, connector, logger):
    def get_status():
        try:
            progress.set_instrument_status(name, "Trying to connect...")

            return connector(logger)
        except Exception as e:
            logger.exception(f'Failed to connect to {name}', e)
            return 'error'

    if progress.instrument_status[name] != "MagicMock":
        if progress.instrument_status[name] != "OK":

            status = get_status()

            while status != 'OK':

                time.sleep(1)
                # Set status after sleep so that the user sees "Trying to connect"
                # This is handy is connector() doesn't give meaningful response
                # then the user still sees the "trying to connect" message
                progress.set_instrument_status(name, status)
                status = get_status()

            progress.set_instrument_status(name, status)
