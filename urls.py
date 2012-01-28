from django.conf import settings
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin
import django.contrib.auth.views

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = ('',
    url(r'^event$', 'track.views.user_track'),
    url(r'^t/(?P<template>[^/]*)$', 'static_template_view.views.index'),
    url(r'^logout$', 'auth.views.logout_user'),
    url(r'^info$', 'util.views.info'),
    url(r'^login$', 'auth.views.login_user'),
    url(r'^login/(?P<error>[^/]*)$', 'auth.views.login_user'),
    url(r'^create_account$', 'auth.views.create_account'),
    url(r'^activate/(?P<key>[^/]*)$', 'auth.views.activate_account'),
    url(r'^$', 'auth.views.index'),
    url(r'^password_reset/$', 'django.contrib.auth.views.password_reset', 
        dict(from_email='registration@mitx.mit.edu'),name='auth_password_reset'),
    url(r'^password_change/$',django.contrib.auth.views.password_change,name='auth_password_change'),
    url(r'^password_change_done/$',django.contrib.auth.views.password_change_done,name='auth_password_change_done'),
    url(r'^password_reset_confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',django.contrib.auth.views.password_reset_confirm,
        name='auth_password_reset_confirm'),
    url(r'^password_reset_complete/$',django.contrib.auth.views.password_reset_complete,
        name='auth_password_reset_complete'),
    url(r'^password_reset_done/$',django.contrib.auth.views.password_reset_done,
        name='auth_password_reset_done'),
    url(r'^send_feedback$', 'util.views.send_feedback'),
    url(r'^courseware/$', 'courseware.views.index'),
)

if settings.PERFSTATS:
   urlpatterns=urlpatterns + (url(r'^reprofile$','perfstats.views.end_profile'),)

if settings.COURSEWARE_ENABLED:
   urlpatterns=urlpatterns + (url(r'^wiki/', include('simplewiki.urls')),
   url(r'^courseware/(?P<course>[^/]*)/(?P<chapter>[^/]*)/(?P<section>[^/]*)/$', 'courseware.views.index'),
    url(r'^courseware/(?P<course>[^/]*)/(?P<chapter>[^/]*)/$', 'courseware.views.index'),
    url(r'^courseware/(?P<course>[^/]*)/$', 'courseware.views.index'),
    url(r'^modx/(?P<module>[^/]*)/(?P<id>[^/]*)/(?P<dispatch>[^/]*)$', 'courseware.views.modx_dispatch'), #reset_problem'),
    url(r'^profile$', 'courseware.views.profile'),
    url(r'^change_setting$', 'auth.views.change_setting'),
    url(r'^s/(?P<template>[^/]*)$', 'static_template_view.views.auth_index'),
    url(r'^book/(?P<page>[^/]*)$', 'staticbook.views.index'), 
    url(r'^book*$', 'staticbook.views.index'), 
#    url(r'^course_info/$', 'auth.views.courseinfo'),
#    url(r'^show_circuit/(?P<circuit>[^/]*)$', 'circuit.views.show_circuit'),
    url(r'^edit_circuit/(?P<circuit>[^/]*)$', 'circuit.views.edit_circuit'),
    url(r'^save_circuit/(?P<circuit>[^/]*)$', 'circuit.views.save_circuit'),
    url(r'^calculate$', 'util.views.calculate'),
)

if settings.ASKBOT_ENABLED:
   urlpatterns=urlpatterns + (url(r'^%s' % settings.ASKBOT_URL, include('askbot.urls')), \
                                 url(r'^admin/', include(admin.site.urls)), \
                                 url(r'^settings/', include('askbot.deps.livesettings.urls')), \
                                 url(r'^followit/', include('followit.urls')), \
#                                 url(r'^robots.txt$', include('robots.urls')),
                              )

urlpatterns = patterns(*urlpatterns)
