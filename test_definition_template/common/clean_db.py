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
        pathlib.Path(_file['file_path']).unlink()

    # Delete file entries on database
    db_client[local_mongodb_name].file_attachments.delete_many(file_delete_filter)
