import json
from test_definitions import *
import test_report_writer

boot_up()

TESTS = [t for t in TESTS if t not in SKIP]

run = True

while run:

    results = {}

    try:
        prepare_test()

        for test_case in TESTS:
            test_instance = globals()[test_case]()
            test_instance.test(INSTRUMENTS)
            results[test_case] = test_instance.result_handler(LIMITS[test_case])

        finalize_test()

    except Error as e:
        # TODO: write error to report
        raise
    else:
        pass
    finally:
        pass

    test_report_writer.create_report(json.dumps(results), 'result.html')

    run = False

shutdown()