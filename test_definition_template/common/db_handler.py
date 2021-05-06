import datetime
import pathlib
from pymongo import MongoClient


class DatabaseHandler:
    def __init__(self, db_connection_string, db_name):
        self.db_client = MongoClient(db_connection_string)
        self.db_name = db_name

    def get_statistics(self):
        return {
            'yield': self.get_yield(),
            'uph': self.get_uph(),
        }

    def get_yield(self):

        pass_count = (
            self.db_client[self.db_name]
            .test_reports.find(
                {
                    'start_time': {'$gt': datetime.datetime.now() - datetime.timedelta(weeks=4)},
                    'overallResult': True,
                }
            )
            .count()
        )
        all_count = (
            self.db_client[self.db_name]
            .test_reports.find(
                {'start_time': {'$gt': datetime.datetime.now() - datetime.timedelta(weeks=4)}}
            )
            .count()
        )

        if all_count == 0:
            return 0

        return pass_count / all_count * 100

    def get_uph(self):
        return (
            self.db_client[self.db_name]
            .test_reports.find(
                {'start_time': {'$gt': datetime.datetime.now() - datetime.timedelta(hours=1)}}
            )
            .count()
        )

    def clean_db(self):
        # Get files older than one week
        file_delete_filter = {
            'added': {'$lt': datetime.datetime.now() - datetime.timedelta(weeks=1)}
        }
        old_files = self.db_client[self.db_name].file_attachments.find(file_delete_filter)

        # Delete files on HDD
        for _file in old_files:
            try:
                pathlib.Path(_file['file_path']).unlink()
            except FileNotFoundError:
                print("Trying to delete non-existent file attachment: " + _file['file_path'])

        # Delete file entries on database
        self.db_client[self.db_name].file_attachments.delete_many(file_delete_filter)

        # Delete old test reports
        self.db_client[self.db_name].test_reports.delete_many(
            {'start_time': {'$lt': datetime.datetime.now() - datetime.timedelta(weeks=4)}}
        )

    def search_db(self, search_args):

        reps = list(self.db_client[self.db_name].test_reports.find({}))

        return {'test_runs': reps}
