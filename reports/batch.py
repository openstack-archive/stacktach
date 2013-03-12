# This is a one-time utility script for backfilling reports.
# Be sure to set up your DJANGO_SETTINGS_MODULE env var first.

import datetime
import subprocess

start_date =  datetime.date(2013, 2, 17)

today = datetime.datetime.now().date()
target = today - datetime.timedelta(days=30)

done = today - start_date
days = done.days

while start_date != target:
    for region in ["dfw", "lon", "ord"]:
        cmd = "python pretty.py --utcdate %s --region %s  --store --percentile 97" % (start_date, region)
        print cmd
        subprocess.call(cmd, shell=True)

    start_date = start_date - datetime.timedelta(days=1)
