from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'dss.stackmon.views.welcome', name='welcome'),
    url(r'new_tenant', 'dss.stackmon.views.new_tenant', name='new_tenant'),
    url(r'logout', 'dss.stackmon.views.logout', name='logout'),
    url(r'^(?P<tenant_id>\d+)/$', 'dss.stackmon.views.home', name='home'),
    url(r'^(?P<tenant_id>\d+)/data/$', 'dss.stackmon.views.data',
        name='data'),
    url(r'^(?P<tenant_id>\d+)/details/(?P<column>\w+)/(?P<row_id>\d+)/$',
        'dss.stackmon.views.details', name='details'),
    url(r'^(?P<tenant_id>\d+)/expand/(?P<row_id>\d+)/$',
        'dss.stackmon.views.expand', name='expand'),
    url(r'^(?P<tenant_id>\d+)/host_status/$', 
        'dss.stackmon.views.host_status', name='host_status'),
    url(r'^(?P<tenant_id>\d+)/instance_status/$',
        'dss.stackmon.views.instance_status', name='instance_status'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)
