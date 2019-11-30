"""Initializations and deinitializations"""


def boot_up():
    print("Executing initialization")


def finalize_test(overallresult, dut, instruments):
    print("Testing ready")


def prepare_test():
    print("Preparing to test")
    import uuid

    return str(uuid.uuid4())


def shutdown():
    print("Shutdown")
