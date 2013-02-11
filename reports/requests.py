import datetime
import json
import sys

sys.path.append("/stacktach")

from stacktach import datetime_to_decimal as dt
from stacktach import image_type
from stacktach import models


if __name__ != '__main__':
    sys.exit(1)

hours = 0
length = 24

now = datetime.datetime.utcnow()
start = now - datetime.timedelta(hours=hours+length)
end = now - datetime.timedelta(hours=hours)

dnow = dt.dt_to_decimal(now)
dstart = dt.dt_to_decimal(start)
dend = dt.dt_to_decimal(end)

codes = {}

# Get all the instances that have changed in the last N hours ...
updates = models.RawData.objects.filter(event='compute.instance.update',
                                        when__gt=dstart, when__lte=dend)\
                                 .values('instance').distinct()

expiry = 60 * 60  # 1 hour
cmds = ['create', 'rebuild', 'rescue', 'resize', 'snapshot']

failures = {}
tenant_issues = {}

for uuid_dict in updates:
    uuid = uuid_dict['instance']

    # All the unique Request ID's for this instance during that timespan.
    reqs = models.RawData.objects.filter(instance=uuid,
                                         when__gt=dstart, when__lte=dend) \
                                 .values('request_id').distinct()


    for req_dict in reqs:
        report = False
        req = req_dict['request_id']
        raws = models.RawData.objects.filter(request_id=req)\
                                     .exclude(event='compute.instance.exists')\
                                     .order_by('when')

        start = None
        err = None

        operation = None
        platform = 0
        tenant = 0
        dump = False

        for raw in raws:
            if not start:
                start = raw.when
            if 'error' in raw.routing_key:
                err = raw
                report = True

            if raw.tenant:
                if tenant > 0 and raw.tenant != tenant:
                    print "Conflicting tenant ID", raw.tenant, tenant
                tenant = raw.tenant

            for cmd in cmds:
                if cmd in raw.event:
                    operation = cmd
                    break

            if raw.image_type > 0:
                platform = raw.image_type

            if dump:
                print "    %s %s T:%s %s %s %s %s %s"\
                        % (raw.id, raw.routing_key, raw.tenant, 
                           raw.service, raw.host, raw.deployment.name, 
                           raw.event, dt.dt_from_decimal(raw.when))
                if raw.event == 'compute.instance.update':
                    print "         State: %s->%s, Task %s->%s" % \
                        (raw.old_state, raw.state, raw.old_task, raw.task)

        if not start:
            continue

        end = raw.when
        diff = end - start

        if diff > 3600:
            report = True

        if report:
            print "------", uuid, "----------"
            print "    Req:", req
            print "    Duration: %.2f minutes" % (diff / 60)
            print "    Operation:", operation
            print "    Platform:", image_type.readable(platform)
            key = (operation, platform)
            failures[key] = failures.get(key, 0) + 1
            tenant_issues[tenant] = tenant_issues.get(tenant, 0) + 1

            if err:
                queue, body = json.loads(err.json)
                payload = body['payload']
                print "Error. EventID: %s, Tenant %s, Service %s, Host %s, "\
                      "Deployment %s, Event %s, When %s"\
                    % (err.id, err.tenant, err.service, err.host, err.deployment.name, 
                       err.event, dt.dt_from_decimal(err.when))
                exc = payload.get('exception')
                if exc:
                    print exc
                    code = exc.get('kwargs', {}).get('code')
                    if code:
                        codes[code] = codes.get(code, 0) + 1

print "-- Failures by operation by platform --"
for failure, count in failures.iteritems():
    operation, platform = failure
    readable = image_type.readable(platform)
    text = "n/a"
    if readable:
        text = ", ".join(readable)
    print "%s on %s = %d" % (operation, text, count)

print "-- Errors by Tenant --"
for tenant, count in tenant_issues.iteritems():
    print "T %s = %d" % (tenant, count)

print "-- Return code counts --"
for k, v in codes.iteritems():
    print k, v
