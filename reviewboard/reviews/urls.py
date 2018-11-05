from __future__ import unicode_literals

from django.conf.urls import include, url

from reviewboard.reviews import views


download_diff_urls = [
    url(r'^orig/$',
        views.DownloadDiffFileView.as_view(
            file_type=views.DownloadDiffFileView.TYPE_ORIG),
        name='download-orig-file'),

    url(r'^new/$',
        views.DownloadDiffFileView.as_view(
            file_type=views.DownloadDiffFileView.TYPE_MODIFIED),
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
        views.DownloadRawDiffView.as_view(),
        name='raw-diff-revision'),

    url(r'^fragment/(?P<filediff_id>\d+)/(?:chunk/(?P<chunk_index>\d+)/)?',
        include(diff_fragment_urls)),

    url(r'^download/(?P<filediff_id>\d+)/',
        include(download_diff_urls)),
]


diffviewer_interdiff_urls = [
    url(r'^$',
        views.ReviewsDiffViewerView.as_view(),
        name="view-interdiff"),

    url(r'^fragment/(?P<filediff_id>\d+)(?:-(?P<interfilediff_id>\d+))?/'
        r'(?:chunk/(?P<chunk_index>\d+)/)?',
        include(diff_fragment_urls)),
]


diffviewer_urls = [
    url(r'^$', views.ReviewsDiffViewerView.as_view(), name='view-diff'),

    url(r'^raw/$', views.DownloadRawDiffView.as_view(), name='raw-diff'),

    url(r'^(?P<revision>\d+)/',
        include(diffviewer_revision_urls)),

    url(r'^(?P<revision>\d+)-(?P<interdiff_revision>\d+)/',
        include(diffviewer_interdiff_urls)),
]


bugs_urls = [
    url(r'^$', views.BugURLRedirectView.as_view(), name='bug_url'),

    url(r'^infobox/$', views.BugInfoboxView.as_view(), name='bug_infobox'),
]


review_request_urls = [
    # Review request detail
    url(r'^$',
        views.ReviewRequestDetailView.as_view(),
        name='review-request-detail'),

    url(r'^_updates/$',
        views.ReviewRequestUpdatesView.as_view(),
        name='review-request-updates'),

    # Review request diffs
    url(r'^diff/', include(diffviewer_urls)),

    # Fragments
    url(r'^_fragments/diff-comments/(?P<comment_ids>[\d,]+)/$',
        views.CommentDiffFragmentsView.as_view(),
        name='diff-comment-fragments'),

    # File attachments
    url(r'^file/(?P<file_attachment_id>\d+)/$',
        views.ReviewFileAttachmentView.as_view(),
        name='file-attachment'),

    url(r'^file/(?P<file_attachment_diff_id>\d+)'
        r'-(?P<file_attachment_id>\d+)/$',
        views.ReviewFileAttachmentView.as_view(),
        name='file-attachment'),

    # Screenshots
    url(r'^s/(?P<screenshot_id>\d+)/$',
        views.ReviewScreenshotView.as_view(),
        name='screenshot'),

    # Bugs
    url(r'^bugs/(?P<bug_id>[\w\.-]+)/', include(bugs_urls)),

    # E-mail previews
    url(r'^preview-email/(?P<message_format>text|html)/$',
        views.PreviewReviewRequestEmailView.as_view(),
        name='preview-review-request-email'),

    url(r'^changes/(?P<changedesc_id>\d+)/preview-email/'
        r'(?P<message_format>text|html)/$',
        views.PreviewReviewRequestEmailView.as_view(),
        name='preview-review-request-email'),

    url(r'^reviews/(?P<review_id>\d+)/preview-email/'
        r'(?P<message_format>text|html)/$',
        views.PreviewReviewEmailView.as_view(),
        name='preview-review-email'),

    url(r'^reviews/(?P<review_id>\d+)/replies/(?P<reply_id>\d+)/'
        r'preview-email/(?P<message_format>text|html)/$',
        views.PreviewReplyEmailView.as_view(),
        name='preview-review-reply-email'),

    # Review Request infobox
    url(r'^infobox/$',
        views.ReviewRequestInfoboxView.as_view(),
        name='review-request-infobox'),
]


urlpatterns = [
    url(r'^new/$',
        views.NewReviewRequestView.as_view(),
        name='new-review-request'),

    url(r'^(?P<review_request_id>\d+)/',
        include(review_request_urls)),
]
