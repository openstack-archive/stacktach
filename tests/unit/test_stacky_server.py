# Copyright 2012 - Rackspace Inc.

import datetime
import json
import unittest

import mox

from stacktach import datetime_to_decimal as dt
from stacktach import models
from stacktach import stacky_server
import utils
from utils import INSTANCE_ID_1
from utils import INSTANCE_ID_2
from utils import REQUEST_ID_1


class StackyServerTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self.mox.StubOutWithMock(models, 'RawData', use_mock_anything=True)
        models.RawData.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'Deployment', use_mock_anything=True)
        models.Deployment.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'Lifecycle', use_mock_anything=True)
        models.Lifecycle.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'Timing', use_mock_anything=True)
        models.Timing.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'RequestTracker',
                                 use_mock_anything=True)
        models.RequestTracker.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'InstanceUsage',
                                 use_mock_anything=True)
        models.InstanceUsage.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'InstanceDeletes',
                                 use_mock_anything=True)
        models.InstanceDeletes.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'InstanceExists',
                                 use_mock_anything=True)
        models.InstanceExists.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'JsonReport', use_mock_anything=True)
        models.JsonReport.objects = self.mox.CreateMockAnything()

    def tearDown(self):
        self.mox.UnsetStubs()

    def _create_raw(self):
        raw = self.mox.CreateMockAnything()
        raw.when = utils.decimal_utc()
        raw.instance = INSTANCE_ID_1
        raw.id = 1
        raw.routing_key = 'monitor.info'
        raw.deployment = self.mox.CreateMockAnything()
        raw.deployment.id = 1
        raw.deployment.name = 'deployment'
        raw.event = 'test.start'
        raw.host = 'example.com'
        raw.state = 'active'
        raw.old_state = None
        raw.old_task = None
        raw.publisher = "api.example.com"
        raw.service = 'api'
        raw.host = 'example.com'
        raw.request_id = REQUEST_ID_1
        raw.json = '{"key": "value"}'
        return raw

    def test_get_event_names(self):
        result = self.mox.CreateMockAnything()
        models.RawData.objects.values('event').AndReturn(result)
        result.distinct().AndReturn(result)
        self.mox.ReplayAll()

        event_names = stacky_server.get_event_names()
        self.assertEqual(event_names, result)

        self.mox.VerifyAll()

    def test_get_host_names(self):
        result = self.mox.CreateMockAnything()
        models.RawData.objects.values('host').AndReturn(result)
        result.distinct().AndReturn(result)
        self.mox.ReplayAll()

        event_names = stacky_server.get_host_names()
        self.assertEqual(event_names, result)

        self.mox.VerifyAll()

    def test_get_deployments(self):
        result = self.mox.CreateMockAnything()
        models.Deployment.objects.all().AndReturn(result)
        result.order_by('name').AndReturn(result)
        self.mox.ReplayAll()

        event_names = stacky_server.get_deployments()
        self.assertEqual(event_names, result)

        self.mox.VerifyAll()

    def test_get_timings_for_uuid_start_only(self):
        lc_result = self.mox.CreateMockAnything()
        lifecycle = self.mox.CreateMockAnything()
        models.Lifecycle.objects.filter(instance=INSTANCE_ID_1)\
                                .AndReturn(lc_result)
        lc_result.__iter__().AndReturn([lifecycle].__iter__())
        t_result = self.mox.CreateMockAnything()
        timing = self.mox.CreateMockAnything()
        models.Timing.objects.filter(lifecycle=lifecycle).AndReturn(t_result)
        t_result.__iter__().AndReturn([timing].__iter__())
        timing.name = 'name'
        timing.start_raw = self.mox.CreateMockAnything()
        timing.end_raw = None
        timing.diff = None
        self.mox.ReplayAll()

        event_names = stacky_server.get_timings_for_uuid(INSTANCE_ID_1)

        self.assertEqual(len(event_names), 2)
        self.assertEqual(event_names[0], ['?', 'Event', 'Time (secs)'])
        self.assertEqual(event_names[1], ['S', 'name', 'n/a'])
        self.mox.VerifyAll()

    def test_get_timings_for_uuid_end_only(self):
        lc_result = self.mox.CreateMockAnything()
        lifecycle = self.mox.CreateMockAnything()
        models.Lifecycle.objects.filter(instance=INSTANCE_ID_1) \
                                .AndReturn(lc_result)
        lc_result.__iter__().AndReturn([lifecycle].__iter__())
        t_result = self.mox.CreateMockAnything()
        timing = self.mox.CreateMockAnything()
        models.Timing.objects.filter(lifecycle=lifecycle).AndReturn(t_result)
        t_result.__iter__().AndReturn([timing].__iter__())
        timing.name = 'name'
        timing.start_raw = None
        timing.end_raw = self.mox.CreateMockAnything()
        timing.diff = None
        self.mox.ReplayAll()

        event_names = stacky_server.get_timings_for_uuid(INSTANCE_ID_1)

        self.assertEqual(len(event_names), 2)
        self.assertEqual(event_names[0], ['?', 'Event', 'Time (secs)'])
        self.assertEqual(event_names[1], ['E', 'name', 'n/a'])
        self.mox.VerifyAll()

    def test_get_timings_for_uuid(self):
        lc_result = self.mox.CreateMockAnything()
        lifecycle = self.mox.CreateMockAnything()
        models.Lifecycle.objects.filter(instance=INSTANCE_ID_1) \
            .AndReturn(lc_result)
        lc_result.__iter__().AndReturn([lifecycle].__iter__())
        t_result = self.mox.CreateMockAnything()
        timing = self.mox.CreateMockAnything()
        models.Timing.objects.filter(lifecycle=lifecycle).AndReturn(t_result)
        t_result.__iter__().AndReturn([timing].__iter__())
        timing.name = 'name'
        timing.start_raw = self.mox.CreateMockAnything()
        timing.end_raw = self.mox.CreateMockAnything()
        timing.diff = 20
        self.mox.ReplayAll()
        event_names = stacky_server.get_timings_for_uuid(INSTANCE_ID_1)

        self.assertEqual(len(event_names), 2)
        self.assertEqual(event_names[0], ['?', 'Event', 'Time (secs)'])
        self.assertEqual(event_names[1], ['.', 'name', '0d 00:00:20'])

        self.mox.VerifyAll()

    def test_do_deployments(self):
        fake_request = self.mox.CreateMockAnything()
        deployment1 = self.mox.CreateMockAnything()
        deployment1.id = 1
        deployment1.name = 'dep1'
        deployment2 = self.mox.CreateMockAnything()
        deployment2.id = 2
        deployment2.name = 'dep2'
        deployments = [deployment1, deployment2]
        self.mox.StubOutWithMock(stacky_server, 'get_deployments')
        stacky_server.get_deployments().AndReturn(deployments)
        self.mox.ReplayAll()

        resp = stacky_server.do_deployments(fake_request)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 3)
        self.assertEqual(json_resp[0], ['#', 'Name'])
        self.assertEqual(json_resp[1], [1, 'dep1'])
        self.assertEqual(json_resp[2], [2, 'dep2'])
        self.mox.VerifyAll()

    def test_do_events(self):
        fake_request = self.mox.CreateMockAnything()
        event1 = {'event': 'some.event.1'}
        event2 = {'event': 'some.event.2'}
        events = [event1, event2]
        self.mox.StubOutWithMock(stacky_server, 'get_event_names')
        stacky_server.get_event_names().AndReturn(events)
        self.mox.ReplayAll()

        resp = stacky_server.do_events(fake_request)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 3)
        self.assertEqual(json_resp[0], ['Event Name'])
        self.assertEqual(json_resp[1], ['some.event.1'])
        self.assertEqual(json_resp[2], ['some.event.2'])
        self.mox.VerifyAll()

    def test_do_hosts(self):
        fake_request = self.mox.CreateMockAnything()
        host1 = {'host': 'www.demo.com'}
        host2 = {'host': 'www.example.com'}
        hosts = [host1, host2]
        self.mox.StubOutWithMock(stacky_server, 'get_host_names')
        stacky_server.get_host_names().AndReturn(hosts)
        self.mox.ReplayAll()

        resp = stacky_server.do_hosts(fake_request)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 3)
        self.assertEqual(json_resp[0], ['Host Name'])
        self.assertEqual(json_resp[1], ['www.demo.com'])
        self.assertEqual(json_resp[2], ['www.example.com'])
        self.mox.VerifyAll()

    def test_do_uuid(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'uuid': INSTANCE_ID_1}
        result = self.mox.CreateMockAnything()
        models.RawData.objects.select_related().AndReturn(result)
        result.filter(instance=INSTANCE_ID_1).AndReturn(result)
        result.order_by('when').AndReturn(result)
        raw = self._create_raw()
        result.__iter__().AndReturn([raw].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_uuid(fake_request)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 2)
        header = ["#", "?", "When", "Deployment", "Event", "Host",
                  "State", "State'", "Task'"]
        self.assertEqual(json_resp[0], header)
        datetime = dt.dt_from_decimal(raw.when)
        body = [1, " ", str(datetime), "deployment", "test.start",
                "example.com", "active", None, None]
        self.assertEqual(json_resp[1], body)
        self.mox.VerifyAll()

    def test_do_uuid_bad_uuid(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'uuid': "obviouslybaduuid"}
        self.mox.ReplayAll()

        resp = stacky_server.do_uuid(fake_request)

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ['Error', 'Message'])
        msg = 'obviouslybaduuid is not uuid-like'
        self.assertEqual(resp_json[1], ['Bad Request', msg])
        self.mox.VerifyAll()

    def test_do_timings_uuid_bad_uuid(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'uuid': "obviouslybaduuid"}
        self.mox.ReplayAll()

        resp = stacky_server.do_timings_uuid(fake_request)

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ['Error', 'Message'])
        msg = 'obviouslybaduuid is not uuid-like'
        self.assertEqual(resp_json[1], ['Bad Request', msg])
        self.mox.VerifyAll()

    def test_do_timings(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'name': 'test.event'}
        results = self.mox.CreateMockAnything()
        models.Timing.objects.select_related().AndReturn(results)
        results.filter(name='test.event').AndReturn(results)
        results.exclude(mox.IgnoreArg()).AndReturn(results)
        results.order_by('diff').AndReturn(results)
        timing1 = self.mox.CreateMockAnything()
        timing1.lifecycle = self.mox.CreateMockAnything()
        timing1.lifecycle.instance = INSTANCE_ID_1
        timing1.diff = 10
        timing2 = self.mox.CreateMockAnything()
        timing2.lifecycle = self.mox.CreateMockAnything()
        timing2.lifecycle.instance = INSTANCE_ID_2
        timing2.diff = 20
        results.__iter__().AndReturn([timing1, timing2].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_timings(fake_request)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 3)
        header = ["test.event", "Time"]
        self.assertEqual(json_resp[0], header)
        self.assertEqual(json_resp[1], [INSTANCE_ID_1, '0d 00:00:10'])
        self.assertEqual(json_resp[2], [INSTANCE_ID_2, '0d 00:00:20'])
        self.mox.VerifyAll()

    def test_do_summary(self):
        fake_request = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(stacky_server, 'get_event_names')
        events = [{'event': 'test.start'}, {'event': 'test.end'}]
        stacky_server.get_event_names().AndReturn(events)
        fake_request.GET = {'name': 'test.event'}
        results = self.mox.CreateMockAnything()
        models.Timing.objects.filter(name='test').AndReturn(results)
        results.exclude(mox.IgnoreArg()).AndReturn(results)
        results.exclude(diff__lt=0).AndReturn(results)
        timing1 = self.mox.CreateMockAnything()
        timing1.lifecycle = self.mox.CreateMockAnything()
        timing1.lifecycle.instance = INSTANCE_ID_1
        timing1.diff = 10
        timing2 = self.mox.CreateMockAnything()
        timing2.lifecycle = self.mox.CreateMockAnything()
        timing2.lifecycle.instance = INSTANCE_ID_2
        timing2.diff = 20
        results.__len__().AndReturn(2)
        results.__iter__().AndReturn([timing1, timing2].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_summary(fake_request)
        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 2)
        self.assertEqual(json_resp[0], ["Event", "N", "Min", "Max", "Avg"])
        self.assertEqual(json_resp[1], [u'test', 2, u'0d 00:00:10.0',
                                        u'0d 00:00:20.0', u'0d 00:00:15'])

        self.mox.VerifyAll()

    def test_do_request(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'request_id': REQUEST_ID_1}
        raw = self._create_raw()
        results = self.mox.CreateMockAnything()
        models.RawData.objects.filter(request_id=REQUEST_ID_1).AndReturn(results)
        results.order_by('when').AndReturn(results)
        results.__iter__().AndReturn([raw].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_request(fake_request)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 2)
        self.assertEqual(json_resp[0], ["#", "?", "When", "Deployment",
                                        "Event", "Host", "State", "State'",
                                        "Task'"])
        self.assertEqual(json_resp[1][0], 1)
        self.assertEqual(json_resp[1][1], u' ')
        self.assertEqual(json_resp[1][2], str(dt.dt_from_decimal(raw.when)))
        self.assertEqual(json_resp[1][3], u'deployment')
        self.assertEqual(json_resp[1][4], u'test.start')
        self.assertEqual(json_resp[1][5], u'example.com')
        self.assertEqual(json_resp[1][6], u'active')
        self.assertEqual(json_resp[1][7], None)
        self.assertEqual(json_resp[1][8], None)
        self.mox.VerifyAll()

    def test_do_request_bad_request_id(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'request_id': "obviouslybaduuid"}
        self.mox.ReplayAll()

        resp = stacky_server.do_request(fake_request)

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ['Error', 'Message'])
        msg = 'obviouslybaduuid is not request-id-like'
        self.assertEqual(resp_json[1], ['Bad Request', msg])
        self.mox.VerifyAll()

    def _assert_on_show(self, values, raw):
        self.assertEqual(len(values), 12)
        self.assertEqual(values[0], ["Key", "Value"])
        self.assertEqual(values[1], ["#", raw.id])
        self.assertEqual(values[2], ["When",
                                     str(dt.dt_from_decimal(raw.when))])
        self.assertEqual(values[3], ["Deployment", raw.deployment.name])
        self.assertEqual(values[4], ["Category", raw.routing_key])
        self.assertEqual(values[5], ["Publisher", raw.publisher])
        self.assertEqual(values[6], ["State", raw.state])
        self.assertEqual(values[7], ["Event", raw.event])
        self.assertEqual(values[8], ["Service", raw.service])
        self.assertEqual(values[9], ["Host", raw.host])
        self.assertEqual(values[10], ["UUID", raw.instance])
        self.assertEqual(values[11], ["Req ID", raw.request_id])

    def test_do_show(self):
        fake_request = self.mox.CreateMockAnything()
        raw = self._create_raw()
        models.RawData.objects.get(id=1).AndReturn(raw)
        self.mox.ReplayAll()

        resp = stacky_server.do_show(fake_request, 1)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 3)
        self._assert_on_show(json_resp[0], raw)
        self.mox.VerifyAll()

    def test_do_watch(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        self.mox.StubOutWithMock(stacky_server, 'get_deployments')
        deployment1 = self.mox.CreateMockAnything()
        deployment1.id = 1
        deployment1.name = 'dep1'
        deployments = [deployment1]
        stacky_server.get_deployments().AndReturn(deployments)
        self.mox.StubOutWithMock(stacky_server, 'get_event_names')
        events = [{'event': 'test.start'}, {'event': 'test.end'}]
        stacky_server.get_event_names().AndReturn(events)
        results = self.mox.CreateMockAnything()
        models.RawData.objects.order_by('when').AndReturn(results)
        results.filter(when__gt=mox.IgnoreArg()).AndReturn(results)
        results.filter(when__lte=mox.IgnoreArg()).AndReturn(results)
        results.__iter__().AndReturn([self._create_raw()].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_watch(fake_request, 0)
        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 3)
        self.assertEqual(json_resp[0], [10, 1, 15, 20, 10, 36])
        print json_resp
        self.assertEqual(json_resp[1][0][0], 1)
        self.assertEqual(json_resp[1][0][1], u' ')
        time_str = "%s %s" % (json_resp[1][0][2], json_resp[1][0][3])
        datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S.%f")
        self.assertEqual(json_resp[1][0][4], u'dep1')
        self.assertEqual(json_resp[1][0][5], u'test.start')
        self.assertEqual(json_resp[1][0][6], u'%s' % INSTANCE_ID_1)
        self.mox.VerifyAll()

    def test_do_watch_with_deployment(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'deployment': 1}
        self.mox.StubOutWithMock(stacky_server, 'get_deployments')
        deployment1 = self.mox.CreateMockAnything()
        deployment1.id = 1
        deployment1.name = 'dep1'
        deployments = [deployment1]
        stacky_server.get_deployments().AndReturn(deployments)
        self.mox.StubOutWithMock(stacky_server, 'get_event_names')
        events = [{'event': 'test.start'}, {'event': 'test.end'}]
        stacky_server.get_event_names().AndReturn(events)
        results = self.mox.CreateMockAnything()
        models.RawData.objects.order_by('when').AndReturn(results)
        results.filter(deployment=1).AndReturn(results)
        results.filter(when__gt=mox.IgnoreArg()).AndReturn(results)
        results.filter(when__lte=mox.IgnoreArg()).AndReturn(results)
        results.__iter__().AndReturn([self._create_raw()].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_watch(fake_request, 1)
        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 3)
        self.assertEqual(json_resp[0], [10, 1, 15, 20, 10, 36])
        print json_resp
        self.assertEqual(json_resp[1][0][0], 1)
        self.assertEqual(json_resp[1][0][1], u' ')
        time_str = "%s %s" % (json_resp[1][0][2], json_resp[1][0][3])
        datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S.%f")
        self.assertEqual(json_resp[1][0][4], u'dep1')
        self.assertEqual(json_resp[1][0][5], u'test.start')
        self.assertEqual(json_resp[1][0][6], u'%s' % INSTANCE_ID_1)
        self.mox.VerifyAll()

    def test_do_watch_with_event_name(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'event_name': 'test.start'}
        self.mox.StubOutWithMock(stacky_server, 'get_deployments')
        deployment1 = self.mox.CreateMockAnything()
        deployment1.id = 1
        deployment1.name = 'dep1'
        deployments = [deployment1]
        stacky_server.get_deployments().AndReturn(deployments)
        self.mox.StubOutWithMock(stacky_server, 'get_event_names')
        events = [{'event': 'test.start'}, {'event': 'test.end'}]
        stacky_server.get_event_names().AndReturn(events)
        results = self.mox.CreateMockAnything()
        models.RawData.objects.order_by('when').AndReturn(results)
        results.filter(event='test.start').AndReturn(results)
        results.filter(when__gt=mox.IgnoreArg()).AndReturn(results)
        results.filter(when__lte=mox.IgnoreArg()).AndReturn(results)
        results.__iter__().AndReturn([self._create_raw()].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_watch(fake_request, 0)
        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 3)
        self.assertEqual(json_resp[0], [10, 1, 15, 20, 10, 36])
        print json_resp
        self.assertEqual(json_resp[1][0][0], 1)
        self.assertEqual(json_resp[1][0][1], u' ')
        time_str = "%s %s" % (json_resp[1][0][2], json_resp[1][0][3])
        datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S.%f")
        self.assertEqual(json_resp[1][0][4], u'dep1')
        self.assertEqual(json_resp[1][0][5], u'test.start')
        self.assertEqual(json_resp[1][0][6], u'%s' % INSTANCE_ID_1)
        self.mox.VerifyAll()

    def test_do_kpi(self):
        fake_request = self.mox.CreateMockAnything()
        results = self.mox.CreateMockAnything()
        models.RequestTracker.objects.select_related().AndReturn(results)
        results.exclude(last_timing=None).AndReturn(results)
        results.exclude(start__lt=mox.IgnoreArg()).AndReturn(results)
        results.order_by('duration').AndReturn(results)
        tracker = self.mox.CreateMockAnything()
        tracker.last_timing = self.mox.CreateMockAnything()
        tracker.last_timing.end_raw = self.mox.CreateMockAnything()
        tracker.last_timing.end_raw.event = 'test.end'
        deployment = self.mox.CreateMockAnything()
        deployment.name = 'dep1'
        tracker.last_timing.end_raw.deployment = deployment
        tracker.lifecycle = self.mox.CreateMockAnything()
        tracker.lifecycle.instance = INSTANCE_ID_1
        tracker.duration = 10
        results.__iter__().AndReturn([tracker].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_kpi(fake_request)
        self.assertEqual(resp.status_code, 200)
        body = resp.content
        body = json.loads(body)
        self.assertEqual(len(body), 2)
        self.assertEqual(body[0], ["Event", "Time", "UUID", "Deployment"])
        time = u'%s' % stacky_server.sec_to_time(10)
        self.assertEqual(body[1], [u'test', time, INSTANCE_ID_1, u'dep1'])

        self.mox.VerifyAll()

    def test_do_kpi_with_tenant(self):
        fake_request = self.mox.CreateMockAnything()
        objects = self.mox.CreateMockAnything()
        models.RawData.objects.filter(tenant='55555').AndReturn(objects)
        objects.count().AndReturn(1)
        results = self.mox.CreateMockAnything()
        models.RequestTracker.objects.select_related().AndReturn(results)
        results.exclude(last_timing=None).AndReturn(results)
        results.exclude(start__lt=mox.IgnoreArg()).AndReturn(results)
        results.order_by('duration').AndReturn(results)
        tracker = self.mox.CreateMockAnything()
        tracker.last_timing = self.mox.CreateMockAnything()
        tracker.last_timing.end_raw = self.mox.CreateMockAnything()
        tracker.last_timing.end_raw.event = 'test.end'
        tracker.last_timing.end_raw.tenant = '55555'
        deployment = self.mox.CreateMockAnything()
        deployment.name = 'dep1'
        tracker.last_timing.end_raw.deployment = deployment
        tracker.lifecycle = self.mox.CreateMockAnything()
        tracker.lifecycle.instance = INSTANCE_ID_1
        tracker.duration = 10
        results.__iter__().AndReturn([tracker].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_kpi(fake_request, '55555')
        self.assertEqual(resp.status_code, 200)
        body = resp.content
        body = json.loads(body)
        self.assertEqual(len(body), 2)
        self.assertEqual(body[0], ["Event", "Time", "UUID", "Deployment"])
        time = u'%s' % stacky_server.sec_to_time(10)
        self.assertEqual(body[1], [u'test', time, INSTANCE_ID_1, u'dep1'])

        self.mox.VerifyAll()

    def test_do_kpi_with_tenant_no_match(self):
        fake_request = self.mox.CreateMockAnything()
        objects = self.mox.CreateMockAnything()
        models.RawData.objects.filter(tenant='55555').AndReturn(objects)
        objects.count().AndReturn(1)
        results = self.mox.CreateMockAnything()
        models.RequestTracker.objects.select_related().AndReturn(results)
        results.exclude(last_timing=None).AndReturn(results)
        results.exclude(start__lt=mox.IgnoreArg()).AndReturn(results)
        results.order_by('duration').AndReturn(results)
        tracker = self.mox.CreateMockAnything()
        tracker.last_timing = self.mox.CreateMockAnything()
        tracker.last_timing.end_raw = self.mox.CreateMockAnything()
        tracker.last_timing.end_raw.event = 'test.end'
        tracker.last_timing.end_raw.tenant = '55556'
        deployment = self.mox.CreateMockAnything()
        deployment.name = 'dep1'
        tracker.last_timing.end_raw.deployment = deployment
        tracker.lifecycle = self.mox.CreateMockAnything()
        tracker.lifecycle.instance = INSTANCE_ID_1
        tracker.duration = 10
        results.__iter__().AndReturn([tracker].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_kpi(fake_request, '55555')
        self.assertEqual(resp.status_code, 200)
        body = resp.content
        body = json.loads(body)
        self.assertEqual(len(body), 1)

        self.mox.VerifyAll()

    def test_do_kpi_tenant_doesnt_exist(self):
        fake_request = self.mox.CreateMockAnything()
        objects = self.mox.CreateMockAnything()
        models.RawData.objects.filter(tenant='55555').AndReturn(objects)
        objects.count().AndReturn(0)
        self.mox.ReplayAll()

        resp = stacky_server.do_kpi(fake_request, '55555')
        self.assertEqual(resp.status_code, 404)
        body = resp.content
        body = json.loads(body)
        self.assertEqual(len(body), 2)
        self.assertEqual(body[0], ['Error', 'Message'])
        msg = 'Could not find raws for tenant 55555'
        self.assertEqual(body[1], ['Not Found', msg])

        self.mox.VerifyAll()

    def test_do_list_usage_launches(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        results = self.mox.CreateMockAnything()
        models.InstanceUsage.objects.all().AndReturn(results)
        usage = self.mox.CreateMockAnything()
        usage.instance = INSTANCE_ID_1
        usage.launched_at = utils.decimal_utc()
        usage.instance_type_id = 1
        results.__iter__().AndReturn([usage].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_list_usage_launches(fake_request)
        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ["UUID", "Launched At",
                                        "Instance Type Id"])
        self.assertEqual(resp_json[1][0], INSTANCE_ID_1)
        time_str = dt.dt_from_decimal(usage.launched_at)
        self.assertEqual(resp_json[1][1], str(time_str))
        self.assertEqual(resp_json[1][2], 1)

        self.mox.VerifyAll()

    def test_do_list_usage_launches_with_instance(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'instance': INSTANCE_ID_1}
        results = self.mox.CreateMockAnything()
        models.InstanceUsage.objects.filter(instance=INSTANCE_ID_1)\
                                    .AndReturn(results)
        usage = self.mox.CreateMockAnything()
        usage.instance = INSTANCE_ID_1
        usage.launched_at = utils.decimal_utc()
        usage.instance_type_id = 1
        results.__iter__().AndReturn([usage].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_list_usage_launches(fake_request)
        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ["UUID", "Launched At",
                                        "Instance Type Id"])
        self.assertEqual(resp_json[1][0], INSTANCE_ID_1)
        time_str = dt.dt_from_decimal(usage.launched_at)
        self.assertEqual(resp_json[1][1], str(time_str))
        self.assertEqual(resp_json[1][2], 1)

        self.mox.VerifyAll()

    def test_do_list_usage_launches_bad_instance(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'instance': "obviouslybaduuid"}
        self.mox.ReplayAll()

        resp = stacky_server.do_list_usage_launches(fake_request)

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ['Error', 'Message'])
        msg = 'obviouslybaduuid is not uuid-like'
        self.assertEqual(resp_json[1], ['Bad Request', msg])
        self.mox.VerifyAll()

    def test_do_list_usage_deletes(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        results = self.mox.CreateMockAnything()
        models.InstanceDeletes.objects.all().AndReturn(results)
        usage = self.mox.CreateMockAnything()
        usage.instance = INSTANCE_ID_1
        usage.launched_at = utils.decimal_utc()
        usage.deleted_at = usage.launched_at + 10
        results.__iter__().AndReturn([usage].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_list_usage_deletes(fake_request)
        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ["UUID", "Launched At",
                                        "Deleted At"])
        self.assertEqual(resp_json[1][0], INSTANCE_ID_1)
        launch_time_str = dt.dt_from_decimal(usage.launched_at)
        self.assertEqual(resp_json[1][1], str(launch_time_str))
        delete_time_str = dt.dt_from_decimal(usage.deleted_at)
        self.assertEqual(resp_json[1][2], str(delete_time_str))
        self.mox.VerifyAll()

    def test_do_list_usage_deletes_with_instance(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'instance': INSTANCE_ID_1}
        results = self.mox.CreateMockAnything()
        models.InstanceDeletes.objects.filter(instance=INSTANCE_ID_1)\
                                      .AndReturn(results)
        usage = self.mox.CreateMockAnything()
        usage.instance = INSTANCE_ID_1
        usage.launched_at = utils.decimal_utc()
        usage.deleted_at = usage.launched_at + 10
        results.__iter__().AndReturn([usage].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_list_usage_deletes(fake_request)
        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ["UUID", "Launched At",
                                        "Deleted At"])
        self.assertEqual(resp_json[1][0], INSTANCE_ID_1)
        launch_time_str = dt.dt_from_decimal(usage.launched_at)
        self.assertEqual(resp_json[1][1], str(launch_time_str))
        delete_time_str = dt.dt_from_decimal(usage.deleted_at)
        self.assertEqual(resp_json[1][2], str(delete_time_str))
        self.mox.VerifyAll()

    def test_do_list_usage_deletes_bad_instance(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'instance': "obviouslybaduuid"}
        self.mox.ReplayAll()

        resp = stacky_server.do_list_usage_deletes(fake_request)

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ['Error', 'Message'])
        msg = 'obviouslybaduuid is not uuid-like'
        self.assertEqual(resp_json[1], ['Bad Request', msg])
        self.mox.VerifyAll()

    def test_do_list_usage_exists(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        results = self.mox.CreateMockAnything()
        models.InstanceExists.objects.all().AndReturn(results)
        usage = self.mox.CreateMockAnything()
        usage.instance = INSTANCE_ID_1
        usage.launched_at = utils.decimal_utc()
        usage.deleted_at = usage.launched_at + 10
        usage.instance_type_id = 1
        usage.message_id = 'someid'
        usage.status = 'pending'
        results.__iter__().AndReturn([usage].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_list_usage_exists(fake_request)
        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ["UUID", "Launched At", "Deleted At",
                                        "Instance Type Id", "Message ID",
                                        "Status"])
        self.assertEqual(resp_json[1][0], INSTANCE_ID_1)
        launch_time_str = dt.dt_from_decimal(usage.launched_at)
        self.assertEqual(resp_json[1][1], str(launch_time_str))
        delete_time_str = dt.dt_from_decimal(usage.deleted_at)
        self.assertEqual(resp_json[1][2], str(delete_time_str))
        self.mox.VerifyAll()

    def test_do_list_usage_exists_with_instance(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'instance': INSTANCE_ID_1}
        results = self.mox.CreateMockAnything()
        models.InstanceExists.objects.filter(instance=INSTANCE_ID_1)\
                                     .AndReturn(results)
        usage = self.mox.CreateMockAnything()
        usage.instance = INSTANCE_ID_1
        usage.launched_at = utils.decimal_utc()
        usage.deleted_at = usage.launched_at + 10
        usage.instance_type_id = 1
        usage.message_id = 'someid'
        usage.status = 'pending'
        results.__iter__().AndReturn([usage].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_list_usage_exists(fake_request)
        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ["UUID", "Launched At", "Deleted At",
                                        "Instance Type Id", "Message ID",
                                        "Status"])
        self.assertEqual(resp_json[1][0], INSTANCE_ID_1)
        launch_time_str = dt.dt_from_decimal(usage.launched_at)
        self.assertEqual(resp_json[1][1], str(launch_time_str))
        delete_time_str = dt.dt_from_decimal(usage.deleted_at)
        self.assertEqual(resp_json[1][2], str(delete_time_str))
        self.mox.VerifyAll()

    def test_do_list_usage_exists_bad_instance(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'instance': "obviouslybaduuid"}
        self.mox.ReplayAll()

        resp = stacky_server.do_list_usage_exists(fake_request)

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ['Error', 'Message'])
        msg = 'obviouslybaduuid is not uuid-like'
        self.assertEqual(resp_json[1], ['Bad Request', msg])
        self.mox.VerifyAll()

