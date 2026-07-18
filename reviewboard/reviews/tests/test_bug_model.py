"""Tests for reviewboard.reviews.models.bug.Bug.

Version Added:
    9.0
"""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.reviews.models import Bug
from reviewboard.testing import TestCase


class BugTests(TestCase):
    """Unit tests for the Bug model.

    Version Added:
        9.0
    """

    fixtures = ['test_users']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.bug_tracker = ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='splat')

    def test_unique_together(self) -> None:
        """Testing Bug uniqueness on (bug_tracker, bug_id)"""
        Bug.objects.create(bug_tracker=self.bug_tracker, bug_id='123')

        with transaction.atomic(), self.assertRaises(IntegrityError):
            Bug.objects.create(bug_tracker=self.bug_tracker,
                               bug_id='123')

        other_tracker = ConfiguredBugTracker.objects.create(
            name='Other Tracker',
            service_name='splat')

        # The same ID on another tracker is a distinct bug.
        Bug.objects.create(bug_tracker=other_tracker, bug_id='123')

    def test_get_or_create_bug(self) -> None:
        """Testing BugManager.get_or_create_bug"""
        bug1 = Bug.objects.get_or_create_bug(bug_tracker=self.bug_tracker,
                                             bug_id='123')
        bug2 = Bug.objects.get_or_create_bug(bug_tracker=self.bug_tracker,
                                             bug_id='123')

        self.assertEqual(bug1.pk, bug2.pk)
        self.assertEqual(Bug.objects.count(), 1)

    def test_bug_tracker_delete_protected(self) -> None:
        """Testing deleting a ConfiguredBugTracker with bugs is protected"""
        Bug.objects.create(bug_tracker=self.bug_tracker, bug_id='123')

        with self.assertRaises(ProtectedError):
            self.bug_tracker.delete()

    def test_review_request_bugs_m2m(self) -> None:
        """Testing linking bugs to review requests and drafts"""
        review_request = self.create_review_request()
        draft = self.create_review_request_draft(review_request)

        bug = Bug.objects.create(bug_tracker=self.bug_tracker, bug_id='123')

        review_request.bugs.add(bug)
        draft.bugs.add(bug)

        self.assertEqual(list(bug.review_requests.all()), [review_request])
        self.assertEqual(list(bug.drafts.all()), [draft])
        self.assertEqual(
            list(review_request.bugs.values_list('bug_id', flat=True)),
            ['123'])
