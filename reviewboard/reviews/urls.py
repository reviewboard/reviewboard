from __future__ import unicode_literals

from django.conf.urls import include, patterns, url

from reviewboard.reviews.views import (ReviewsDiffFragmentView,
                                       ReviewsDiffViewerView)


download_diff_urls = patterns(
    'reviewboard.reviews.views',

    url(r'^orig/$', 'download_orig_file', name='download-orig-file'),
    url(r'^new/$', 'download_modified_file', name='download-modified-file'),
)

diffviewer_revision_urls = patterns(
    'reviewboard.reviews.views',

    url(r'^$',
        ReviewsDiffViewerView.as_view(),
        name="view-diff-revision"),

    url(r'^raw/$',
        'raw_diff',
        name='raw-diff-revision'),

    url(r'^fragment/(?P<filediff_id>[0-9]+)/'
        r'(chunk/(?P<chunk_index>[0-9]+)/)?$',
        ReviewsDiffFragmentView.as_view()),

    url(r'^download/(?P<filediff_id>[0-9]+)/', include(download_diff_urls)),
)

diffviewer_interdiff_urls = patterns(
    'reviewboard.reviews.views',

    url(r'^$',
        ReviewsDiffViewerView.as_view(),
        name="view-interdiff"),

    url(r'^fragment/(?P<filediff_id>[0-9]+)(-(?P<interfilediff_id>[0-9]+))?/'
        r'(chunk/(?P<chunk_index>[0-9]+)/)?$',
        ReviewsDiffFragmentView.as_view()),
)

diffviewer_urls = patterns(
    'reviewboard.reviews.views',

    url(r'^$', ReviewsDiffViewerView.as_view(), name="view-diff"),
    url(r'^raw/$', 'raw_diff', name='raw-diff'),

    url(r'^(?P<revision>[0-9]+)/', include(diffviewer_revision_urls)),
    url(r'^(?P<revision>[0-9]+)-(?P<interdiff_revision>[0-9]+)/',
        include(diffviewer_interdiff_urls)),
)

review_request_urls = patterns(
    'reviewboard.reviews.views',

    # Review request detail
    url(r'^$', 'review_detail', name="review-request-detail"),

    # Review request diffs
    url(r'^diff/', include(diffviewer_urls)),

    # Fragments
    url(r'^fragments/diff-comments/(?P<comment_ids>[0-9,]+)/$',
        'comment_diff_fragments'),

    # File attachments
    url(r'^file/(?P<file_attachment_id>[0-9]+)/$',
        'review_file_attachment',
        name='file-attachment'),

    # Screenshots
    url(r'^s/(?P<screenshot_id>[0-9]+)/$',
        'view_screenshot',
        name='screenshot'),

    # E-mail previews
    url(r'^preview-email/(?P<format>(text|html))/$',
        'preview_review_request_email',
        name='preview-review-request-email'),

    url(r'^changes/(?P<changedesc_id>[0-9]+)/preview-email/'
        r'(?P<format>(text|html))/$',
        'preview_review_request_email',
        name='preview-review-request-email'),

    url(r'^reviews/(?P<review_id>[0-9]+)/preview-email/'
        r'(?P<format>(text|html))/$',
        'preview_review_email',
        name='preview-review-email'),

    url(r'^reviews/(?P<review_id>[0-9]+)/replies/(?P<reply_id>[0-9]+)/'
        r'preview-email/(?P<format>(text|html))/$',
        'preview_reply_email',
        name='preview-review-reply-email'),
)

urlpatterns = patterns(
    'reviewboard.reviews.views',

    url(r'^new/$', 'new_review_request', name="new-review-request"),
    url(r'^(?P<review_request_id>[0-9]+)/', include(review_request_urls)),
)
