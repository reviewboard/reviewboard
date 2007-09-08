from django.conf.urls.defaults import patterns


urlpatterns = patterns('',
    (r'^$', 'reviewboard.reports.views.report_list'),
    (r'^(?P<username>[A-Za-z0-9_-]+)/review_request/(?P<format>[a-z]+)/$', 'reviewboard.reports.views.review_request'),
    (r'^(?P<username>[A-Za-z0-9_-]+)/review/(?P<format>[a-z]+)/$', 'reviewboard.reports.views.review'),
    (r'^(?P<username>[A-Za-z0-9_-]+)/status_report/(?P<format>[a-z]+)/$', 'reviewboard.reports.views.status_report'),
)
