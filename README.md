# StackTach

StackTach is a debugging / monitoring utility for OpenStack ([Open]StackTach[ometer]). StackTach can work with multiple datacenters including multi-cell deployments.

## Overview
OpenStack has the ability to publish notifications to a RabbitMQ exchange as they occur. So, rather than pouring through reams of logs across multiple servers, you can now watch requests travel through the system from a single location.

A detailed description of the notifications published by OpenStack [is available here](http://wiki.openstack.org/SystemUsageData)

StackTach has three primary components:
1. The Worker daemon. Consumes the notifications from the Rabbit queue and writes it to a SQL database.
1. The Web UI, which is a Django application. Provides a real-time display of notifications as they are consumed by the worker. Also provides for point-and-click analysis of the events for following related events.
1. Stacky, the command line tool. Operator and Admins aren't big fans of web interfaces. StackTach also exposes a REST interface which Stacky can use to provide output suitable for tail/grep post-processing.

## Installing StackTach

### The "Hurry Up" Install Guide
1. Create a database for StackTach to use. By default, StackTach assumes MySql, but you can modify the settings.py file to others.
1. Install django and the other required libraries listed in `./etc/pip-requires.txt` (I hope I got 'em all)
1. Clone this repo
1. Copy and configure the config files in `./etc` (see below for details)
1. Create the necessary database tables (python manage.py syncdb) You don't need an administrator account since there are no user profiles used.
1. Configure OpenStack to publish Notifications back into RabbitMQ (see below)
1. Restart the OpenStack services.
1. Run the Worker to start consuming messages. (see below)
1. Run the web server (python manage.py runserver)
1. Point your browser to `http://127.0.0.1:8000` (the default server location)
1. Click on stuff, see what happens. You can't hurt anything, it's all read-only.

Of course, this is only suitable for playing around. If you want to get serious about deploying StackTach you should set up a proper webserver and database on standalone servers. There is a lot of data that gets collected by StackTach (depending on your deployment size) ... be warned. Keep an eye on DB size.

#### The Config Files
There are two config files for StackTach. The first one tells us where the second one is. A sample of these two files is in `./etc/sample_*`

The `sample_stacktach_config.sh` shell script defines the necessary environment variables StackTach needs. Most of these are just information about the database (assuming MySql) but some are a little different.

`STACKTACH_INSTALL_DIR` should point to where StackTach is running out of. In most cases this will be your repo directory, but it could be elsewhere if your going for a proper deployment.
The StackTach worker needs to know which RabbitMQ servers to listen to. This information is stored in the deployment file. `STACKTACH_DEPLOYMENTS_FILE` should point to this json file. To learn more about the deployments file, see further down.

Finally, `DJANGO_SETTINGS_MODULE` tells Django where to get its configuration from. This should point to the `setting.py` file. You shouldn't have to do much with the `settings.py` file and most of what it needs is in these environment variables.

The `sample_stacktach_worker_config.json` file tells StackTach where each of the RabbitMQ servers are that it needs to get events from. In most cases you'll only have one entry in this file, but for large multi-cell deployments, this file can get pretty large. It's also handy for setting up one StackTach for each developer environment.

The file is in json format and the main configuration is under the `"deployments"` key, which should contain a list of deployment dictionaries. 

A blank worker config file would look like this:
```
{"deployments": [] }
```

But that's not much fun. A deployment entry would look like this:

```
{"deployments": [
     {
         "name": "east_coast.prod.cell1",
         "rabbit_host": "10.0.1.1",
         "rabbit_port": 5672,
         "rabbit_userid": "rabbit",
         "rabbit_password": "rabbit",
         "rabbit_virtual_host": "/"
     }
]}
```

where, *name* is whatever you want to call your deployment, and *rabbit_<>* are the connectivity details for your rabbit server. It should be the same information in your `nova.conf` file that OpenStack is using. Note, json has no concept of comments, so using `#`, `//` or `/* */` as a comment won't work.

You can add as many deployments as you like. 

#### Starting the Worker

`./worker/start_workers.py` will spawn a worker.py process for each deployment defined. Each worker will consume from a single Rabbit queue.


#### Configuring Nova to generate Notifications

`--notification_driver=nova.openstack.common.notifier.rabbit_notifier`
`--notification_topics=monitor`

This will tell OpenStack to publish notifications to a Rabbit exchange starting with `monitor.*` ... this may result in `monitor.info`, `monitor.error`, etc.

You'll need to restart Nova once these changes are made.

### Next Steps

Once you have this working well, you should download and install Stacky and play with the command line tool.


