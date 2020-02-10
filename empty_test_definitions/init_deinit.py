"""Initializations and deinitializations"""


def boot_up():
    print("Executing initialization")


def finalize_test(overallresult, duts, instruments):
    print("Testing ready")


def prepare_test():
    print("Preparing to test")
    import uuid

    return {
        "left": {'sn': str(uuid.uuid4())},
        "right": {'sn': str(uuid.uuid4())},
        "middle": {'sn': str(uuid.uuid4())},
    }


def shutdown():
    print("Shutdown")
