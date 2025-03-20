"""Unit tests for ReviewRequestPageData."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional, Sequence, TYPE_CHECKING

from django.contrib.auth.models import User
from django.db.models import Q
from django.template import RequestContext
from django.test.client import RequestFactory
from django.utils import timezone

from reviewboard.accounts.models import Profile
from reviewboard.attachments.models import (FileAttachment,
                                            FileAttachmentHistory)
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.hostingsvcs.github import GitHub
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.reviews.detail import (BaseReviewRequestPageEntry,
                                        ChangeEntry,
                                        InitialStatusUpdatesEntry,
                                        ReviewEntry,
                                        ReviewRequestEntry,
                                        ReviewRequestPageData)
from reviewboard.reviews.models import (BaseComment,
                                        Review,
                                        ReviewRequestDraft,
                                        Screenshot,
                                        StatusUpdate)
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from djblets.db.query_comparator import ExpectedQuery

    from reviewboard.reviews.models import (Comment,
                                            FileAttachmentComment,
                                            GeneralComment,
                                            ScreenshotComment)


class ReviewRequestPageDataTests(TestCase):
    """Unit tests for ReviewRequestPageData."""

    fixtures = ['test_scmtools', 'test_users']

    ######################
    # Instance variables #
    ######################

    #: The test comments created.
    #:
    #: This covers all comment types.
    #:
    #: Version Added:
    #:     7.1
    all_comments: list[BaseComment]

    #: The test change descriptions created.
    #:
    #: Version Added:
    #:     7.1
    changedescs: list[ChangeDescription]

    #: The test diff comments created.
    #:
    #: Version Added:
    #:     7.1
    diff_comments: list[Comment]

    #: The test DiffSets created.
    #:
    #: Version Added:
    #:     7.1
    diffsets: list[DiffSet]

    #: The test draft created.
    draft: Optional[ReviewRequestDraft]

    #: The test file attachment comments created.
    #:
    #: Version Added:
    #:     7.1
    file_attachment_comments: list[FileAttachmentComment]

    #: The test file attachments created.
    #:
    #: Version Added:
    #:     7.1
    file_attachments: list[FileAttachment]

    #: The test FileDiffs created.
    #:
    #: Version Added:
    #:     7.1
    filediffs: list[FileDiff]

    #: The test general comments created.
    #:
    #: Version Added:
    #:     7.1
    general_comments: list[GeneralComment]

    #: The test inactive file attachments created.
    #:
    #: Version Added:
    #:     7.1
    inactive_screenshots: list[Screenshot]

    #: The test inactive screenshots created.
    #:
    #: Version Added:
    #:     7.1
    inactive_file_attachments: list[FileAttachment]

    #: The test issue counts created.
    #:
    #: Version Added:
    #:     7.1
    issue_counts: dict[str, int]

    #: The test reviews created.
    #:
    #: Version Added:
    #:     7.1
    reviews: list[Review]

    #: The test screenshot comments created.
    #:
    #: Version Added:
    #:     7.1
    screenshot_comments: list[ScreenshotComment]

    #: The test screenshots created.
    #:
    #: Version Added:
    #:     7.1
    screenshots: list[Screenshot]

    #: The test status updates created.
    #:
    #: Version Added:
    #:     7.1
    status_updates: list[StatusUpdate]

    def test_query_data_pre_etag(self) -> None:
        """Testing ReviewRequestPageData.query_data_pre_etag"""
        self._populate_review_request()

        self._test_query_data_pre_etag_with(
            expected_queries=lambda: [
                {
                    'model': Review,
                    'order_by': ('-timestamp',),
                    'select_related': {'user'},
                    'where': (
                        Q(review_request=self.review_request) &
                        (Q(public=True) |
                         Q(user_id=2))
                    ),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_changedescs': 'INNER JOIN',
                    },
                    'model': ChangeDescription,
                    'num_joins': 1,
                    'tables': {
                        'changedescs_changedescription',
                        'reviews_reviewrequest_changedescs',
                    },
                    'where': (
                        Q(review_request__id=1) &
                        Q(public=True)
                    ),
                },
                {
                    'model': ReviewRequestDraft,
                    'where': Q(review_request=self.review_request),
                },
                {
                    'model': DiffSet,
                    'where': Q(history__pk=1),
                },
                {
                    'model': FileDiff,
                    'where': Q(diffset__in=list(DiffSet.objects.all())),
                },
                {
                    'model': StatusUpdate,
                    'order_by': ('summary',),
                    'where': Q(review_request=self.review_request),
                },
            ],
            expect_diffs=True,
            expect_reviews=True,
            expect_changedescs=True,
            expect_draft=True,
            expect_status_updates=True)

    def test_query_data_pre_etag_with_only_review_request_entry(self) -> None:
        """Testing ReviewRequestPageData.query_data_pre_etag with only
        ReviewRequestEntry in entry_classes
        """
        self._populate_review_request()

        self._test_query_data_pre_etag_with(
            entry_classes=[ReviewRequestEntry],
            expected_queries=lambda: [
                {
                    'model': Review,
                    'order_by': ('-timestamp',),
                    'select_related': {'user'},
                    'where': (
                        Q(review_request=self.review_request) &
                        (Q(public=True) |
                         Q(user_id=2))
                    ),
                },
                {
                    'model': ReviewRequestDraft,
                    'where': Q(review_request=self.review_request),
                },
                {
                    'model': DiffSet,
                    'where': Q(history__pk=1),
                },
                {
                    'model': FileDiff,
                    'where': Q(diffset__in=list(DiffSet.objects.all())),
                },
            ],
            expect_diffs=True,
            expect_reviews=True,
            expect_draft=True)

    def test_query_data_pre_etag_with_only_initial_status_updates_entry(
        self,
    ) -> None:
        """Testing ReviewRequestPageData.query_data_pre_etag with only
        InitialStatusUpdatesEntry in entry_classes
        """
        self._populate_review_request()

        self._test_query_data_pre_etag_with(
            entry_classes=[InitialStatusUpdatesEntry],
            expected_queries=lambda: [
                {
                    'model': Review,
                    'order_by': ('-timestamp',),
                    'select_related': {'user'},
                    'where': (
                        Q(review_request=self.review_request) &
                        (Q(public=True) |
                         Q(user_id=2))
                    ),
                },
                {
                    'model': DiffSet,
                    'where': Q(history__pk=1),
                },
                {
                    'model': FileDiff,
                    'where': Q(diffset__in=list(DiffSet.objects.all())),
                },
                {
                    'model': StatusUpdate,
                    'order_by': ('summary',),
                    'where': Q(review_request=self.review_request),
                },
            ],
            expect_diffs=True,
            expect_reviews=True,
            expect_status_updates=True)

    def test_query_data_pre_etag_with_only_review_entry(self) -> None:
        """Testing ReviewRequestPageData.query_data_pre_etag with only
        ReviewEntry in entry_classes
        """
        self._populate_review_request()

        self._test_query_data_pre_etag_with(
            entry_classes=[ReviewEntry],
            expected_queries=lambda: [
                {
                    'model': Review,
                    'order_by': ('-timestamp',),
                    'select_related': {'user'},
                    'where': (
                        Q(review_request=self.review_request) &
                        (Q(public=True) |
                         Q(user_id=2))
                    ),
                },
                {
                    'model': DiffSet,
                    'where': Q(history__pk=1),
                },
                {
                    'model': FileDiff,
                    'where': Q(diffset__in=self.diffsets),
                },
            ],
            expect_diffs=True,
            expect_reviews=True)

    def test_query_data_pre_etag_with_only_change_entry(self) -> None:
        """Testing ReviewRequestPageData.query_data_pre_etag with only
        ChangeEntry in entry_classes
        """
        self._populate_review_request()

        self._test_query_data_pre_etag_with(
            entry_classes=[ChangeEntry],
            expected_queries=lambda: [
                {
                    'model': Review,
                    'order_by': ('-timestamp',),
                    'select_related': {'user'},
                    'where': (
                        Q(review_request=self.review_request) &
                        (Q(public=True) |
                         Q(user_id=2))
                    ),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_changedescs': 'INNER JOIN',
                    },
                    'model': ChangeDescription,
                    'num_joins': 1,
                    'tables': {
                        'changedescs_changedescription',
                        'reviews_reviewrequest_changedescs',
                    },
                    'where': (
                        Q(review_request__id=self.review_request.pk) &
                        Q(public=True)
                    ),
                },
                {
                    'model': DiffSet,
                    'where': Q(history__pk=1),
                },
                {
                    'model': FileDiff,
                    'where': Q(diffset__in=list(DiffSet.objects.all())),
                },
                {
                    'model': StatusUpdate,
                    'order_by': ('summary',),
                    'where': Q(review_request=self.review_request),
                },
            ],
            expect_diffs=True,
            expect_reviews=True,
            expect_changedescs=True,
            expect_status_updates=True)

    def test_query_data_pre_etag_with_no_changedescs(self) -> None:
        """Testing ReviewRequestPageData.query_data_pre_etag with no
        change descriptions
        """
        self._populate_review_request(enable_changedescs=False)

        self._test_query_data_pre_etag_with(
            expected_queries=lambda: [
                {
                    'model': Review,
                    'order_by': ('-timestamp',),
                    'select_related': {'user'},
                    'where': (
                        Q(review_request=self.review_request) &
                        (Q(public=True) |
                         Q(user_id=2))
                    ),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_changedescs': 'INNER JOIN',
                    },
                    'model': ChangeDescription,
                    'num_joins': 1,
                    'tables': {
                        'changedescs_changedescription',
                        'reviews_reviewrequest_changedescs',
                    },
                    'where': (
                        Q(review_request__id=self.review_request.pk) &
                        Q(public=True)
                    ),
                },
                {
                    'model': ReviewRequestDraft,
                    'where': Q(review_request=self.review_request),
                },
                {
                    'model': DiffSet,
                    'where': Q(history__pk=1),
                },
                {
                    'model': FileDiff,
                    'where': Q(diffset__in=list(DiffSet.objects.all())),
                },
                {
                    'model': StatusUpdate,
                    'order_by': ('summary',),
                    'where': Q(review_request=self.review_request),
                },
            ],
            expect_diffs=True,
            expect_draft=True,
            expect_reviews=True,
            expect_status_updates=True)

    def test_query_data_pre_etag_with_no_diffs(self) -> None:
        """Testing ReviewRequestPageData.query_data_pre_etag with no diffs"""
        self._populate_review_request(enable_diffs=False)

        self._test_query_data_pre_etag_with(
            expected_queries=lambda: [
                {
                    'model': Review,
                    'order_by': ('-timestamp',),
                    'select_related': {'user'},
                    'where': (
                        Q(review_request=self.review_request) &
                        (Q(public=True) |
                         Q(user_id=2))
                    ),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_changedescs': 'INNER JOIN',
                    },
                    'model': ChangeDescription,
                    'num_joins': 1,
                    'tables': {
                        'changedescs_changedescription',
                        'reviews_reviewrequest_changedescs',
                    },
                    'where': (
                        Q(review_request__id=self.review_request.pk) &
                        Q(public=True)
                    ),
                },
                {
                    'model': ReviewRequestDraft,
                    'where': Q(review_request=self.review_request),
                },
                {
                    'model': StatusUpdate,
                    'order_by': ('summary',),
                    'where': Q(review_request=self.review_request),
                },
            ],
            expect_changedescs=True,
            expect_draft=True,
            expect_reviews=True,
            expect_status_updates=True)

    def test_query_data_pre_etag_with_no_reviews(self) -> None:
        """Testing ReviewRequestPageData.query_data_pre_etag with no reviews"""
        self._populate_review_request(enable_reviews=False)

        self._test_query_data_pre_etag_with(
            expected_queries=lambda: [
                {
                    'model': Review,
                    'order_by': ('-timestamp',),
                    'select_related': {'user'},
                    'where': (
                        Q(review_request=self.review_request) &
                        (Q(public=True) |
                         Q(user_id=2))
                    ),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_changedescs': 'INNER JOIN',
                    },
                    'model': ChangeDescription,
                    'num_joins': 1,
                    'tables': {
                        'changedescs_changedescription',
                        'reviews_reviewrequest_changedescs',
                    },
                    'where': (
                        Q(review_request__id=self.review_request.pk) &
                        Q(public=True)
                    ),
                },
                {
                    'model': ReviewRequestDraft,
                    'where': Q(review_request=self.review_request),
                },
                {
                    'model': DiffSet,
                    'where': Q(history__pk=1),
                },
                {
                    'model': FileDiff,
                    'where': Q(diffset__in=list(DiffSet.objects.all())),
                },
                {
                    'model': StatusUpdate,
                    'order_by': ('summary',),
                    'where': Q(review_request=self.review_request),
                },
            ],
            expect_diffs=True,
            expect_draft=True,
            expect_changedescs=True,
            expect_status_updates=True)

    def test_query_data_post_etag(self) -> None:
        """Testing ReviewRequestPageData.query_data_post_etag"""
        self._populate_review_request()

        self._test_query_data_post_etag_with(
            expected_queries=lambda: [
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_file_attachments':
                            'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequestdraft_file_attachments',
                    },
                    'where': Q(drafts__id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=2),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=3),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=4),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=5),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=6),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=7),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=8),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=9),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=10),
                },
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_inactive_file_attachments':
                            'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequestdraft_inactive_file_attachments',
                    },
                    'where': Q(inactive_drafts__id=1),
                },
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_screenshots': 'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequestdraft_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(drafts__id=1),
                },
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_inactive_screenshots':
                            'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequestdraft_inactive_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(inactive_drafts__id=1),
                },
                {
                    'model': Review.general_comments.through,
                    'order_by': ('generalcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.screenshot_comments.through,
                    'order_by': ('screenshotcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.file_attachment_comments.through,
                    'order_by': ('fileattachmentcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.comments.through,
                    'order_by': ('comment__filediff',
                                 'comment__first_line',
                                 'comment__timestamp'),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
            ],
            expect_reviews=True,
            expect_file_attachments=True,
            expect_screenshots=True,
            expect_draft=True,
            expect_comments=True,
            expect_issues=True)

    def test_query_data_post_etag_with_only_review_request_entry(self) -> None:
        """Testing ReviewRequestPageData.query_data_post_etag with only
        ReviewRequestEntry in entry_classes
        """
        self._populate_review_request()

        self._test_query_data_post_etag_with(
            entry_classes=[ReviewRequestEntry],
            expected_queries=lambda: [
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_file_attachments':
                            'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequestdraft_file_attachments',
                    },
                    'where': Q(drafts__id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=2),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=3),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=4),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=5),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=6),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=7),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=8),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=9),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=10),
                },
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_inactive_file_attachments':
                            'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequestdraft_inactive_file_attachments',
                    },
                    'where': Q(inactive_drafts__id=1),
                },
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_screenshots': 'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequestdraft_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(drafts__id=1),
                },
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_inactive_screenshots':
                            'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequestdraft_inactive_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(inactive_drafts__id=1),
                },
                {
                    'model': Review.general_comments.through,
                    'order_by': ('generalcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.screenshot_comments.through,
                    'order_by': ('screenshotcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.file_attachment_comments.through,
                    'order_by': ('fileattachmentcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.comments.through,
                    'order_by': ('comment__filediff',
                                 'comment__first_line',
                                 'comment__timestamp'),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
            ],
            expect_draft=True,
            expect_reviews=True,
            expect_file_attachments=True,
            expect_screenshots=True,
            expect_comments=True,
            expect_issues=True)

    def test_query_data_post_etag_with_only_initial_status_updates_entry(
        self,
    ) -> None:
        """Testing ReviewRequestPageData.query_data_post_etag with only
        InitialStatusUpdatesEntry in entry_classes
        """
        self._populate_review_request()

        self._test_query_data_post_etag_with(
            entry_classes=[InitialStatusUpdatesEntry],
            expected_queries=lambda: [
                {
                    'join_types': {
                        'reviews_reviewrequest_file_attachments':
                            'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequest_file_attachments',
                    },
                    'where': Q(review_request__id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=2),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=3),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=4),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=5),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=6),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=7),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=8),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=9),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=10),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_inactive_file_attachments':
                            'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequest_inactive_file_attachments',
                    },
                    'where': Q(inactive_review_request__id=1),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_screenshots': 'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequest_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(review_request__id=1),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_inactive_screenshots':
                            'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequest_inactive_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(inactive_review_request__id=1),
                },
                {
                    'model': Review.general_comments.through,
                    'order_by': ('generalcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.screenshot_comments.through,
                    'order_by': ('screenshotcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.file_attachment_comments.through,
                    'order_by': ('fileattachmentcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.comments.through,
                    'order_by': ('comment__filediff',
                                 'comment__first_line',
                                 'comment__timestamp'),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
            ],
            expect_reviews=True,
            expect_file_attachments=True,
            expect_screenshots=True,
            expect_comments=True,
            expect_issues=True)

    def test_query_data_post_etag_with_only_review_entry(self) -> None:
        """Testing ReviewRequestPageData.query_data_post_etag with only
        ReviewEntry in entry_classes
        """
        self._populate_review_request()

        self._test_query_data_post_etag_with(
            entry_classes=[ReviewEntry],
            expected_queries=lambda: [
                {
                    'join_types': {
                        'reviews_reviewrequest_file_attachments': 'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequest_file_attachments',
                    },
                    'where': Q(review_request__id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=2),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=3),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=4),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=5),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=6),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=7),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=8),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=9),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=10),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_inactive_file_attachments':
                            'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequest_inactive_file_attachments',
                    },
                    'where': Q(inactive_review_request__id=1),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_screenshots': 'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequest_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(review_request__id=1),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_inactive_screenshots':
                            'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequest_inactive_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(inactive_review_request__id=1),
                },
                {
                    'model': Review.general_comments.through,
                    'order_by': ('generalcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.screenshot_comments.through,
                    'order_by': ('screenshotcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.file_attachment_comments.through,
                    'order_by': ('fileattachmentcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.comments.through,
                    'order_by': ('comment__filediff',
                                 'comment__first_line',
                                 'comment__timestamp'),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
            ],
            expect_reviews=True,
            expect_file_attachments=True,
            expect_screenshots=True,
            expect_comments=True,
            expect_issues=True)

    def test_query_data_post_etag_with_only_change_entry(self) -> None:
        """Testing ReviewRequestPageData.query_data_post_etag with only
        ChangeEntry in entry_classes
        """
        self._populate_review_request()

        self._test_query_data_post_etag_with(
            entry_classes=[ChangeEntry],
            expected_queries=lambda: [
                {
                    'join_types': {
                        'reviews_reviewrequest_file_attachments': 'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequest_file_attachments',
                    },
                    'where': Q(review_request__id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=2),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=3),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=4),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=5),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=6),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=7),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=8),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=9),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=10),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_inactive_file_attachments':
                            'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequest_inactive_file_attachments',
                    },
                    'where': Q(inactive_review_request__id=1),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_screenshots': 'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequest_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(review_request__id=1),
                },
                {
                    'join_types': {
                        'reviews_reviewrequest_inactive_screenshots':
                            'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequest_inactive_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(inactive_review_request__id=1),
                },
                {
                    'model': Review.general_comments.through,
                    'order_by': ('generalcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.screenshot_comments.through,
                    'order_by': ('screenshotcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.file_attachment_comments.through,
                    'order_by': ('fileattachmentcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.comments.through,
                    'order_by': ('comment__filediff',
                                 'comment__first_line',
                                 'comment__timestamp'),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
            ],
            expect_reviews=True,
            expect_file_attachments=True,
            expect_screenshots=True,
            expect_comments=True,
            expect_issues=True)

    def test_query_data_post_etag_with_no_comments(self) -> None:
        """Testing ReviewRequestPageData.query_data_post_etag with no
        comments
        """
        self._populate_review_request(
            enable_diff_comments=False,
            enable_file_attachment_comments=False,
            enable_general_comments=False,
            enable_screenshot_comments=False)

        self._test_query_data_post_etag_with(
            expected_queries=lambda: [
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_file_attachments':
                            'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequestdraft_file_attachments',
                    },
                    'where': Q(drafts__id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=2),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=3),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=4),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=5),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=6),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=7),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=8),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=9),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=10),
                },
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_inactive_file_attachments':
                            'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequestdraft_inactive_file_attachments',
                    },
                    'where': Q(inactive_drafts__id=1),
                },
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_screenshots': 'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequestdraft_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(drafts__id=1),
                },
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_inactive_screenshots':
                            'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequestdraft_inactive_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(inactive_drafts__id=1),
                },
                {
                    'model': Review.general_comments.through,
                    'order_by': ('generalcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.screenshot_comments.through,
                    'order_by': ('screenshotcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.file_attachment_comments.through,
                    'order_by': ('fileattachmentcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.comments.through,
                    'order_by': ('comment__filediff',
                                 'comment__first_line',
                                 'comment__timestamp'),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
            ],
            expect_reviews=True,
            expect_file_attachments=True,
            expect_screenshots=True,
            expect_draft=True,
            expect_comments=True,
            expect_issues=True)

    def test_query_data_post_etag_with_no_file_attachments(self) -> None:
        """Testing ReviewRequestPageData.query_data_post_etag with no
        file attachments
        """
        self._populate_review_request(enable_file_attachments=False)

        self._test_query_data_post_etag_with(
            expected_queries=lambda: [
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_screenshots': 'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequestdraft_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(drafts__id=1),
                },
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_inactive_screenshots':
                            'INNER JOIN',
                    },
                    'model': Screenshot,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequestdraft_inactive_screenshots',
                        'reviews_screenshot',
                    },
                    'where': Q(inactive_drafts__id=1),
                },
                {
                    'model': Review.general_comments.through,
                    'order_by': ('generalcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.screenshot_comments.through,
                    'order_by': ('screenshotcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.file_attachment_comments.through,
                    'order_by': ('fileattachmentcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.comments.through,
                    'order_by': ('comment__filediff',
                                 'comment__first_line',
                                 'comment__timestamp'),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
            ],
            expect_reviews=True,
            expect_screenshots=True,
            expect_draft=True,
            expect_comments=True,
            expect_issues=True)

    def test_query_data_post_etag_with_no_screenshots(self) -> None:
        """Testing ReviewRequestPageData.query_data_post_etag with no
        screenshots
        """
        self._populate_review_request(enable_screenshots=False)

        self._test_query_data_post_etag_with(
            expected_queries=lambda: [
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_file_attachments':
                            'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequestdraft_file_attachments',
                    },
                    'where': Q(drafts__id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=1),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=2),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=3),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=4),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=5),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=6),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=7),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=8),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=9),
                },
                {
                    'model': FileAttachmentHistory,
                    'where': Q(id=10),
                },
                {
                    'join_types': {
                        'reviews_reviewrequestdraft_inactive_file_attachments':
                            'INNER JOIN',
                    },
                    'model': FileAttachment,
                    'num_joins': 1,
                    'tables': {
                        'attachments_fileattachment',
                        'reviews_reviewrequestdraft_inactive_file_attachments',
                    },
                    'where': Q(inactive_drafts__id=1),
                },
                {
                    'model': Review.general_comments.through,
                    'order_by': ('generalcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.screenshot_comments.through,
                    'order_by': ('screenshotcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.file_attachment_comments.through,
                    'order_by': ('fileattachmentcomment__timestamp',),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
                {
                    'model': Review.comments.through,
                    'order_by': ('comment__filediff',
                                 'comment__first_line',
                                 'comment__timestamp'),
                    'select_related': True,
                    'where': Q(review__in=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
                },
            ],
            expect_reviews=True,
            expect_file_attachments=True,
            expect_draft=True,
            expect_comments=True,
            expect_issues=True)

    def test_get_entries(self) -> None:
        """Testing ReviewRequestPageData.get_entries"""
        self._populate_review_request()

        data = self._build_data()
        data.query_data_pre_etag()
        data.query_data_post_etag()

        queries: list[ExpectedQuery] = [
            {
                'model': User,
                'where': Q(id=2),
            },
            {
                'model': User,
                'where': Q(id=2),
            },
            {
                'model': User,
                'where': Q(id=2),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'model': ChangeDescription,
                'num_joins': 1,
                'order_by': ('-pk',),
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': (
                    Q(review_request__id=1) &
                    Q(pk__lt=3)
                ),
            },
            {
                'model': ChangeDescription,
                'type': 'UPDATE',
                'where': Q(pk=3),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'model': ChangeDescription,
                'num_joins': 1,
                'order_by': ('-pk',),
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': (
                    Q(review_request__id=1) &
                    Q(pk__lt=2)
                ),
            },
            {
                'model': ChangeDescription,
                'type': 'UPDATE',
                'where': Q(pk=2),
            },
        ]

        with self.assertQueries(queries):
            entries = data.get_entries()

        initial_entries = entries['initial']
        main_entries = entries['main']
        reviews = self.reviews
        changedescs = self.changedescs

        self.assertEqual(len(initial_entries), 1)
        self.assertEqual(len(main_entries), len(reviews) + len(changedescs))

        entry = initial_entries[0]
        self.assertIsInstance(entry, InitialStatusUpdatesEntry)

        for i in range(len(reviews)):
            entry = main_entries[i]
            assert isinstance(entry, ReviewEntry)
            self.assertEqual(entry.review, reviews[i])

        start = len(reviews)

        for i in range(len(changedescs)):
            entry = main_entries[start + i]
            assert isinstance(entry, ChangeEntry)
            self.assertEqual(entry.changedesc, changedescs[i])

    def test_rendering(self) -> None:
        """Testing ReviewRequestPageData entries rendering"""
        # We're testing a render across all the entries in order to see
        # if we're generating too many SQL queries.
        self._populate_review_request()

        data = self._build_data()
        data.query_data_pre_etag()
        data.query_data_post_etag()

        request = data.request
        context = RequestContext(request)

        owner = self.review_request.owner
        reviewer = self.reviews[0].user
        viewer = request.user

        # Ensure users have profiles for the test, to avoid excess queries.
        owner.get_profile()
        reviewer.get_profile()
        viewer.get_profile()

        entries = data.get_entries()

        queries: list[ExpectedQuery] = [
            {
                'model': Profile,
                'where': Q(user=reviewer)
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'model': Profile,
                'where': Q(user=reviewer)
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'model': Profile,
                'where': Q(user=reviewer)
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'model': Profile,
                'where': Q(user=reviewer)
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'model': Profile,
                'where': Q(user=reviewer)
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'model': Profile,
                'where': Q(user=reviewer)
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'model': Profile,
                'where': Q(user=reviewer)
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'model': Profile,
                'where': Q(user=reviewer)
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'model': Profile,
                'where': Q(user=reviewer)
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'model': Profile,
                'where': Q(user=reviewer)
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'model': Profile,
                'where': Q(user=owner)
            },
            {
                'model': Profile,
                'where': Q(user=owner)
            },
            {
                'model': Profile,
                'where': Q(user=owner)
            },
        ]

        with self.assertQueries(queries):
            for key in ('initial', 'main'):
                for entry in entries[key]:
                    entry.render_to_string(request=request,
                                           context=context)

    def _build_data(
        self,
        entry_classes: Optional[
            Sequence[type[BaseReviewRequestPageEntry]]
        ] = None,
    ) -> ReviewRequestPageData:
        """Build the data to test against.

        This will build the page data to test against. It must be run
        after populating review request data.

        Args:
            entry_classes (list of type, optional):
                The list of entry classes available for the page data.

        Returns:
            reviewboard.reviews.detail.ReviewRequestPageData:
            The resulting page data.
        """
        request = RequestFactory().get('/r/1/')
        request.user = self.review_request.submitter

        return ReviewRequestPageData(review_request=self.review_request,
                                     request=request,
                                     entry_classes=entry_classes)

    def _test_query_data_pre_etag_with(
        self,
        *,
        expected_queries: Callable[[], Sequence[ExpectedQuery]],
        entry_classes: Optional[
            Sequence[type[BaseReviewRequestPageEntry]]
        ] = None,
        expect_changedescs: bool = False,
        expect_diffs: bool = False,
        expect_draft: bool = False,
        expect_reviews: bool = False,
        expect_status_updates: bool = False,
    ) -> None:
        """Perform a test of state from pre-ETag calculations.

        Version Changed:
            7.1:
            Added the following argument: ``expected_queries``,
            ``expect_diffs``.

        Args:
            expected_queries (callable):
                A function returning a list of expected queries.

                Version Added:
                    7.1

            entry_classes (list of type, optional):
                The list of entry classes available for the page data.

            expect_changedescs (bool, optional):
                Whether to expect change descriptions in the results.

            expect_diffs (bool, optional):
                Whether to expect diffs in the results.

                Version Added:
                    7.1

            expect_draft (bool, optional):
                Whether to expect a review request draft in the results.

            expect_reviews (bool, optional):
                Whether to expect reviews in the results.

            expect_status_updates (bool, optional):
                Whether to expect status updates in the results.
        """
        data = self._build_data(entry_classes=entry_classes)

        with self.assertQueries(expected_queries()):
            data.query_data_pre_etag()

        if expect_reviews:
            self.assertEqual(data.reviews, self.reviews[::-1])
            self.assertEqual(data.latest_review_timestamp,
                             self.reviews[-1].timestamp)
        else:
            self.assertEqual(data.reviews, [])
            self.assertEqual(data.latest_review_timestamp,
                             datetime.fromtimestamp(0, timezone.utc))

        if expect_diffs:
            self.assertEqual(data.diffsets, self.diffsets)
            self.assertEqual(
                data.diffsets_by_id,
                {
                    pk: diffset
                    for pk, diffset in enumerate(self.diffsets, start=1)
                })
        else:
            self.assertEqual(data.diffsets, [])
            self.assertEqual(data.diffsets_by_id, {})

        if expect_changedescs:
            self.assertEqual(data.changedescs, self.changedescs[::-1])
            self.assertEqual(data.latest_changedesc_timestamp,
                             self.changedescs[-1].timestamp)
        else:
            self.assertEqual(data.changedescs, [])
            self.assertIsNone(data.latest_changedesc_timestamp)

        if expect_draft:
            self.assertEqual(data.draft, self.draft)
        else:
            self.assertIsNone(data.draft)

        if expect_status_updates:
            self.assertEqual(data.all_status_updates, self.status_updates)
        else:
            self.assertEqual(data.all_status_updates, [])

    def _test_query_data_post_etag_with(
        self,
        *,
        expected_queries: Callable[[], Sequence[ExpectedQuery]],
        entry_classes: Optional[
            Sequence[type[BaseReviewRequestPageEntry]]
        ] = None,
        expect_comments: bool = False,
        expect_draft: bool = False,
        expect_file_attachments: bool = False,
        expect_issues: bool = False,
        expect_reviews: bool = False,
        expect_screenshots: bool = False,
    ) -> None:
        """Perform a test of state from post-ETag calculations.

        Version Changed:
            7.1:
            Added the following argument: ``expected_queries``,

        Args:
            expected_queries (callable):
                A function returning a list of expected queries.

                Version Added:
                    7.1

            entry_classes (list of type, optional):
                The list of entry classes available for the page data.

            expect_comments (bool, optional):
                Whether to expect comments in the results.

            expect_draft (bool, optional):
                Whether to expect a review request draft in the results.

            expect_file_attachments (bool, optional):
                Whether to expect file attachments in the results.

            expect_issues (bool, optional):
                Whether to expect filed issues in the results.

            expect_reviews (bool, optional):
                Whether to expect reviews in the results.

            expect_screenshots (bool, optional):
                Whether to expect screenshots in the results.
        """
        data = self._build_data(entry_classes=entry_classes)

        data.query_data_pre_etag()

        with self.assertQueries(expected_queries()):
            data.query_data_post_etag()

        if expect_reviews:
            self.assertEqual(
                data.reviews_by_id,
                {
                    pk: review
                    for pk, review in enumerate(self.reviews, start=1)
                })
        else:
            self.assertEqual(data.reviews_by_id, {})

        if expect_draft:
            self.assertEqual(data.review_request_details, self.draft)
        else:
            self.assertEqual(data.review_request_details,
                             self.review_request)

        if expect_file_attachments:
            all_expected_file_attachments = \
                self.file_attachments + self.inactive_file_attachments

            self.assertEqual(data.active_file_attachments,
                             self.file_attachments)
            self.assertEqual(data.all_file_attachments,
                             all_expected_file_attachments)
            self.assertEqual(
                data.file_attachments_by_id,
                {
                    pk: file_attachment
                    for pk, file_attachment in enumerate(
                        all_expected_file_attachments,
                        start=1)
                })
        else:
            self.assertEqual(data.active_file_attachments, [])
            self.assertEqual(data.all_file_attachments, [])
            self.assertEqual(data.file_attachments_by_id, {})

        if expect_screenshots:
            all_expected_screenshots = \
                self.screenshots + self.inactive_screenshots

            self.assertEqual(data.active_screenshots, self.screenshots)
            self.assertEqual(data.all_screenshots, all_expected_screenshots)
            self.assertEqual(
                data.screenshots_by_id,
                {
                    pk: screenshot
                    for pk, screenshot in enumerate(
                        all_expected_screenshots,
                        start=1)
                })
        else:
            self.assertEqual(data.active_screenshots, [])
            self.assertEqual(data.all_screenshots, [])
            self.assertEqual(data.screenshots_by_id, {})

        if expect_comments:
            self.assertEqual(data.all_comments, self.all_comments)
        else:
            self.assertEqual(data.all_comments, [])

        if expect_issues:
            self.assertEqual(
                data.issues,
                [
                    comment
                    for comment in self.all_comments
                    if comment.issue_opened
                ])
            self.assertEqual(data.issue_counts, self.issue_counts)
        else:
            self.assertEqual(data.issues, [])
            self.assertEqual(data.issue_counts, {})

    def _populate_review_request(
        self,
        *,
        enable_changedescs: bool = True,
        enable_diff_comments: bool = True,
        enable_diffs: bool = True,
        enable_draft: bool = True,
        enable_file_attachment_comments: bool = True,
        enable_file_attachments: bool = True,
        enable_general_comments: bool = True,
        enable_reviews: bool = True,
        enable_screenshot_comments: bool = True,
        enable_screenshots: bool = True,
        enable_status_updates: bool = True,
    ) -> None:
        """Populate review request state to test against.

        Version Changed:
            7.1:
            Added the following arguments: ``enable_changedescs``,
            ``enable_diff_comments``, ``enable_diffs``, ``enable_draft``,
            ``enable_file_attachment_comments``, ``enable_file_attachments``,
            ``enable_general_comments``, ``enable_reviews``,
            ``enable_screenshot_comments``, ``enable_screenshots``,
            ``enable_status_updates``.

        Args:
            enable_changedescs (bool, optional):
                Whether to enable change descriptions in the database.

                Version Added:
                    7.1

            enable_diff_comments (bool, optional):
                Whether to enable diff comments in the database.

                Version Added:
                    7.1

            enable_diffs (bool, optional):
                Whether to enable diffs in the database.

                Version Added:
                    7.1

            enable_draft (bool, optional):
                Whether to enable a draft for the revie request in the
                database.

            enable_file_attachment_comments (bool, optional):
                Whether to enable file attachment comments in the database.

                Version Added:
                    7.1

            enable_file_attachments (bool, optional):
                Whether to enable file attachments in the database.

                Version Added:
                    7.1

            enable_general_comments (bool, optional):
                Whether to enable general comments in the database.

                Version Added:
                    7.1

            enable_reviews (bool, optional):
                Whether to enable reviews in the database.

                Version Added:
                    7.1

            enable_screenshot_comments (bool, optional):
                Whether to enable screenshot comments in the database.

                Version Added:
                    7.1

            enable_screenshots (bool, optional):
                Whether to enable screenshots in the database.

                Version Added:
                    7.1

            enable_status_updates (bool, optional):
                Whether to enable Status Updates in the database.

                Version Added:
                    7.1
        """
        now = timezone.now()
        days_offset: int = 0

        # Create the review request, diffs, attachments, and screenshots.
        if enable_diffs:
            account = HostingServiceAccount.objects.create(
                service_name=GitHub.hosting_service_id,
                username='foo')
            repository = self.create_repository(hosting_account=account)
        else:
            repository = None

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.review_request = review_request

        user = review_request.owner

        #: Create the diff data.
        diffsets: list[DiffSet] = []
        filediffs: list[FileDiff] = []

        if enable_diffs:
            diffsets = [
                self.create_diffset(review_request)
                for i in range(10)
            ]

            filediffs = [
                self.create_filediff(diffset)
                for diffset in diffsets
            ]

        self.diffsets = diffsets
        self.filediffs = filediffs

        # Create the file attachments.
        file_attachments: list[FileAttachment] = []
        inactive_file_attachments: list[FileAttachment] = []

        if enable_file_attachments:
            file_attachments = [
                self.create_file_attachment(review_request)
                for i in range(10)
            ]

            inactive_file_attachments = [
                self.create_file_attachment(review_request, active=False)
                for i in range(5)
            ]

        self.file_attachments = file_attachments
        self.inactive_file_attachments = inactive_file_attachments

        # Create the screenshots.
        screenshots: list[Screenshot] = []
        inactive_screenshots: list[Screenshot] = []

        if enable_screenshots:
            screenshots = [
                self.create_screenshot(review_request)
                for i in range(10)
            ]

            inactive_screenshots = [
                self.create_screenshot(review_request, active=False)
                for i in range(5)
            ]

        self.screenshots = screenshots
        self.inactive_screenshots = inactive_screenshots

        # Create a draft for this review request.
        if enable_draft:
            draft = ReviewRequestDraft.create(review_request)
        else:
            draft = None

        self.draft = draft

        # Create some reviews.
        diff_comments: list[Comment] = []
        general_comments: list[GeneralComment] = []
        screenshot_comments: list[ScreenshotComment] = []
        file_attachment_comments: list[FileAttachmentComment] = []
        reviews: list[Review] = []
        issue_counts = {
            'dropped': 0,
            'open': 0,
            'resolved': 0,
            'total': 0,
            'verifying': 0,
        }

        if enable_reviews:
            # We'll create alternating pairs of reviews with two different
            # sets of state.
            for i in range(0, 10, 2):
                # First review in the pair.
                timestamp = now + timedelta(days=days_offset)
                review = self.create_review(
                    review_request,
                    timestamp=timestamp,
                    publish=True)
                reviews.append(review)
                days_offset += 1

                if enable_general_comments:
                    general_comments.append(
                        self.create_general_comment(
                            review,
                            issue_opened=True,
                            issue_status=BaseComment.OPEN,
                            timestamp=timestamp))
                    issue_counts['open'] += 1
                    issue_counts['total'] += 1

                if enable_diffs and enable_diff_comments:
                    diff_comments.append(
                        self.create_diff_comment(
                            review,
                            filediffs[i],
                            issue_opened=True,
                            issue_status=BaseComment.RESOLVED,
                            timestamp=timestamp))
                    issue_counts['resolved'] += 1
                    issue_counts['total'] += 1

                if enable_file_attachments and enable_file_attachment_comments:
                    file_attachment_comments.append(
                        self.create_file_attachment_comment(
                            review,
                            file_attachments[i],
                            issue_opened=True,
                            issue_status=BaseComment.DROPPED,
                            timestamp=timestamp))
                    issue_counts['dropped'] += 1
                    issue_counts['total'] += 1

                if enable_screenshots and enable_screenshot_comments:
                    screenshot_comments.append(
                        self.create_screenshot_comment(
                            review,
                            screenshots[i],
                            issue_opened=False,
                            timestamp=timestamp))

                # Second review in the pair.
                timestamp = now + timedelta(days=days_offset)
                review = self.create_review(
                    review_request,
                    timestamp=timestamp,
                    publish=True)
                reviews.append(review)
                days_offset += 1
                i += 1

                if enable_general_comments:
                    general_comments.append(
                        self.create_general_comment(
                            review,
                            issue_opened=True,
                            issue_status=BaseComment.OPEN,
                            timestamp=timestamp))
                    issue_counts['open'] += 1
                    issue_counts['total'] += 1

                if enable_diffs and enable_diff_comments:
                    diff_comments.append(
                        self.create_diff_comment(
                            review,
                            filediffs[i],
                            issue_opened=True,
                            issue_status=BaseComment.RESOLVED,
                            timestamp=timestamp))
                    issue_counts['resolved'] += 1
                    issue_counts['total'] += 1

                if enable_file_attachments and enable_file_attachment_comments:
                    file_attachment_comments.append(
                        self.create_file_attachment_comment(
                            review,
                            file_attachments[i],
                            issue_opened=True,
                            issue_status=BaseComment.DROPPED,
                            timestamp=timestamp))
                    issue_counts['dropped'] += 1
                    issue_counts['total'] += 1

                if enable_screenshots and enable_screenshot_comments:
                    screenshot_comments.append(
                        self.create_screenshot_comment(
                            review,
                            screenshots[i],
                            issue_opened=False,
                            timestamp=timestamp))

        self.all_comments = [
            *general_comments,
            *screenshot_comments,
            *file_attachment_comments,
            *diff_comments,
        ]
        self.diff_comments = diff_comments
        self.general_comments = general_comments
        self.file_attachment_comments = file_attachment_comments
        self.screenshot_comments = screenshot_comments
        self.issue_counts = issue_counts
        self.reviews = reviews

        # Create some change descriptions.
        #
        # Only the second will have a user assigned (simulating older
        # change descriptions).
        changedescs: list[ChangeDescription] = []

        if enable_changedescs:
            for i in range(2):
                changedescs.append(review_request.changedescs.create(
                    timestamp=now + timedelta(days=days_offset + i),
                    public=True))

            days_offset += 2

            for i in range(3):
                changedescs.append(review_request.changedescs.create(
                    timestamp=now + timedelta(days=days_offset + i),
                    public=True,
                    user=user))

            days_offset += 3

        self.changedescs = changedescs

        # Create some status updates.
        status_updates: list[StatusUpdate] = []

        if enable_status_updates:
            status_updates += [
                self.create_status_update(review_request),
                self.create_status_update(review_request),
            ]

        self.status_updates = status_updates
