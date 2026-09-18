"""Tests for reviewboard.reviews.models.bug.Bug.

Version Added:
    9.0
"""

from __future__ import annotations

import kgb
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.hostingsvcs.splat import Splat
from reviewboard.reviews.models import Bug
from reviewboard.reviews.models.bug import sort_bug_ids
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

        self.bug_tracker = self.create_bug_tracker()

    def test_unique_together(self) -> None:
        """Testing Bug uniqueness on (bug_tracker, bug_id)"""
        Bug.objects.create(bug_tracker=self.bug_tracker, bug_id='123')

        with transaction.atomic(), self.assertRaises(IntegrityError):
            Bug.objects.create(bug_tracker=self.bug_tracker,
                               bug_id='123')

        other_tracker = self.create_bug_tracker(name='Other Tracker')

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


class SortBugIDsTests(kgb.SpyAgency, TestCase):
    """Unit tests for sort_bug_ids.

    Version Added:
        9.0
    """

    def test_numeric(self) -> None:
        """Testing sort_bug_ids with numeric IDs"""
        self.assertEqual(sort_bug_ids(['12', '4', '100']),
                         ['4', '12', '100'])

    def test_non_numeric(self) -> None:
        """Testing sort_bug_ids with non-numeric IDs"""
        self.assertEqual(sort_bug_ids(['ENG-5', 'ENG-12', '4']),
                         ['4', 'ENG-12', 'ENG-5'])

    def test_with_tracker_service_keys(self) -> None:
        """Testing sort_bug_ids with a service providing sort keys"""
        tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='splat')

        self.spy_on(
            Splat.get_bug_id_sort_key,
            owner=Splat,
            op=kgb.SpyOpMatchAny([
                {
                    'kwargs': {'bug_id': 'ENG-5'},
                    'op': kgb.SpyOpReturn(('ENG', 5)),
                },
                {
                    'kwargs': {'bug_id': 'ENG-12'},
                    'op': kgb.SpyOpReturn(('ENG', 12)),
                },
                {
                    'kwargs': {'bug_id': 'APP-3'},
                    'op': kgb.SpyOpReturn(('APP', 3)),
                },
            ]))

        self.assertEqual(
            sort_bug_ids(['ENG-12', 'APP-3', 'ENG-5'], tracker=tracker),
            ['APP-3', 'ENG-5', 'ENG-12'])

    def test_with_partial_service_keys(self) -> None:
        """Testing sort_bug_ids falls back when any ID has no key"""
        tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='splat')

        self.spy_on(
            Splat.get_bug_id_sort_key,
            owner=Splat,
            op=kgb.SpyOpMatchAny([
                {
                    'kwargs': {'bug_id': 'ENG-5'},
                    'op': kgb.SpyOpReturn(('ENG', 5)),
                },
                {
                    'kwargs': {'bug_id': 'weird'},
                    'op': kgb.SpyOpReturn(None),
                },
            ]))

        self.assertEqual(
            sort_bug_ids(['weird', 'ENG-5'], tracker=tracker),
            ['ENG-5', 'weird'])

    def test_with_sentinel_tracker(self) -> None:
        """Testing sort_bug_ids with the sentinel tracker"""
        tracker = ConfiguredBugTracker.objects.get_sentinel()

        self.assertEqual(sort_bug_ids(['12', '4'], tracker=tracker),
                         ['4', '12'])

    def test_with_missing_service(self) -> None:
        """Testing sort_bug_ids with an unregistered service"""
        tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='xxx-unknown')

        self.assertEqual(sort_bug_ids(['12', '4'], tracker=tracker),
                         ['4', '12'])
