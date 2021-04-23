LIMITS = {}

LIMITS["Second"] = {
    "Measurement1": {
        "limit": lambda measurement: 90 < measurement < 100,
        "unit": "dB",
        "report_limit": "Overriden representation of limit to be written to the report.",
    },
    "Measurement2": {"limit": lambda measurement: measurement == [123, 456, 1, 3]},
    # Measurement result may be something else than boolean
    # Boolean True is only result that is reported as "Pass",
    # All other results are considered "Fail"
    "Measurement3": {"limit": lambda measurement: True if measurement < 100 else "ABC"},
    "Measurement4": {"limit": lambda measurement: measurement.contains("123abc")},
    "Measurement5": {"limit": lambda measurement: complicated_limit_definition(measurement)},
}

LIMITS["First"] = {
    "Measurement1": {"limit": lambda measurement: 90 < measurement < 100},
    "Measurement2": {"limit": lambda measurement: measurement == [123, 456, 1, 3]},
}


def complicated_limit_definition(measurement):
    # Must return true/false
    pass
