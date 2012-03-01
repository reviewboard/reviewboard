from django.conf.urls.defaults import patterns, url

from {{package_name}}.extension import {{class_name}}


urlpatterns = patterns('{{package_name}}.views',
    url(r'^$', 'configure'),
)

