from django.conf.urls.defaults import patterns


urlpatterns = patterns('reviewboard.reports.views',
    (r'^$', 'report_list'),
    (r'^(?P<username>[A-Za-z0-9_-]+)/review_request/(?P<format>[a-z]+)/$',
      'review_request'),
    (r'^(?P<username>[A-Za-z0-9_-]+)/review/(?P<format>[a-z]+)/$', 'review'),
    (r'^(?P<username>[A-Za-z0-9_-]+)/status_report/(?P<format>[a-z]+)/$',
      'status_report'),
)
