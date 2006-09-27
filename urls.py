from django.conf.urls.defaults import *
from reviewboard.reviews.models import ReviewRequest, Person, Group

HTDOC_URL = '//home/chipx86/src/reviewboard/htdocs'

urlpatterns = patterns('',
    (r'^admin/', include('django.contrib.admin.urls')),

    (r'css/(.*)$', 'django.views.static.serve',
     {'document_root': HTDOC_URL + '/css'}),
    (r'images/(.*)$', 'django.views.static.serve',
     {'document_root': HTDOC_URL + '/images'}),

    (r'^$', 'django.views.generic.list_detail.object_list',
     {'queryset':
      ReviewRequest.objects.filter(status='P').order_by('last_updated')[:25],
      'template_name': 'frontpage.html'}),

    (r'reviews/$', 'django.views.generic.list_detail.object_list',
     {'queryset': ReviewRequest.objects.all(),
      'template_name': 'reviews/review_list.html',
      'allow_empty': True}),
    (r'reviews/(?P<object_id>[0-9]+)/$',
     'django.views.generic.list_detail.object_detail',
     {'queryset': ReviewRequest.objects.all(),
      'template_name': 'reviews/review_detail.html'}),
    (r'reviews/new/$', 'reviewboard.reviews.views.new_review',
     {'template_name': 'reviews/new_review.html'}),

    (r'submitters/$', 'django.views.generic.list_detail.object_list',
     {'queryset': Person.objects.all(),
      'template_name': 'reviews/submitter_list.html',
      'allow_empty': True,
      'paginate_by': 50}),

    (r'submitters/(?P<username>[A-Za-z0-9_-]+)/$',
     'reviewboard.reviews.views.submitter',
     {'template_name': 'reviews/review_list.html',
      'paginate_by': 25}),

    (r'groups/$', 'django.views.generic.list_detail.object_list',
     {'queryset': Group.objects.all(),
      'template_name': 'reviews/group_list.html',
      'allow_empty': True,
      'paginate_by': 50}),

    (r'groups/(?P<name>[A-Za-z0-9_-]+)/$',
     'reviewboard.reviews.views.group',
     {'template_name': 'reviews/review_list.html',
      'paginate_by': 25}),
)
