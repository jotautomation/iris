LIMITS = {}

LIMITS["second"] = {
    "Measurement1": lambda measurement: 90 < measurement < 100,
    "Measurement2": lambda measurement: measurement == [123, 456, 1, 3],
    # Measurement result may be something else than boolean
    # Boolean True is only result that is reported as "Pass",
    # All other results are considered "Fail"
    "Measurement3": lambda measurement: True if measurement < 100 else "ABC",
    "Measurement4": lambda measurement: measurement.contains("123abc"),
    "Measurement5": lambda measurement: complicated_limit_definition(measurement),
}

LIMITS["first"] = {
    "Measurement1": lambda measurement: 90 < measurement < 100,
    "Measurement2": lambda measurement: measurement == [123, 456, 1, 3],
    "Measurement3": lambda measurement: 90 <= measurement <= 100,
    "Measurement4": lambda measurement: measurement.contains("123abc"),
    "Measurement5": lambda measurement: complicated_limit_definition(measurement),
}


def complicated_limit_definition(measurement):
    # Must return true/false
    pass
