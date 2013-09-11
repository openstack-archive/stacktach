# Copyright (c) 2013 - Rackspace Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import os
import sys

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from stacktach import models

if __name__ != '__main__':
    sys.exit(1)

seed_usage = models.InstanceUsage.objects.filter(request_id=None)
deleted_instances = models.InstanceDeletes.objects.values('instance').distinct()

deleted = set()
for instance in deleted_instances:
    deleted.add(instance['instance'])

fixed = 0

for usage in seed_usage:
    if usage.instance not in deleted and usage.launched_at is not None and \
            usage.launched_at is not '':
        filters = {
            'instance': usage.instance,
            'launched_at__gte': int(usage.launched_at),
            'launched_at__lt': int(usage.launched_at) + 1,
            'status': models.InstanceExists.VERIFIED
        }
        exists = models.InstanceExists.objects.filter(**filters)
        if exists.count() > 0:
            fixed += 1
            usage.os_architecture = exists[0].os_architecture
            usage.os_distro = exists[0].os_distro
            usage.os_version = exists[0].os_version
            usage.rax_options = exists[0].rax_options
            usage.save()
        else:
            print "Couldn't find verified exists for instance %s" % usage.instance

print "Populated %s usage records" % fixed
