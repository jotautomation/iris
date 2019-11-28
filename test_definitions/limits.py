LIMITS = {}

LIMITS['second'] = {
    'Measurement1': lambda result: 90 < result < 100,
    'Measurement2': lambda result: result == [123, 456, 1, 3],
    'Measurement3': lambda result: 90 <= result <= 100,
    'Measurement4': lambda result: result.contains('123abc'),
    'Measurement5': lambda result: complicated_limit_definition(result)
    }

LIMITS['first'] = {
    'Voltage': lambda result: 90 < result < 100,
    }

LIMITS['third'] = {
    'Voltage': lambda result: 90 < result < 100,
    }


def complicated_limit_definition(result):
    # Must return true/false
    pass
