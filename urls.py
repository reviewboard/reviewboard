from django.conf import settings
from django.conf.urls.defaults import *
from reviewboard.reviews.models import ReviewRequest, Person, Group
from reviewboard.reviews.feeds import RssReviewsFeed, RssSubmittersFeed
from reviewboard.reviews.feeds import AtomReviewsFeed, AtomSubmittersFeed

rss_feeds = {
    'reviews': RssReviewsFeed,
    'submitters': RssSubmittersFeed,
}

atom_feeds = {
    'reviews': AtomReviewsFeed,
    'submitters': AtomSubmittersFeed,
}

urlpatterns = patterns('',
    (r'^admin/', include('django.contrib.admin.urls')),

    (r'^css/(.*)$', 'django.views.static.serve',
     {'document_root': settings.HTDOCS_ROOT + '/css'}),
    (r'^images/(.*)$', 'django.views.static.serve',
     {'document_root': settings.HTDOCS_ROOT + '/images'}),

    (r'^$', 'django.views.generic.simple.redirect_to',
     {'url': '/reviews/'}),

    (r'^reviews/$', 'reviewboard.reviews.views.review_list',
     {'queryset': ReviewRequest.objects.all(),
      'template_name': 'reviews/review_list.html'}),

    (r'^reviews/new/$', 'reviewboard.reviews.views.new_review_request',
     {'template_name': 'reviews/new.html'}),

    (r'^reviews/(?P<object_id>[0-9]+)/$',
     'django.views.generic.list_detail.object_detail',
     {'queryset': ReviewRequest.objects.all(),
      'template_name': 'reviews/review_detail.html'}),

    (r'^reviews/new/$', 'reviewboard.reviews.views.new_review',
     {'template_name': 'reviews/new_review.html'}),

    (r'^submitters/$', 'reviewboard.reviews.views.submitter_list',
     {'template_name': 'reviews/submitter_list.html'}),

    (r'^submitters/(?P<username>[A-Za-z0-9_-]+)/$',
     'reviewboard.reviews.views.submitter',
     {'template_name': 'reviews/review_list.html'}),

    (r'^groups/$', 'reviewboard.reviews.views.group_list',
     {'template_name': 'reviews/group_list.html'}),

    (r'^groups/(?P<name>[A-Za-z0-9_-]+)/$',
     'reviewboard.reviews.views.group',
     {'template_name': 'reviews/review_list.html',
      'paginate_by': 25}),

    # Feeds
    (r'^feeds/rss/(?P<url>.*)/$', 'django.contrib.syndication.views.feed',
     {'feed_dict': rss_feeds}),
    (r'^feeds/atom/(?P<url>.*)/$', 'django.contrib.syndication.views.feed',
     {'feed_dict': atom_feeds}),
)
