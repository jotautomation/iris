import datetime
import pathlib


def clean_db(db_client, local_mongodb_name):
    # Get files older than one week
    file_delete_filter = {
        'added': {'$lt': datetime.datetime.now() - datetime.timedelta(weeks=1)}
    }
    old_files = db_client[local_mongodb_name].file_attachments.find(file_delete_filter)

    # Delete files on HDD
    for _file in old_files:
        try:
            pathlib.Path(_file['file_path']).unlink()
        except FileNotFoundError as err:
            print("Trying to delete non-existent file attachment: " + _file['file_path'])

    # Delete file entries on database
    db_client[local_mongodb_name].file_attachments.delete_many(file_delete_filter)

    # Delete old test reports
    db_client[local_mongodb_name].test_reports.delete_many(
        {'start_time': {'$lt': datetime.datetime.now() - datetime.timedelta(weeks=4)}}
    )
