import datetime


def get_statistics(db_client, local_mongodb_name):
    return {
        'yield': get_yield(db_client, local_mongodb_name),
        'uph': get_uph(db_client, local_mongodb_name),
    }


def get_yield(db_client, local_mongodb_name):

    pass_count = (
        db_client[local_mongodb_name]
        .test_reports.find(
            {
                'start_time': {'$gt': datetime.datetime.now() - datetime.timedelta(weeks=4)},
                'overallResult': True,
            }
        )
        .count()
    )
    all_count = (
        db_client[local_mongodb_name]
        .test_reports.find(
            {'start_time': {'$gt': datetime.datetime.now() - datetime.timedelta(weeks=4)}}
        )
        .count()
    )

    if all_count == 0:
        return 0

    return pass_count / all_count * 100


def get_uph(db_client, local_mongodb_name):
    return (
        db_client[local_mongodb_name]
        .test_reports.find(
            {'start_time': {'$gt': datetime.datetime.now() - datetime.timedelta(hours=1)}}
        )
        .count()
    )
