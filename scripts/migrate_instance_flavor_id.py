#!/usr/bin/python
import os
import sys

sys.path.append(os.environ.get('STACKTACH_INSTALL_DIR', '/stacktach'))

import csv
from stacktach import models


def migrate_forwards(csv_file_path):
    with open(csv_file_path, "r") as f:
        for old_flavor, new_flavor in csv.reader(f):
            models.InstanceUsage.objects.filter(
                instance_type_id=old_flavor, instance_flavor_id=None)\
                .update(instance_flavor_id=new_flavor)
            models.InstanceExists.objects.filter(
                instance_type_id=old_flavor, instance_flavor_id=None)\
                .update(instance_flavor_id=new_flavor)
            models.InstanceReconcile.objects.filter(
                instance_type_id=old_flavor, instance_flavor_id=None)\
                .update(instance_flavor_id=new_flavor)


def migrate_backwards(csv_file_path):
    with open(csv_file_path, "r") as f:
        for old_flavor, new_flavor in csv.reader(f):
            models.InstanceUsage.objects.filter(instance_flavor_id=new_flavor)\
                .update(instance_flavor_id=None)
            models.InstanceExists.objects.filter(instance_flavor_id=new_flavor)\
                .update(instance_flavor_id=None)
            models.InstanceReconcile.objects.filter(
                instance_flavor_id=new_flavor)\
                .update(instance_flavor_id=None)

if __name__ == '__main__':
    try:
        csv_file_path = sys.argv[1]
        action = sys.argv[2]
    except Exception:
        print ("""usage: migrate_flavor_id.py <csv_file_absolute_path>"""
                """ <forwards | backwards>"""
                """\n\nThe input file for this script can be generated"""
                """ using the following SQL query:"""
                """\nSELECT id, flavorid"""
                """\nINTO OUTFILE '/tmp/flavors.csv'"""
                """\nFIELDS TERMINATED BY ','"""
                """\nENCLOSED BY '"'"""
                """\nLINES TERMINATED BY '\\n'"""
                """\nFROM instance_types;""")
        sys.exit(2)

    if action == "forwards":
        migrate_forwards(csv_file_path)
    elif action == "backwards":
        migrate_backwards(csv_file_path)
