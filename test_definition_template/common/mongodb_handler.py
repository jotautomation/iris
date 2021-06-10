import datetime
import pathlib
import logging
from pymongo import MongoClient


class DatabaseHandler:
    def __init__(self, db_connection_string, db_name):
        self.db_client = MongoClient(db_connection_string, serverSelectionTimeoutMS=10000)
        self.db_name = db_name
        self.logger = logging.getLogger("DatabaseHandler")

    def get_media_file_path(self, file_name):
        return self.db_client[self.db_name].file_attachments.find_one({'name': file_name})[
            'file_path'
        ]

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
                self.logger.warning(
                    "Trying to delete non-existent file attachment: %s", _file['file_path']
                )

        # Delete file entries on database
        self.db_client[self.db_name].file_attachments.delete_many(file_delete_filter)

        # Delete old test reports
        self.db_client[self.db_name].test_reports.delete_many(
            {'start_time': {'$lt': datetime.datetime.now() - datetime.timedelta(weeks=4)}}
        )

    def get_search_bar_items(self):
        return {
            'searchBarItems': [
                {
                    'name': 'limit_N',
                    'placeholder_txt': "Number of items to get",
                    'label': 'Number of items',
                    'type': 'textbox',
                },
                {
                    'name': 'limit_hours',
                    'placeholder_txt': "Hours",
                    'label': 'Hours',
                    'type': 'textbox',
                },
                {
                    'name': 'dut_identifier',
                    'placeholder_txt': "ABCD-1234",
                    'label': 'DUT ID',
                    'type': 'textbox',
                },
                {
                    'name': 'only_fails',
                    'placeholder_txt': "",
                    'label': 'Only Fails',
                    'type': 'checkbox',
                },
            ]
        }

    def search_db(self, search_args):

        db_filter = {}
        if 'limit_hours' in search_args:
            db_filter.update(
                {
                    'start_time': {
                        '$gt': datetime.datetime.now()
                        - datetime.timedelta(hours=search_args['limit_hours'])
                    }
                }
            )

        if 'dut_identifier' in search_args:
            db_filter.update({'serialnumber': search_args['dut_identifier']})

        if 'only_fails' in search_args:
            db_filter.update({'result': False})

        limit = 500

        if 'limit_N' in search_args:
            limit = search_args['limit_N']

        reps = (
            self.db_client[self.db_name]
            .test_reports.find(db_filter)
            .sort('start_time')
            .limit(limit)
        )

        return {'test_runs': list(reps)}

    def store_test_data_file_to_db(self, **kwargs):
        self.db_client[self.db_name].file_attachments.insert_one({**kwargs})
