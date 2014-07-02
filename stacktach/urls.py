# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from django.conf.urls import patterns, url

from stacktach import stacklog

stacklog.set_default_logger_name('stacktach-web')
web_logger = stacklog.get_logger('stacktach-web')
web_logger_listener = stacklog.LogListener(web_logger)
web_logger_listener.start()

web_urls = (
    url(r'^$', 'stacktach.views.welcome', name='welcome'),
    url(r'^(?P<deployment_id>\d+)/$', 'stacktach.views.home', name='home'),
    url(r'^(?P<deployment_id>\d+)/details/(?P<column>\w+)/(?P<row_id>\d+)/$',
        'stacktach.views.details', name='details'),
    url(r'^(?P<deployment_id>\d+)/search/$',
        'stacktach.views.search', name='search'),
    url(r'^(?P<deployment_id>\d+)/expand/(?P<row_id>\d+)/$',
        'stacktach.views.expand', name='expand'),
    url(r'^(?P<deployment_id>\d+)/latest_raw/$',
        'stacktach.views.latest_raw', name='latest_raw'),
    url(r'^(?P<deployment_id>\d+)/instance_status/$',
        'stacktach.views.instance_status', name='instance_status'),
)

stacky_urls = (
    url(r'^stacky/deployments/$', 'stacktach.stacky_server.do_deployments'),
    url(r'^stacky/events/$', 'stacktach.stacky_server.do_events'),
    url(r'^stacky/hosts/$', 'stacktach.stacky_server.do_hosts'),
    url(r'^stacky/uuid/$', 'stacktach.stacky_server.do_uuid'),
    url(r'^stacky/timings/$', 'stacktach.stacky_server.do_timings'),
    url(r'^stacky/timings/uuid/$', 'stacktach.stacky_server.do_timings_uuid'),
    url(r'^stacky/summary/$', 'stacktach.stacky_server.do_summary'),
    url(r'^stacky/request/$', 'stacktach.stacky_server.do_request'),
    url(r'^stacky/reports/search/$',
        'stacktach.stacky_server.do_jsonreports_search'),
    url(r'^stacky/reports/$', 'stacktach.stacky_server.do_jsonreports'),
    url(r'^stacky/report/(?P<report_id>\d+)/$',
                            'stacktach.stacky_server.do_jsonreport'),
    url(r'^stacky/show/(?P<event_id>\d+)/$',
                                        'stacktach.stacky_server.do_show'),
    url(r'^stacky/watch/(?P<deployment_id>\d+)/$',
                                        'stacktach.stacky_server.do_watch'),
    url(r'^stacky/search/$', 'stacktach.stacky_server.search'),
    url(r'^stacky/kpi/$', 'stacktach.stacky_server.do_kpi'),
    url(r'^stacky/kpi/(?P<tenant_id>\w+)/$', 'stacktach.stacky_server.do_kpi'),
    url(r'^stacky/usage/launches/$',
        'stacktach.stacky_server.do_list_usage_launches'),
    url(r'^stacky/usage/deletes/$',
        'stacktach.stacky_server.do_list_usage_deletes'),
    url(r'^stacky/usage/exists/$',
        'stacktach.stacky_server.do_list_usage_exists'),
)

dbapi_urls = (
    url(r'^db/usage/launches/$',
        'stacktach.dbapi.list_usage_launches'),
    url(r'^db/usage/nova/launches/$',
        'stacktach.dbapi.list_usage_launches'),
    url(r'^db/usage/glance/images/$',
        'stacktach.dbapi.list_usage_images'),
    url(r'^db/usage/launches/(?P<launch_id>\d+)/$',
        'stacktach.dbapi.get_usage_launch'),
    url(r'^db/usage/nova/launches/(?P<launch_id>\d+)/$',
        'stacktach.dbapi.get_usage_launch'),
    url(r'^db/usage/glance/images/(?P<image_id>\d+)/$',
        'stacktach.dbapi.get_usage_image'),
    url(r'^db/usage/deletes/$',
        'stacktach.dbapi.list_usage_deletes'),
    url(r'^db/usage/nova/deletes/$',
        'stacktach.dbapi.list_usage_deletes'),
    url(r'^db/usage/glance/deletes/$',
        'stacktach.dbapi.list_usage_deletes_glance'),
    url(r'^db/usage/deletes/(?P<delete_id>\d+)/$',
        'stacktach.dbapi.get_usage_delete'),
    url(r'^db/usage/nova/deletes/(?P<delete_id>\d+)/$',
        'stacktach.dbapi.get_usage_delete'),
    url(r'^db/usage/glance/deletes/(?P<delete_id>\d+)/$',
        'stacktach.dbapi.get_usage_delete_glance'),
    url(r'^db/usage/exists/$', 'stacktach.dbapi.list_usage_exists'),
    url(r'^db/usage/nova/exists/$', 'stacktach.dbapi.list_usage_exists'),
    url(r'^db/usage/glance/exists/$', 'stacktach.dbapi.list_usage_exists_glance'),
    url(r'^db/usage/exists/(?P<exist_id>\d+)/$',
        'stacktach.dbapi.get_usage_exist'),
    url(r'^db/usage/nova/exists/(?P<exist_id>\d+)/$',
        'stacktach.dbapi.get_usage_exist'),
    url(r'^db/usage/glance/exists/(?P<exist_id>\d+)/$',
        'stacktach.dbapi.get_usage_exist_glance'),
    url(r'^db/confirm/usage/exists/(?P<message_id>[\w\-]+)/$',
        'stacktach.dbapi.exists_send_status'),
    url(r'^db/stats/nova/exists/$',
        'stacktach.dbapi.get_usage_exist_stats'),
    url(r'^db/stats/glance/exists/$',
        'stacktach.dbapi.get_usage_exist_stats_glance'),
    url(r'^db/stats/events/', 'stacktach.dbapi.get_event_stats'),
    url(r'^db/repair/', 'stacktach.dbapi.repair_stacktach_down'),
)

urlpatterns = patterns('', *(web_urls + stacky_urls + dbapi_urls))
