#!usr/bin/env python

import csv
import argparse
import time
import sys
import os
import MySQLdb
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


class Args(object):
    def __init__(self, filepath=None, host=None, user=None, passwd=None, port=3306, db='stacktach'):
        self.csv_filepath = filepath
        self.db_host = host
        self.db_user = user
        self.db_passwd = passwd
        self.db_port = port
        self.db_name = db


def get_instance_uuids_from_csv(args_obj):
    uuid_list = list()
    with open(args_obj.csv_filepath, 'r') as csv_fp:
        csv_reader = csv.reader(csv_fp, delimiter=',', quotechar='"')
        for single_uuid_list in csv_reader:
            if single_uuid_list:
                uuid_list.append(single_uuid_list[0])
    return uuid_list


def update_instances_as_deleted(arg_obj, uuid_list):
    db_connector = MySQLdb.connect(host=arg_obj.db_host, db=arg_obj.db_name, user=arg_obj.db_user,
                                   passwd=arg_obj.db_passwd, port=arg_obj.db_port)
    db_cursor = db_connector.cursor()
    db_entry_tuple_list = list()
    for uuid in uuid_list:
        check_sql = "SELECT * FROM `stacktach_instancedeletes` WHERE `instance`=%s"
        check_sql_args = (uuid,)
        # Insert only if an entry with the same instance doesnt exist already in the stacktach_instacedeletes table
        if not db_cursor.execute(check_sql, check_sql_args):
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
                deleted_at = None
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


def get_commandline_args():
    arg_parser = argparse.ArgumentParser(description="Enter command line parameters.")
    arg_parser.add_argument("--csv_filepath", type=str, help="Enter your csv file with instance UUIDs here.",
                            required=True)
    arg_parser.add_argument("--db_host", type=str, help="The stacktach DB host.", required=True)
    arg_parser.add_argument("--db_user", type=str, help="The stacktach DB username.", required=True)
    arg_parser.add_argument("--db_passwd", type=str, help="The stacktach DB user's password.", required=True)
    arg_parser.add_argument("--db_port", type=int, help="The stacktach DB port. Default is 3306", required=False)
    arg_parser.add_argument("--db_name", type=str, help="The stacktach database name. Default is stacktach.",
                            required=False)
    parser_obj = arg_parser.parse_args()

    db_port_arg = None
    db_name_arg = None
    if parser_obj.db_port:
        db_port_arg = parser_obj.db_port
    if parser_obj.db_name:
        db_name_arg = parser_obj.db_name

    # Don't pass the port and db name if they are not found in the command line parameters
    if not (db_port_arg or db_name_arg):
        args_obj = Args(parser_obj.csv_filepath, parser_obj.db_host, parser_obj.db_user, parser_obj.db_passwd)
    else:
        args_obj = Args(parser_obj.csv_filepath, parser_obj.db_host, parser_obj.db_user, parser_obj.db_passwd,
                        db_port_arg, db_name_arg)
    return args_obj


if __name__ == '__main__':
    arg_obj = get_commandline_args()
    instance_uuid_list = get_instance_uuids_from_csv(arg_obj)
    update_instances_as_deleted(arg_obj, instance_uuid_list)
    print "SCRIPT RUN SUCCESSFULLY"
