"""Unit tests for reviewboard.reviews.models.BaseComment.

Version Added:
    7.1
"""

from __future__ import annotations

import kgb
from django.db import models

from reviewboard.reviews.models import BaseComment
from reviewboard.reviews.signals import comment_issue_status_updated
from reviewboard.testing import TestCase


class BaseCommentTests(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.reviews.models.BaseComment.

    Version Added:
        7.1
    """

    fixtures = ['test_users']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request=review_request)
        self.review_request = review_request
        self.review_draft = review

    def test_save_kwargs(self) -> None:
        """Testing BaseComment.save passes its arguments to the parent save
        method
        """
        comment = self.create_general_comment(review=self.review_draft)

        self.spy_on(models.Model.save, owner=models.Model)

        comment.issue_opened = True
        comment.issue_status = BaseComment.OPEN

        comment.save(
            None,  # Passing `force_insert` as a positional argument.
            update_fields=['issue_opened', 'issue_status', 'timestamp'])

        self.assertSpyCalledWith(
            models.Model.save,
            force_insert=None,
            update_fields={'issue_opened', 'issue_status', 'timestamp'})

    def test_issue_updated_signal_with_created(self) -> None:
        """Testing comment creation does not emit the
        comment_issue_status_updated signal
        """
        def on_issue_status_updated(**kwargs) -> None:
            pass

        self.addCleanup(comment_issue_status_updated.disconnect,
                        on_issue_status_updated)

        comment_issue_status_updated.connect(on_issue_status_updated)
        self.spy_on(on_issue_status_updated)

        # Create a comment that opens an issue, and one that doesn't.
        self.create_general_comment(review=self.review_draft)
        self.create_general_comment(
            review=self.review_draft,
            issue_opened=True,
            issue_status=BaseComment.OPEN)

        self.assertSpyNotCalled(on_issue_status_updated)

    def test_issue_updated_signal_with_draft_update(self) -> None:
        """Testing updating the issue status on a draft comment does not
        emit the comment_issue_status_updated signal
        """
        def on_issue_status_updated(**kwargs) -> None:
            pass

        self.addCleanup(comment_issue_status_updated.disconnect,
                        on_issue_status_updated)

        comment = self.create_general_comment(
            review=self.review_draft,
            issue_opened=True,
            issue_status=BaseComment.OPEN)

        comment_issue_status_updated.connect(on_issue_status_updated)
        self.spy_on(on_issue_status_updated)

        comment.issue_status = BaseComment.DROPPED
        comment.save(update_fields=['issue_status'])

        self.assertSpyNotCalled(on_issue_status_updated)

    def test_issue_updated_signal_with_issue_dropped(self) -> None:
        """Testing dropping the issue on a published comment emits the
        comment_issue_status_updated signal
        """
        def on_issue_status_updated(**kwargs) -> None:
            pass

        self.addCleanup(comment_issue_status_updated.disconnect,
                        on_issue_status_updated)

        review_draft = self.review_draft
        comment = self.create_general_comment(
            review=review_draft,
            issue_opened=True,
            issue_status=BaseComment.OPEN)
        review_draft.publish()

        comment_issue_status_updated.connect(on_issue_status_updated)
        self.spy_on(on_issue_status_updated)

        comment.issue_status = BaseComment.DROPPED
        comment.save(update_fields=['issue_status'])

        self.assertSpyCalledWith(on_issue_status_updated,
                                 comment=comment,
                                 prev_status=BaseComment.OPEN,
                                 cur_status=BaseComment.DROPPED)

    def test_issue_updated_signal_with_issue_reopened(self) -> None:
        """Testing re-opening the issue on a published comment emits the
        comment_issue_status_updated signal
        """
        def on_issue_status_updated(**kwargs) -> None:
            pass

        self.addCleanup(comment_issue_status_updated.disconnect,
                        on_issue_status_updated)

        review_draft = self.review_draft
        comment = self.create_general_comment(
            review=review_draft,
            issue_opened=True,
            issue_status=BaseComment.OPEN)
        review_draft.publish()
        comment.issue_status = BaseComment.DROPPED
        comment.save(update_fields=['issue_status'])

        comment_issue_status_updated.connect(on_issue_status_updated)
        self.spy_on(on_issue_status_updated)

        comment.issue_status = BaseComment.OPEN
        comment.save(update_fields=['issue_status'])

        self.assertSpyCalledWith(on_issue_status_updated,
                                 comment=comment,
                                 prev_status=BaseComment.DROPPED,
                                 cur_status=BaseComment.OPEN)

    def test_issue_updated_signal_with_issue_resolved(self) -> None:
        """Testing resolving the issue on a published comment emits the
        comment_issue_status_updated signal
        """
        def on_issue_status_updated(**kwargs) -> None:
            pass

        self.addCleanup(comment_issue_status_updated.disconnect,
                        on_issue_status_updated)

        review_draft = self.review_draft
        comment = self.create_general_comment(
            review=review_draft,
            issue_opened=True,
            issue_status=BaseComment.OPEN)
        review_draft.publish()

        comment_issue_status_updated.connect(on_issue_status_updated)
        self.spy_on(on_issue_status_updated)

        comment.issue_status = BaseComment.RESOLVED
        comment.save(update_fields=['issue_status'])

        self.assertSpyCalledWith(on_issue_status_updated,
                                 comment=comment,
                                 prev_status=BaseComment.OPEN,
                                 cur_status=BaseComment.RESOLVED)
