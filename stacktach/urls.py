from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'stacktach.views.welcome', name='welcome'),
    url(r'new_tenant', 'stacktach.views.new_tenant', name='new_tenant'),
    url(r'logout', 'stacktach.views.logout', name='logout'),
    url(r'^(?P<tenant_id>\d+)/$', 'stacktach.views.home', name='home'),
    url(r'^(?P<tenant_id>\d+)/data/$', 'stacktach.views.data',
        name='data'),
    url(r'^(?P<tenant_id>\d+)/details/(?P<column>\w+)/(?P<row_id>\d+)/$',
        'stacktach.views.details', name='details'),
    url(r'^(?P<tenant_id>\d+)/expand/(?P<row_id>\d+)/$',
        'stacktach.views.expand', name='expand'),
    url(r'^(?P<tenant_id>\d+)/host_status/$', 
        'stacktach.views.host_status', name='host_status'),
    url(r'^(?P<tenant_id>\d+)/instance_status/$',
        'stacktach.views.instance_status', name='instance_status'),
)
