"""Initializations and deinitializations"""


def boot_up():
    print("Executing initialization")


def finalize_test(overallresult, duts, instruments):
    print("Testing ready")


def prepare_test(instruments):
    print("Waiting G5 to get ready for next (or first) test run")
    instruments['G5'].wait_ready()
    import uuid

    # Figure out DUT sn (probably with code reader), find out what
    # sequence must be used with the DUT type.
    # Return DUTs and sequence name.
    # Sequence name is the directory name at test_definitions
    # Here we use testA as an example. Thus you must create
    # the sequence with 'python super_simple_test_runner.py -c testA'
    return ({
        "left": {'sn': str(uuid.uuid4())},
        "right": {'sn': str(uuid.uuid4())},
        "middle": {'sn': str(uuid.uuid4())},
    }, "testA")


def shutdown():
    print("Shutdown")
