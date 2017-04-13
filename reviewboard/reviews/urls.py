from __future__ import unicode_literals

from django.conf.urls import include, url

from reviewboard.reviews import views


download_diff_urls = [
    url(r'^orig/$',
        views.download_orig_file,
        name='download-orig-file'),

    url(r'^new/$',
        views.download_modified_file,
        name='download-modified-file'),
]


diff_fragment_urls = [
    url(r'^$', views.ReviewsDiffFragmentView.as_view(),
        name='view-diff-fragment'),

    url(r'^patch-error-bundle/$',
        views.ReviewsDownloadPatchErrorBundleView.as_view(),
        name='patch-error-bundle'),
]


diffviewer_revision_urls = [
    url(r'^$',
        views.ReviewsDiffViewerView.as_view(),
        name="view-diff-revision"),

    url(r'^raw/$',
        views.raw_diff,
        name='raw-diff-revision'),

    url(r'^fragment/(?P<filediff_id>\d+)/(chunk/(?P<chunk_index>\d+)/)?',
        include(diff_fragment_urls)),

    url(r'^download/(?P<filediff_id>\d+)/',
        include(download_diff_urls)),
]


diffviewer_interdiff_urls = [
    url(r'^$',
        views.ReviewsDiffViewerView.as_view(),
        name="view-interdiff"),

    url(r'^fragment/(?P<filediff_id>\d+)(-(?P<interfilediff_id>\d+))?/'
        r'(chunk/(?P<chunk_index>\d+)/)?',
        include(diff_fragment_urls)),
]


diffviewer_urls = [
    url(r'^$', views.ReviewsDiffViewerView.as_view(), name='view-diff'),

    url(r'^raw/$', views.raw_diff, name='raw-diff'),

    url(r'^(?P<revision>\d+)/',
        include(diffviewer_revision_urls)),

    url(r'^(?P<revision>\d+)-(?P<interdiff_revision>\d+)/',
        include(diffviewer_interdiff_urls)),
]


bugs_urls = [
    url(r'^$', views.bug_url, name='bug_url'),

    url(r'^infobox/$', views.bug_infobox, name='bug_infobox'),
]


review_request_urls = [
    # Review request detail
    url(r'^$',
        views.review_detail,
        name='review-request-detail'),

    # Review request diffs
    url(r'^diff/', include(diffviewer_urls)),

    # Fragments
    url(r'^fragments/diff-comments/(?P<comment_ids>[\d,]+)/$',
        views.comment_diff_fragments),

    # File attachments
    url(r'^file/(?P<file_attachment_id>\d+)/$',
        views.review_file_attachment,
        name='file-attachment'),

    url(r'^file/(?P<file_attachment_diff_id>\d+)'
        r'-(?P<file_attachment_id>\d+)/$',
        views.review_file_attachment,
        name='file-attachment'),

    # Screenshots
    url(r'^s/(?P<screenshot_id>\d+)/$',
        views.view_screenshot,
        name='screenshot'),

    # Bugs
    url(r'^bugs/(?P<bug_id>[\w\.-]+)/', include(bugs_urls)),

    # E-mail previews
    url(r'^preview-email/(?P<format>(text|html))/$',
        views.preview_review_request_email,
        name='preview-review-request-email'),

    url(r'^changes/(?P<changedesc_id>\d+)/preview-email/'
        r'(?P<format>(text|html))/$',
        views.preview_review_request_email,
        name='preview-review-request-email'),

    url(r'^reviews/(?P<review_id>\d+)/preview-email/'
        r'(?P<format>(text|html))/$',
        views.preview_review_email,
        name='preview-review-email'),

    url(r'^reviews/(?P<review_id>\d+)/replies/(?P<reply_id>\d+)/'
        r'preview-email/(?P<format>(text|html))/$',
        views.preview_reply_email,
        name='preview-review-reply-email'),
]


urlpatterns = [
    url(r'^new/$',
        views.new_review_request,
        name='new-review-request'),

    url(r'^(?P<review_request_id>\d+)/',
        include(review_request_urls)),
]
