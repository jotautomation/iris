"""Instrument definitions"""

import gaiaclient


# This definition will also run when new test sequence is created.
# Thus it is not good idea to connect to instrument here
# connect at instrument_initialization instead.

INSTRUMENTS = {"gaia": None}


def instrument_initialization():
    """Connect and initialize instruments"""
    INSTRUMENTS["gaia"] = gaiaclient.Client("http://localhost:1234")
