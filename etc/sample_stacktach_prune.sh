#!/bin/bash
# Example script to prune the Stacktach RawData table

# The following is one way you could keep your RawData table from growing
# very large -- keep only the last N days worth of data, N being a number
# convenient to your installation.

# Full path to where you have deployed the Stacktach app
PATH_TO_ST='/path/to/stacktach'

# Let us say we want to keep only 90 days' worth of RawData.
# 90 days = 90 * (24*60*60) seconds = 7776000 seconds.
KEEP_RAWDATA_DAYS=90
KEEP_RAWDATA_SECS=$((KEEP_RAWDATA_DAYS*24*60*60))

# Source the stacktach_config.sh script to populate the 
# STACKTACH_DB_* variables among other things, and do the deed.
cd ${PATH_TO_ST} && \
. ${PATH_TO_ST}/etc/stacktach_config.sh && \
python manage.py dbshell <<EOF \
     > /tmp/stacktach_prune.stdout \
    2> /tmp/stacktach_prune.stderr

DELETE FROM stacktach_rawdata
WHERE stacktach_rawdata.when < (UNIX_TIMESTAMP(NOW())-${KEEP_RAWDATA_SECS});

EOF
