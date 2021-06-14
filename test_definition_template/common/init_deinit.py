"""Initializations and deinitializations"""


def boot_up(instruments, logger):
    logger.info("Executing initialization")


def finalize_test(overallresult, duts, instruments, logger):
    logger.info("Testing ready. Release DUT(s) on Gaia")

    if overallresult:
        instruments['gaia'].state_triggers['ReleasePass']()
    else:
        instruments['gaia'].state_triggers['ReleaseFail']()

    instruments['gaia'].wait_not_ready()


def prepare_test(instruments, logger, dut_sn_values, sequence_name):
    logger.info("Waiting G5 to get ready for next (or first) test run")
    instruments['gaia'].wait_ready()


def indentify_DUTs(instruments, logger):
    import uuid

    # Figure out DUT sn (probably with code reader), find out what
    # sequence must be used with the DUT type.
    # Return DUTs and sequence name.
    # Sequence name is the directory name at test_definitions
    # Here we use testA as an example. Thus you must create
    # the sequence with 'python super_simple_test_runner.py -c testA'
    return (
        # DUTs
        {
            "1": {'sn': str(uuid.uuid4())},
            "2": {'sn': str(uuid.uuid4())},
            "3": {'sn': str(uuid.uuid4())},
        },
        # Test sequence
        "testA",
        # Operator info
        {"name": "John Doe"},
    )


def shutdown(instruments, logger):
    logger.info("Shutdown")
