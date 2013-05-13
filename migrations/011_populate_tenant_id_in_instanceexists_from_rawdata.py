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


def add_past_exists(instance_tenant_id_maps):
    update_count = 0
    for map in instance_tenant_id_maps:
        update_count += models.InstanceExists.objects.filter(instance=map['instance']).update(tenant=map['tenant'])
    print "updated %s rows" % update_count

distinct_exists_instances = models.InstanceExists.objects.all().values('instance').distinct()
instance_tenant_id_maps = models.RawData.objects.filter(instance__in=distinct_exists_instances).distinct().values('instance', 'tenant')
add_past_exists(instance_tenant_id_maps)