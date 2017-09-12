#!usr/bin/env python

from stacktach.utils import get_local_mysqldb_connection
import csv
import argparse
import time
import sys
import os
sys.path.append(os.environ.get('STACKTACH_INSTALL_DIR', '/stacktach'))

"""
    The purpose of this script to clean the DB from instances for whom NOVA doesnt send an 'exists' notification.
    Those instances have probably been deleted in the NOVA DB.
    
    The script takes a CSV file as the input. The CSV format example is :
    
        7e5e7f09-66dc-49e8-8e3e-58b97918a8dc
        58a7040c-5cf5-4f09-b6df-0a9cba975d5b
        688068ee-a446-4e78-8677-013d2378ae6e
        93890be5-bd2b-4c0d-8e38-a79841fdd546
        57258b0a-54d2-423a-9f79-7b0ea4bf140a

    To run the script :
    
        python stacktach_db_cleaner.py --csv_filepath <path of the csv file that contains the instance ids>
"""


def get_instance_uuids_from_csv(csv_path):
    uuid_list = list()
    with open(csv_path, 'r') as csv_fp:
        csv_reader = csv.reader(csv_fp, delimiter=',', quotechar='"')
        for single_uuid_list in csv_reader:
            if single_uuid_list:
                uuid_list.append(single_uuid_list[0])
    return uuid_list


def update_instances_as_deleted(uuid_list):
    db_connector = get_local_mysqldb_connection()
    db_cursor = db_connector.cursor()

    db_entry_tuple_list = list()
    for uuid in uuid_list:
        # Take the launched_at data from stacktach_instanceusage table
        sql = "SELECT `instance`, `launched_at` FROM `stacktach_instanceusage` WHERE `instance` = %s LIMIT 1"
        sql_args = (uuid, )
        if db_cursor.execute(sql, sql_args):
            result = db_cursor.fetchone()
            instance_id, launched_at = result
            if not launched_at:
                launched_at = time.time()

            # Getting deleted_at from stacktach_instanceexists table
            # If there is no deleted_at value, use the current timestamp.
            sql = "SELECT `deleted_at` FROM stacktach_instanceexists WHERE `instance` = %s LIMIT 1"
            sql_args = (uuid,)
            if db_cursor.execute(sql, sql_args):
                (deleted_at,) = db_cursor.fetchone()
            if not deleted_at:
                    deleted_at = time.time()
            db_entry_tuple_list.append((instance_id, launched_at, deleted_at))
        else:
            print "***** ERROR!!! Instance {} not found in the stacktach DB. *****".format(uuid)

    sql = "INSERT INTO `stacktach_instancedeletes` (`instance`, `launched_at`, `deleted_at`) values (%s, %s, %s)"
    try:
        db_cursor.executemany(sql, db_entry_tuple_list)
    except Exception, e:
        print "ERROR!!! - ", str(e)
        db_connector.rollback()
    else:
        db_connector.commit()


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--csv_filepath", type=str, help="Enter your csv file with instance UUIDs here.")
    args = arg_parser.parse_args()
    instance_uuid_list = get_instance_uuids_from_csv(args.csv_filepath)
    update_instances_as_deleted(instance_uuid_list)
    print "SCRIPT RUN SUCCESSFULLY"
