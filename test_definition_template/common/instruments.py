"""Instrument definitions"""

import gaiaclient


# This definition will also run when new test sequence is created.
# Thus it is not good idea to connect to instrument here
# connect at instrument_initialization instead.

INSTRUMENTS = {"G5": None}


def instrument_initialization():
    """Connect and initialize instruments"""
    INSTRUMENTS["G5"] = gaiaclient.Client("http://localhost:1234")
