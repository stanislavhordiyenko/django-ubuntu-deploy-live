from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns('',
    url(r'^$', views.list, name='list'),
    url(r'^(?P<slug>[\w-]+)/$', views.view, name='view'),
)