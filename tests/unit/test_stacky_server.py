# Copyright (c) 2012 - Rackspace Inc.
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
import ast

import datetime
import decimal
import json
from django.core.exceptions import FieldError

import mox

from stacktach import datetime_to_decimal as dt
from stacktach import models
from stacktach import stacky_server
import utils
from utils import INSTANCE_ID_1, INSTANCE_TYPE_ID_1
from utils import INSTANCE_FLAVOR_ID_1
from utils import INSTANCE_ID_2
from utils import REQUEST_ID_1

from tests.unit import StacktachBaseTestCase


class StackyServerTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self.mox.StubOutWithMock(models, 'RawData', use_mock_anything=True)
        models.RawData.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'Deployment', use_mock_anything=True)
        self.mox.StubOutWithMock(models, 'GlanceRawData',
                                 use_mock_anything=True)
        models.GlanceRawData.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'GenericRawData',
                                 use_mock_anything=True)
        models.GenericRawData.objects = self.mox.CreateMockAnything()
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
        raw.when = utils.decimal_utc(datetime.datetime(2013, 7, 17, 10, 16,
                                                       10, 717219))
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
        raw.status = 'state'
        raw.request_id = REQUEST_ID_1
        raw.json = '{"key": "value"}'
        raw.uuid = 'uuid'
        raw.tenant = 'tenant'
        return raw

    def test_get_event_names(self):
        model = self.mox.CreateMockAnything()
        result = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(stacky_server, '_model_factory')
        stacky_server._model_factory('nova').AndReturn(model)
        model.values('event').AndReturn(result)
        result.distinct().AndReturn(result)
        self.mox.ReplayAll()

        event_names = stacky_server.get_event_names()
        self.assertEqual(event_names, result)

        self.mox.VerifyAll()

    def test_get_host_names_for_nova(self):
        result = self.mox.CreateMockAnything()
        models.RawData.objects.values('host').AndReturn(result)
        result.distinct().AndReturn(result)
        self.mox.ReplayAll()

        event_names = stacky_server.get_host_names('nova')
        self.assertEqual(event_names, result)

        self.mox.VerifyAll()

    def test_get_host_names_for_glance(self):
        result = self.mox.CreateMockAnything()
        models.GlanceRawData.objects.values('host').AndReturn(result)
        result.distinct().AndReturn(result)
        self.mox.ReplayAll()

        event_names = stacky_server.get_host_names('glance')
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
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        lc_result = self.mox.CreateMockAnything()
        lifecycle = self.mox.CreateMockAnything()
        models.Lifecycle.objects.filter(instance=INSTANCE_ID_1)\
                                .AndReturn(lc_result)
        lc_result[None:50].AndReturn(lc_result)
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

        event_names = stacky_server.get_timings_for_uuid(fake_request,
                                                         INSTANCE_ID_1)

        self.assertEqual(len(event_names), 2)
        self.assertEqual(event_names[0], ['?', 'Event', 'Time (secs)'])
        self.assertEqual(event_names[1], ['S', 'name', 'n/a'])
        self.mox.VerifyAll()

    def test_get_timings_for_uuid_end_only(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        lc_result = self.mox.CreateMockAnything()
        lifecycle = self.mox.CreateMockAnything()
        models.Lifecycle.objects.filter(instance=INSTANCE_ID_1) \
                                .AndReturn(lc_result)
        lc_result[None:50].AndReturn(lc_result)
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

        event_names = stacky_server.get_timings_for_uuid(fake_request,
                                                         INSTANCE_ID_1)

        self.assertEqual(len(event_names), 2)
        self.assertEqual(event_names[0], ['?', 'Event', 'Time (secs)'])
        self.assertEqual(event_names[1], ['E', 'name', 'n/a'])
        self.mox.VerifyAll()

    def test_get_timings_for_uuid(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        lc_result = self.mox.CreateMockAnything()
        lifecycle = self.mox.CreateMockAnything()
        models.Lifecycle.objects.filter(instance=INSTANCE_ID_1) \
            .AndReturn(lc_result)
        lc_result[None:50].AndReturn(lc_result)
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
        event_names = stacky_server.get_timings_for_uuid(fake_request,
                                                         INSTANCE_ID_1)

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

    def test_do_events_of_a_single_service(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'service': 'nova'}
        event1 = {'event': 'some.event.1'}
        event2 = {'event': 'some.event.2'}
        events = [event1, event2]
        self.mox.StubOutWithMock(stacky_server, 'get_event_names')
        stacky_server.get_event_names(service='nova').AndReturn(events)
        self.mox.ReplayAll()

        resp = stacky_server.do_events(fake_request)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 3)
        self.assertEqual(json_resp[0], ['Event Name'])
        self.assertEqual(json_resp[1], ['some.event.1'])
        self.assertEqual(json_resp[2], ['some.event.2'])
        self.mox.VerifyAll()

    def test_do_events_of_all_services(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'service': 'all'}
        event1 = {'event': 'some.event.1'}
        event2 = {'event': 'some.event.2'}
        events = [event1, event2]
        self.mox.StubOutWithMock(stacky_server, 'get_event_names')
        stacky_server.get_event_names('nova').AndReturn(events)
        stacky_server.get_event_names('glance').AndReturn(events)
        stacky_server.get_event_names('generic').AndReturn(events)
        self.mox.ReplayAll()

        resp = stacky_server.do_events(fake_request)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 7)
        self.assertEqual(json_resp[0], ['Event Name'])
        self.assertEqual(json_resp[1], ['some.event.1'])
        self.assertEqual(json_resp[2], ['some.event.2'])
        self.mox.VerifyAll()

    def test_do_hosts(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'service': 'service'}
        host1 = {'host': 'www.demo.com'}
        host2 = {'host': 'www.example.com'}
        hosts = [host1, host2]
        self.mox.StubOutWithMock(stacky_server, 'get_host_names')
        stacky_server.get_host_names('service').AndReturn(hosts)
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
        search_result = [["#", "?", "When", "Deployment", "Event", "Host",
                          "State", "State'", "Task'"], [1, " ",
                          "2013-07-17 10:16:10.717219", "deployment",
                          "test.start", "example.com", "active", None, None]]
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'uuid': INSTANCE_ID_1}
        result = self.mox.CreateMockAnything()
        models.RawData.objects.select_related().AndReturn(result)
        result.filter(instance=INSTANCE_ID_1).AndReturn(result)
        result.order_by('when').AndReturn(result)
        raw = self._create_raw()
        result[None:50].AndReturn(result)
        result.__iter__().AndReturn([raw].__iter__())
        raw.search_results([], mox.IgnoreArg(), ' ').AndReturn(search_result)
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

    def test_do_uuid_when_filters(self):
        search_result = [["#", "?", "When", "Deployment", "Event", "Host",
                          "State", "State'", "Task'"], [1, " ",
                          "2013-07-17 10:16:10.717219", "deployment",
                          "test.start", "example.com", "active", None, None]]
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'uuid': INSTANCE_ID_1,
                            'when_min': '1.1',
                            'when_max': '2.1'}
        result = self.mox.CreateMockAnything()
        models.RawData.objects.select_related().AndReturn(result)
        result.filter(instance=INSTANCE_ID_1,
                      when__gte=decimal.Decimal('1.1'),
                      when__lte=decimal.Decimal('2.1')).AndReturn(result)
        result.order_by('when').AndReturn(result)
        raw = self._create_raw()
        result[None:50].AndReturn(result)
        result.__iter__().AndReturn([raw].__iter__())
        raw.search_results([], mox.IgnoreArg(), ' ').AndReturn(search_result)
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

    def test_do_uuid_for_glance(self):
        search_result = [["#", "?", "When", "Deployment", "Event", "Host",
                          "Status"], [1, " ",
                          "2013-07-17 10:16:10.717219", "deployment",
                          "test.start", "example.com", "state"]]
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'uuid': INSTANCE_ID_1, 'service': 'glance'}
        result = self.mox.CreateMockAnything()
        models.GlanceRawData.objects.select_related().AndReturn(result)
        result.filter(uuid=INSTANCE_ID_1).AndReturn(result)
        result.order_by('when').AndReturn(result)
        raw = self._create_raw()
        result[None:50].AndReturn(result)
        result.__iter__().AndReturn([raw].__iter__())
        raw.search_results([], mox.IgnoreArg(), ' ').AndReturn(search_result)
        self.mox.ReplayAll()

        resp = stacky_server.do_uuid(fake_request)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 2)
        header = ["#", "?", "When", "Deployment", "Event", "Host",
                  "Status"]
        self.assertEqual(json_resp[0], header)
        datetime = dt.dt_from_decimal(raw.when)
        body = [1, " ", str(datetime), "deployment", "test.start",
                "example.com", "state"]
        self.assertEqual(json_resp[1], body)
        self.mox.VerifyAll()

    def test_do_uuid_for_glance_when_filters(self):
        search_result = [["#", "?", "When", "Deployment", "Event", "Host",
                          "Status"], [1, " ",
                          "2013-07-17 10:16:10.717219", "deployment",
                          "test.start", "example.com", "state"]]
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'uuid': INSTANCE_ID_1,
                            'when_min': '1.1',
                            'when_max': '2.1',
                            'service': 'glance'}
        result = self.mox.CreateMockAnything()
        models.GlanceRawData.objects.select_related().AndReturn(result)
        result.filter(uuid=INSTANCE_ID_1,
                      when__gte=decimal.Decimal('1.1'),
                      when__lte=decimal.Decimal('2.1')).AndReturn(result)
        result.order_by('when').AndReturn(result)
        raw = self._create_raw()
        result[None:50].AndReturn(result)
        result.__iter__().AndReturn([raw].__iter__())
        raw.search_results([], mox.IgnoreArg(), ' ').AndReturn(search_result)
        self.mox.ReplayAll()

        resp = stacky_server.do_uuid(fake_request)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 2)
        header = ["#", "?", "When", "Deployment", "Event", "Host",
                  "Status"]
        self.assertEqual(json_resp[0], header)
        datetime = dt.dt_from_decimal(raw.when)
        body = [1, " ", str(datetime), "deployment", "test.start",
                "example.com", "state"]
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
        results[None:50].AndReturn(results)
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

    def test_do_timings_end_when_min(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'name': 'test.event', 'end_when_min': '1.1'}
        results = self.mox.CreateMockAnything()
        models.Timing.objects.select_related().AndReturn(results)
        results.filter(name='test.event',
                       end_when__gte=decimal.Decimal('1.1')).AndReturn(results)
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
        results[None:50].AndReturn(results)
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

    def test_do_timings_end_when_max(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'name': 'test.event', 'end_when_max': '1.1'}
        results = self.mox.CreateMockAnything()
        models.Timing.objects.select_related().AndReturn(results)
        results.filter(name='test.event',
                       end_when__lte=decimal.Decimal('1.1')).AndReturn(results)
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
        results[None:50].AndReturn(results)
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

    def test_do_timings_end_when_max_when_min(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'name': 'test.event',
                            'end_when_min': '1.1',
                            'end_when_max': '2.1'}
        results = self.mox.CreateMockAnything()
        models.Timing.objects.select_related().AndReturn(results)
        results.filter(name='test.event',
                       end_when__gte=decimal.Decimal('1.1'),
                       end_when__lte=decimal.Decimal('2.1')).AndReturn(results)
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
        results[None:50].AndReturn(results)
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
        results[None:50].AndReturn(results)
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
        results[None:50].AndReturn(results)
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

    def test_do_request_when_filters(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'request_id': REQUEST_ID_1,
                            'when_min': '1.1',
                            'when_max': '2.1'}
        raw = self._create_raw()
        results = self.mox.CreateMockAnything()
        when_min = decimal.Decimal('1.1')
        when_max = decimal.Decimal('2.1')
        models.RawData.objects.filter(request_id=REQUEST_ID_1,
                                      when__gte=when_min,
                                      when__lte=when_max).AndReturn(results)
        results.order_by('when').AndReturn(results)
        results[None:50].AndReturn(results)
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

    def _assert_on_show_nova(self, json_resp, raw):
        self.assertEqual(len(json_resp), 3)
        values = json_resp[0]
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
        self.assertEqual(values[10],["UUID", raw.instance])
        self.assertEqual(values[11], ["Req ID", raw.request_id])

    def _assert_on_show_glance(self, json_resp, raw):
        self.assertEqual(len(json_resp), 3)
        values = json_resp[0]
        self.assertEqual(len(values), 12)
        self.assertEqual(values[0], ["Key", "Value"])
        self.assertEqual(values[1], ["#", raw.id])
        self.assertEqual(values[2], ["When",
                                     str(dt.dt_from_decimal(raw.when))])
        self.assertEqual(values[3], ["Deployment", raw.deployment.name])
        self.assertEqual(values[4], ["Category", raw.routing_key])
        self.assertEqual(values[5], ["Publisher", raw.publisher])
        self.assertEqual(values[6], ["Status", raw.status])
        self.assertEqual(values[7], ["Event", raw.event])
        self.assertEqual(values[8], ["Service", raw.service])
        self.assertEqual(values[9], ["Host", raw.host])
        self.assertEqual(values[10],["UUID", raw.uuid])
        self.assertEqual(values[11], ["Req ID", raw.request_id])

    def test_do_show(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        raw = self._create_raw()
        models.RawData.objects.get(id=1).AndReturn(raw)
        self.mox.ReplayAll()

        resp = stacky_server.do_show(fake_request, 1)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self._assert_on_show_nova(json_resp, raw)
        self.mox.VerifyAll()

    def test_do_show_for_glance_rawdata(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'service':'glance'}
        raw = self._create_raw()
        models.GlanceRawData.objects.get(id=1).AndReturn(raw)
        self.mox.ReplayAll()

        resp = stacky_server.do_show(fake_request, 1)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self._assert_on_show_glance(json_resp, raw)
        self.mox.VerifyAll()

    def test_do_show_for_generic_rawdata(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'service':'generic'}
        raw = self._create_raw()
        models.GenericRawData.objects.get(id=1).AndReturn(raw)
        self.mox.ReplayAll()

        resp = stacky_server.do_show(fake_request, 1)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self._assert_on_show_nova(json_resp, raw)
        self.mox.VerifyAll()

    def test_do_show_should_return_empty_result_on_object_not_found_exception(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}

        raw = self._create_raw()
        models.RawData.objects.get(id=1).AndReturn(raw)
        self.mox.ReplayAll()

        resp = stacky_server.do_show(fake_request, 1)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self._assert_on_show_nova(json_resp, raw)
        self.mox.VerifyAll()

    def test_do_watch_for_glance(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'service': 'glance'}
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
        models.GlanceRawData.objects.order_by('when').AndReturn(results)
        results.filter(when__gt=mox.IgnoreArg()).AndReturn(results)
        results.filter(when__lte=mox.IgnoreArg()).AndReturn(results)
        results.__iter__().AndReturn([self._create_raw()].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_watch(fake_request, 0)
        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 3)
        self.assertEqual(json_resp[0], [10, 1, 15, 20, 10, 36])
        self.assertEqual(json_resp[1][0][0], 1)
        self.assertEqual(json_resp[1][0][1], u' ')
        time_str = "%s %s" % (json_resp[1][0][2], json_resp[1][0][3])
        datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S.%f")
        self.assertEqual(json_resp[1][0][4], u'dep1')
        self.assertEqual(json_resp[1][0][5], u'test.start')
        self.assertEqual(json_resp[1][0][6], u'%s' % 'uuid')
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
        model = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(stacky_server, '_model_factory')
        stacky_server._model_factory('nova').AndReturn(model)
        model.order_by('when').AndReturn(results)
        results.filter(when__gt=mox.IgnoreArg()).AndReturn(results)
        results.filter(when__lte=mox.IgnoreArg()).AndReturn(results)
        results.__iter__().AndReturn([self._create_raw()].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_watch(fake_request, 0)
        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 3)
        self.assertEqual(json_resp[0], [10, 1, 15, 20, 10, 36])
        self.assertEqual(json_resp[1][0][0], 1)
        self.assertEqual(json_resp[1][0][1], u' ')
        time_str = "%s %s" % (json_resp[1][0][2], json_resp[1][0][3])
        datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S.%f")
        self.assertEqual(json_resp[1][0][4], u'dep1')
        self.assertEqual(json_resp[1][0][5], u'test.start')
        self.assertEqual(json_resp[1][0][6], u'%s' % 'uuid')
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
        model = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(stacky_server, '_model_factory')
        stacky_server._model_factory('nova').AndReturn(model)
        model.order_by('when').AndReturn(results)

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
        self.assertEqual(json_resp[1][0][0], 1)
        self.assertEqual(json_resp[1][0][1], u' ')
        time_str = "%s %s" % (json_resp[1][0][2], json_resp[1][0][3])
        datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S.%f")
        self.assertEqual(json_resp[1][0][4], u'dep1')
        self.assertEqual(json_resp[1][0][5], u'test.start')
        self.assertEqual(json_resp[1][0][6], u'%s' % 'uuid')
        self.mox.VerifyAll()

    def test_do_watch_with_event_name(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'event_name': 'test.start','service': 'nova'}
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
        self.assertEqual(json_resp[1][0][0], 1)
        self.assertEqual(json_resp[1][0][1], u' ')
        time_str = "%s %s" % (json_resp[1][0][2], json_resp[1][0][3])
        datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S.%f")
        self.assertEqual(json_resp[1][0][4], u'dep1')
        self.assertEqual(json_resp[1][0][5], u'test.start')
        self.assertEqual(json_resp[1][0][6], u'%s' % 'uuid')
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
        usage.instance_type_id = INSTANCE_TYPE_ID_1
        usage.instance_flavor_id = INSTANCE_FLAVOR_ID_1
        results[None:50].AndReturn(results)
        results.__iter__().AndReturn([usage].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_list_usage_launches(fake_request)
        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ["UUID", "Launched At",
                                        "Instance Type Id",
                                        "Instance Flavor Id"])
        self.assertEqual(resp_json[1][0], INSTANCE_ID_1)
        time_str = dt.dt_from_decimal(usage.launched_at)
        self.assertEqual(resp_json[1][1], str(time_str))
        self.assertEqual(resp_json[1][2], INSTANCE_TYPE_ID_1)
        self.assertEqual(resp_json[1][3], INSTANCE_FLAVOR_ID_1)

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
        usage.instance_type_id = INSTANCE_TYPE_ID_1
        usage.instance_flavor_id = INSTANCE_FLAVOR_ID_1
        results[None:50].AndReturn(results)
        results.__iter__().AndReturn([usage].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_list_usage_launches(fake_request)
        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ["UUID", "Launched At",
                                        "Instance Type Id",
                                        "Instance Flavor Id"])
        self.assertEqual(resp_json[1][0], INSTANCE_ID_1)
        time_str = dt.dt_from_decimal(usage.launched_at)
        self.assertEqual(resp_json[1][1], str(time_str))
        self.assertEqual(resp_json[1][2], INSTANCE_TYPE_ID_1)
        self.assertEqual(resp_json[1][3], INSTANCE_FLAVOR_ID_1)

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
        results[None:50].AndReturn(results)
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
        results[None:50].AndReturn(results)
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
        usage.instance_type_id = INSTANCE_TYPE_ID_1
        usage.instance_flavor_id = INSTANCE_FLAVOR_ID_1
        usage.message_id = 'someid'
        usage.status = 'pending'
        results[None:50].AndReturn(results)
        results.__iter__().AndReturn([usage].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_list_usage_exists(fake_request)
        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ["UUID", "Launched At", "Deleted At",
                                        "Instance Type Id",
                                        "Instance Flavor Id", "Message ID",
                                        "Status"])
        self.assertEqual(resp_json[1][0], INSTANCE_ID_1)
        launch_time_str = dt.dt_from_decimal(usage.launched_at)
        self.assertEqual(resp_json[1][1], str(launch_time_str))
        delete_time_str = dt.dt_from_decimal(usage.deleted_at)
        self.assertEqual(resp_json[1][2], str(delete_time_str))
        self.assertEqual(resp_json[1][3], INSTANCE_TYPE_ID_1)
        self.assertEqual(resp_json[1][4], INSTANCE_FLAVOR_ID_1)
        self.assertEqual(resp_json[1][5], 'someid')
        self.assertEqual(resp_json[1][6], 'pending')
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
        usage.instance_type_id = INSTANCE_TYPE_ID_1
        usage.instance_flavor_id = INSTANCE_FLAVOR_ID_1
        usage.message_id = 'someid'
        usage.status = 'pending'
        results[None:50].AndReturn(results)
        results.__iter__().AndReturn([usage].__iter__())
        self.mox.ReplayAll()

        resp = stacky_server.do_list_usage_exists(fake_request)
        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)
        self.assertEqual(resp_json[0], ["UUID", "Launched At", "Deleted At",
                                        "Instance Type Id",
                                        "Instance Flavor Id", "Message ID",
                                        "Status"])
        self.assertEqual(resp_json[1][0], INSTANCE_ID_1)
        launch_time_str = dt.dt_from_decimal(usage.launched_at)
        self.assertEqual(resp_json[1][1], str(launch_time_str))
        delete_time_str = dt.dt_from_decimal(usage.deleted_at)
        self.assertEqual(resp_json[1][2], str(delete_time_str))
        self.assertEqual(resp_json[1][3], INSTANCE_TYPE_ID_1)
        self.assertEqual(resp_json[1][4], INSTANCE_FLAVOR_ID_1)
        self.assertEqual(resp_json[1][5], 'someid')
        self.assertEqual(resp_json[1][6], 'pending')
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

    def test_model_factory_for_nova(self):
        self.mox.UnsetStubs()
        nova_model = stacky_server._model_factory('nova')
        self.assertEqual(nova_model.model, models.RawData)

    def test_model_factory_for_nova(self):
        self.mox.UnsetStubs()
        nova_model = stacky_server._model_factory('glance')
        self.assertEqual(nova_model.model, models.GlanceRawData)

    def test_model_factory_for_nova(self):
        self.mox.UnsetStubs()
        nova_model = stacky_server._model_factory('generic')
        self.assertEqual(nova_model.model, models.GenericRawData)

    def _assert_on_search_nova(self, json_resp, raw):
        title = json_resp[0]
        values = json_resp[1]
        self.assertEqual(len(values), 9)
        self.assertEqual([title[0], values[0]],["#", raw.id] )
        self.assertEqual([title[1], values[1]], ['?', ' '])
        self.assertEqual([title[2], values[2]], ["When",
                                     str(dt.dt_from_decimal(raw.when))])
        self.assertEqual([title[3], values[3]], ["Deployment", raw.deployment.name])
        self.assertEqual([title[4], values[4]], ["Event", raw.event])
        self.assertEqual([title[5], values[5]], ["Host", raw.host])
        self.assertEqual([title[6], values[6]], ["State", raw.state])
        self.assertEqual([title[7], values[7]], ["State'", raw.old_state])

    def test_search_by_field_for_nova(self):
        search_result = [["#", "?", "When", "Deployment", "Event", "Host",
                          "State", "State'", "Task'"], [1, " ",
                          "2013-07-17 10:16:10.717219", "deployment",
                          "test.start", "example.com", "active", None, None]]
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'field': 'tenant', 'value': 'tenant'}
        raw = self._create_raw()
        results = self.mox.CreateMockAnything()
        models.RawData.objects.filter(tenant='tenant').AndReturn(results)
        results.order_by('-when').AndReturn([raw])
        raw.search_results([], mox.IgnoreArg(), ' ').AndReturn(search_result)
        self.mox.ReplayAll()

        resp = stacky_server.search(fake_request)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self._assert_on_search_nova(json_resp, raw)
        self.mox.VerifyAll()

    def test_search_by_field_for_nova_when_filters(self):
        search_result = [["#", "?", "When", "Deployment", "Event", "Host",
                          "State", "State'", "Task'"], [1, " ",
                          "2013-07-17 10:16:10.717219", "deployment",
                          "test.start", "example.com", "active", None, None]]
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'field': 'tenant', 'value': 'tenant',
                            'when_min': '1.1',
                            'when_max': '2.1'}
        raw = self._create_raw()
        results = self.mox.CreateMockAnything()
        models.RawData.objects.filter(tenant='tenant',
                                      when__gte=decimal.Decimal('1.1'),
                                      when__lte=decimal.Decimal('2.1')).AndReturn(results)
        results.order_by('-when').AndReturn([raw])
        raw.search_results([], mox.IgnoreArg(), ' ').AndReturn(search_result)
        self.mox.ReplayAll()

        resp = stacky_server.search(fake_request)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self._assert_on_search_nova(json_resp, raw)
        self.mox.VerifyAll()

    def test_search_by_field_for_nova_with_limit(self):
        search_result = [["#", "?", "When", "Deployment", "Event", "Host",
                          "State", "State'", "Task'"], [1, " ",
                          "2013-07-17 10:16:10.717219", "deployment",
                          "test.start", "example.com", "active", None, None]]
        search_result_2 = [["#", "?", "When", "Deployment", "Event", "Host",
                          "State", "State'", "Task'"], [1, " ",
                          "2013-07-17 10:16:10.717219", "deployment",
                          "test.start", "example.com", "active", None, None],[2, " ",
                          "2013-07-17 10:16:10.717219", "deployment",
                          "test.start", "example.com", "active", None, None]]
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'field': 'tenant', 'value': 'tenant', 'limit': '2',
                            'service': 'nova'}
        raw1 = self._create_raw()
        raw2 = self._create_raw()
        raw3 = self._create_raw()
        raw2.id = 2
        raw3.id = 3
        results = self.mox.CreateMockAnything()
        models.RawData.objects.filter(tenant='tenant').AndReturn(results)
        results.order_by('-when').AndReturn([raw1, raw2, raw3])
        raw1.search_results([], mox.IgnoreArg(), ' ').AndReturn(search_result)
        raw2.search_results(search_result, mox.IgnoreArg(),' ').AndReturn(search_result_2)
        self.mox.ReplayAll()

        resp = stacky_server.search(fake_request)

        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 3)
        self._assert_on_search_nova(json_resp, raw1)
        self.mox.VerifyAll()

    def test_search_with_wrong_field_value_returns_400_error_and_a_message(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'field': 'tenant', 'value': 'tenant'}
        models.RawData.objects.filter(tenant='tenant').AndRaise(FieldError)
        self.mox.ReplayAll()

        resp = stacky_server.search(fake_request)

        self.assertEqual(resp.status_code, 400)
        json_resp = json.loads(resp.content)
        self.assertEquals(json_resp[0],[u'Error', u'Message'])
        self.assertEquals(json_resp[1],
                          [u'Bad Request', u"The requested field"
        u" 'tenant' does not exist for the corresponding object.\nNote: "
        u"The field names of database are case-sensitive."])

        self.mox.VerifyAll()

    def test_model_search_default_limit(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        fake_model = self.mox.CreateMockAnything()
        filters = {'field': 'value'}
        results = self.mox.CreateMockAnything()
        fake_model.filter(**filters).AndReturn(results)
        results[None:50].AndReturn(results)
        self.mox.ReplayAll()
        actual_results = stacky_server.model_search(fake_request, fake_model,
                                                    filters)
        self.assertEqual(actual_results, results)
        self.mox.VerifyAll()

    def test_model_search_default_limit_with_offset(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'offset': '1'}
        fake_model = self.mox.CreateMockAnything()
        filters = {'field': 'value'}
        results = self.mox.CreateMockAnything()
        fake_model.filter(**filters).AndReturn(results)
        results[1:51].AndReturn(results)
        self.mox.ReplayAll()
        actual_results = stacky_server.model_search(fake_request, fake_model,
                                                    filters)
        self.assertEqual(actual_results, results)
        self.mox.VerifyAll()

    def test_model_search_default_with_limit(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'limit': '1'}
        fake_model = self.mox.CreateMockAnything()
        filters = {'field': 'value'}
        results = self.mox.CreateMockAnything()
        fake_model.filter(**filters).AndReturn(results)
        results[None:1].AndReturn(results)
        self.mox.ReplayAll()
        actual_results = stacky_server.model_search(fake_request, fake_model,
                                                    filters)
        self.assertEqual(actual_results, results)
        self.mox.VerifyAll()

    def test_model_search_default_with_limit_and_offset(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'limit': '5',
                            'offset': '10'}
        fake_model = self.mox.CreateMockAnything()
        filters = {'field': 'value'}
        results = self.mox.CreateMockAnything()
        fake_model.filter(**filters).AndReturn(results)
        results[10:15].AndReturn(results)
        self.mox.ReplayAll()
        actual_results = stacky_server.model_search(fake_request, fake_model,
                                                    filters)
        self.assertEqual(actual_results, results)
        self.mox.VerifyAll()

    def test_model_search_related(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        fake_model = self.mox.CreateMockAnything()
        filters = {'field': 'value'}
        results = self.mox.CreateMockAnything()
        fake_model.select_related().AndReturn(results)
        results.filter(**filters).AndReturn(results)
        results[None:50].AndReturn(results)
        self.mox.ReplayAll()
        actual_results = stacky_server.model_search(fake_request, fake_model,
                                                    filters, related=True)
        self.assertEqual(actual_results, results)
        self.mox.VerifyAll()

    def test_model_order_by(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        fake_model = self.mox.CreateMockAnything()
        filters = {'field': 'value'}
        results = self.mox.CreateMockAnything()
        fake_model.filter(**filters).AndReturn(results)
        results.order_by('when').AndReturn(results)
        results[None:50].AndReturn(results)
        self.mox.ReplayAll()
        actual_results = stacky_server.model_search(fake_request, fake_model,
                                                    filters, order_by='when')
        self.assertEqual(actual_results, results)
        self.mox.VerifyAll()


class JsonReportsSearchAPI(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self.model = models.JsonReport.objects
        self.model_search_result = self.mox.CreateMockAnything()
        self.model_search_result.id = '5975'
        self.model_search_result.period_start = datetime.datetime(2014, 1, 18,)
        self.model_search_result.period_end = datetime.datetime(2014, 1, 19)
        self.model_search_result.created = 1388569200
        self.model_search_result.name = 'nova usage audit'
        self.model_search_result.version = 4

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_jsonreports_search_order_by_period_start(self):
        request = self.mox.CreateMockAnything()
        request.GET = {
            'id': 1,
            'name': 'nova_usage_audit',
            'period_start': '2014-01-01 00:00:00',
            'period_end': '2014-01-02 00:00:00',
            'created': '2014-01-01 09:40:00',
            'version': 4,
            'json': 'json'
        }
        filters = {
            'id__exact': 1,
            'period_start__exact': '2014-01-01 00:00:00',
            'name__exact': 'nova_usage_audit',
            'period_end__exact': '2014-01-02 00:00:00',
            'created__exact': decimal.Decimal('1388569200'),
            'version__exact': 4,
            'json__exact': 'json'
        }
        self.mox.StubOutWithMock(stacky_server, 'model_search')
        stacky_server.model_search(request, self.model, filters,
                                   order_by='-id').AndReturn(
            [self.model_search_result])
        self.mox.ReplayAll()

        actual_result = stacky_server.do_jsonreports_search(request).content
        expected_result = \
            [['Id', 'Start', 'End', 'Created', 'Name', 'Version'],
             ['5975', '2014-01-18 00:00:00', '2014-01-19 00:00:00',
              '2014-01-01 09:40:00', 'nova usage audit', 4]]

        self.assertEquals(ast.literal_eval(actual_result), expected_result)
        self.mox.VerifyAll()

    def test_jsonreports_search_with_limit_offset(self):
        request = self.mox.CreateMockAnything()
        request.GET = {
            'period_start': '2014-01-01 09:40:00',
            'name': 'nova_usage_audit',
            'limit': 10,
            'offset': 5
        }
        filters = {
            'period_start__exact': '2014-01-01 09:40:00',
            'name__exact': 'nova_usage_audit',
        }
        self.mox.StubOutWithMock(stacky_server, 'model_search')
        stacky_server.model_search(request, self.model, filters,
                                   order_by='-id').AndReturn(
            [self.model_search_result])
        self.mox.ReplayAll()

        actual_result = stacky_server.do_jsonreports_search(request).content
        expected_result = \
            [['Id', 'Start', 'End', 'Created', 'Name', 'Version'],
             ['5975', '2014-01-18 00:00:00', '2014-01-19 00:00:00',
              '2014-01-01 09:40:00', 'nova usage audit', 4]]

        self.assertEquals(ast.literal_eval(actual_result), expected_result)
        self.mox.VerifyAll()

    def test_jsonreports_search_with_invalid_field_names_400(self):
        request = self.mox.CreateMockAnything()
        request.GET = {'invalid_column_1': 'value_1',
                       'invalid_column_2': 'value_2',
                       'period_start': '2014-01-01 00:00:00'}
        self.mox.ReplayAll()

        actual_result = stacky_server.do_jsonreports_search(request).content
        expected_result = \
        [
            ["Error", "Message"],
            ["Bad Request", "The requested fields do not exist for the "
             "corresponding object: invalid_column_1, invalid_column_2. Note: "
             "The field names of database are case-sensitive."]
        ]
        self.assertEqual(ast.literal_eval(actual_result), expected_result)
        self.mox.VerifyAll()

    def test_jsonreports_search_with_invalid_format_of_field_values_400(self):
        request = self.mox.CreateMockAnything()
        request.GET = {'period_start': '1234'}
        self.mox.ReplayAll()

        actual_result = stacky_server.do_jsonreports_search(request).content
        expected_result = \
        [
            ["Error", "Message"],
            ["Bad Request", "'1234' value has an invalid format. It must be in "
             "YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ] format."]
        ]
        self.assertEqual(ast.literal_eval(actual_result), expected_result)
        self.mox.VerifyAll()

    def test_jsonreports_search_by_created(self):
        request = self.mox.CreateMockAnything()
        request.GET = {
            'created': '2014-01-01 09:40:20'}
        filters = {
            'created__exact': 1388569220}
        self.mox.StubOutWithMock(stacky_server, 'model_search')
        stacky_server.model_search(request, self.model, filters,
                                   order_by='-id').AndReturn(
            [self.model_search_result])
        self.mox.ReplayAll()

        actual_result = stacky_server.do_jsonreports_search(request).content
        expected_result = \
            [['Id', 'Start', 'End', 'Created', 'Name', 'Version'],
             ['5975', '2014-01-18 00:00:00', '2014-01-19 00:00:00',
              '2014-01-01 09:40:00', 'nova usage audit', 4]]

        self.assertEquals(ast.literal_eval(actual_result), expected_result)
        self.mox.VerifyAll()

    def test_jsonreports_search_by_invalid_created_400(self):
        request = self.mox.CreateMockAnything()
        request.GET = {
            'created': '1234'}
        self.mox.ReplayAll()

        actual_result = stacky_server.do_jsonreports_search(request).content
        expected_result = \
        [
            ["Error", "Message"],
            ["Bad Request", "'1234' value has an invalid format. It must be in "
             "YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ] format."]
        ]
        self.assertEquals(ast.literal_eval(actual_result), expected_result)
        self.mox.VerifyAll()
