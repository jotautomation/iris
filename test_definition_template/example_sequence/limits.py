LIMITS = {}

LIMITS["second"] = {
    "Measurement1": lambda measurement: 90 < measurement < 100,
    "Measurement2": lambda measurement: measurement == [123, 456, 1, 3],
    "Measurement3": lambda measurement: 90 <= measurement <= 100,
    "Measurement4": lambda measurement: measurement.contains("123abc"),
    "Measurement5": lambda measurement: complicated_limit_definition(measurement),
}

LIMITS["first"] = {"Voltage": lambda measurement: 90 < measurement < 100}

LIMITS["third"] = {"Voltage": lambda measurement: 90 < measurement < 100}


def complicated_limit_definition(measurement):
    # Must return true/false
    pass
