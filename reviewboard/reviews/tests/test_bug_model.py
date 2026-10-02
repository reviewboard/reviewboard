"""Tests for reviewboard.reviews.models.bug.Bug.

Version Added:
    9.0
"""

from __future__ import annotations

from datetime import timedelta

import kgb
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from reviewboard.hostingsvcs.base.bug_tracker import BugInfo
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


class BugMetadataTests(kgb.SpyAgency, TestCase):
    """Unit tests for cached bug metadata."""

    fixtures = ['test_users']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.bug_tracker = ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='splat')

    def test_get_cached_bug_info(self) -> None:
        """Testing BugManager.get_cached_bug_info"""
        Bug.objects.create(bug_tracker=self.bug_tracker,
                           bug_id='123',
                           summary='A crash',
                           status='open',
                           metadata_timestamp=timezone.now())
        Bug.objects.create(bug_tracker=self.bug_tracker,
                           bug_id='456')

        metadata, stale_bug_ids = Bug.objects.get_cached_bug_info(
            bug_tracker=self.bug_tracker,
            bug_ids=['123', '456', '789'])

        self.assertEqual(metadata, {
            '123': {
                'status': 'open',
                'summary': 'A crash',
            },
        })
        self.assertEqual(stale_bug_ids, ['456', '789'])

    def test_get_cached_bug_info_with_stale_metadata(self) -> None:
        """Testing BugManager.get_cached_bug_info with stale metadata"""
        Bug.objects.create(
            bug_tracker=self.bug_tracker,
            bug_id='123',
            summary='A crash',
            status='open',
            metadata_timestamp=timezone.now() - timedelta(days=1))

        metadata, stale_bug_ids = Bug.objects.get_cached_bug_info(
            bug_tracker=self.bug_tracker,
            bug_ids=['123'])

        # The stale metadata is still returned, so it can be shown while
        # fresh metadata is fetched.
        self.assertEqual(metadata, {
            '123': {
                'status': 'open',
                'summary': 'A crash',
            },
        })
        self.assertEqual(stale_bug_ids, ['123'])

    def test_fetch_bug_info(self) -> None:
        """Testing BugManager.fetch_bug_info caches fetched metadata"""
        bug = Bug.objects.create(bug_tracker=self.bug_tracker, bug_id='123')

        self._spy_on_get_bugs_info()

        self.assertEqual(
            Bug.objects.fetch_bug_info(bug_tracker=self.bug_tracker,
                                       bug_ids=['123']),
            {
                '123': {
                    'status': 'open',
                    'summary': 'Bug 123',
                },
            })

        bug.refresh_from_db()

        self.assertEqual(bug.summary, 'Bug 123')
        self.assertEqual(bug.status, 'open')
        self.assertIsNotNone(bug.metadata_timestamp)

    def test_fetch_bug_info_with_multiple_bugs(self) -> None:
        """Testing BugManager.fetch_bug_info saves all refreshed bugs in
        one query
        """
        bug1 = Bug.objects.create(bug_tracker=self.bug_tracker, bug_id='123')
        bug2 = Bug.objects.create(bug_tracker=self.bug_tracker, bug_id='456')

        self._spy_on_get_bugs_info(bugs_info={
            '123': {
                'status': 'open',
                'summary': 'Bug 123',
            },
            '456': {
                'status': 'closed',
                'summary': 'Bug 456',
            },
        })

        # 1 query to fetch the rows, 1 to update them.
        with self.assertNumQueries(2):
            Bug.objects.fetch_bug_info(bug_tracker=self.bug_tracker,
                                       bug_ids=['123', '456'])

        bug1.refresh_from_db()
        bug2.refresh_from_db()

        self.assertEqual(bug1.summary, 'Bug 123')
        self.assertEqual(bug1.status, 'open')
        self.assertEqual(bug2.summary, 'Bug 456')
        self.assertEqual(bug2.status, 'closed')
        self.assertEqual(bug1.metadata_timestamp, bug2.metadata_timestamp)

    def test_fetch_bug_info_with_fresh_metadata(self) -> None:
        """Testing BugManager.fetch_bug_info does not contact the tracker
        for fresh metadata
        """
        Bug.objects.create(bug_tracker=self.bug_tracker,
                           bug_id='123',
                           summary='A crash',
                           status='open',
                           metadata_timestamp=timezone.now())

        spy = self._spy_on_get_bugs_info()

        self.assertEqual(
            Bug.objects.fetch_bug_info(bug_tracker=self.bug_tracker,
                                       bug_ids=['123']),
            {
                '123': {
                    'status': 'open',
                    'summary': 'A crash',
                },
            })

        self.assertSpyNotCalled(spy)

    def test_fetch_bug_info_without_row(self) -> None:
        """Testing BugManager.fetch_bug_info does not create rows"""
        self._spy_on_get_bugs_info()

        self.assertEqual(
            Bug.objects.fetch_bug_info(bug_tracker=self.bug_tracker,
                                       bug_ids=['123']),
            {
                '123': {
                    'status': 'open',
                    'summary': 'Bug 123',
                },
            })

        self.assertEqual(Bug.objects.count(), 0)

    def test_fetch_bug_info_without_bug_info_support(self) -> None:
        """Testing BugManager.fetch_bug_info with a tracker without bug
        info support
        """
        Bug.objects.create(bug_tracker=self.bug_tracker, bug_id='123')

        spy = self._spy_on_get_bugs_info(supports_bug_info=False)

        self.assertEqual(
            Bug.objects.fetch_bug_info(bug_tracker=self.bug_tracker,
                                       bug_ids=['123']),
            {})
        self.assertSpyNotCalled(spy)

    def test_fetch_bug_info_with_error(self) -> None:
        """Testing BugManager.fetch_bug_info with an error fetching
        metadata
        """
        Bug.objects.create(
            bug_tracker=self.bug_tracker,
            bug_id='123',
            summary='A crash',
            status='open',
            metadata_timestamp=(timezone.now() - timedelta(days=1)))

        service_cls = type(self.bug_tracker.service)

        self.spy_on(service_cls.get_bugs_info,
                    owner=service_cls,
                    op=kgb.SpyOpRaise(Exception('kaboom')))

        with self.assertLogs(logger='reviewboard.reviews.models.bug',
                             level='ERROR'):
            metadata = Bug.objects.fetch_bug_info(
                bug_tracker=self.bug_tracker,
                bug_ids=['123'])

        # The stale metadata is served rather than nothing.
        self.assertEqual(metadata, {
            '123': {
                'status': 'open',
                'summary': 'A crash',
            },
        })

    def test_fetch_bug_info_with_partial_error(self) -> None:
        """Testing BugManager.fetch_bug_info with an error fetching
        metadata for one bug
        """
        stale_timestamp = timezone.now() - timedelta(days=1)
        bug1 = Bug.objects.create(
            bug_tracker=self.bug_tracker,
            bug_id='123',
            summary='A crash',
            status='open',
            metadata_timestamp=stale_timestamp)
        bug2 = Bug.objects.create(
            bug_tracker=self.bug_tracker,
            bug_id='456',
            summary='A hang',
            status='open',
            metadata_timestamp=stale_timestamp)

        def _get_bug_info(
            _service: Splat,
            *args,
            bug_id: str,
            **kwargs,
        ) -> BugInfo:
            if bug_id == '123':
                raise Exception('kaboom')

            return {
                'description': '',
                'status': 'closed',
                'summary': 'A hang, fixed',
            }

        self.spy_on(Splat.get_bug_info,
                    owner=Splat,
                    call_fake=_get_bug_info)

        with self.assertLogs(logger='reviewboard.hostingsvcs.base.bug_tracker',
                             level='WARNING'):
            metadata = Bug.objects.fetch_bug_info(
                bug_tracker=self.bug_tracker,
                bug_ids=['123', '456'])

        # The failed bug falls back to its stale metadata, while the other
        # bug gets fresh metadata.
        self.assertEqual(metadata, {
            '123': {
                'status': 'open',
                'summary': 'A crash',
            },
            '456': {
                'status': 'closed',
                'summary': 'A hang, fixed',
            },
        })

        bug1.refresh_from_db()
        bug2.refresh_from_db()

        # The failed bug's row is left alone, so it stays stale and is
        # retried next time.
        self.assertEqual(bug1.summary, 'A crash')
        self.assertEqual(bug1.status, 'open')
        self.assertEqual(bug1.metadata_timestamp, stale_timestamp)

        self.assertEqual(bug2.summary, 'A hang, fixed')
        self.assertEqual(bug2.status, 'closed')
        self.assertGreater(bug2.metadata_timestamp, stale_timestamp)

    def _spy_on_get_bugs_info(
        self,
        supports_bug_info: bool = True,
        bugs_info: (dict[str, dict[str, str]] | None) = None,
    ) -> kgb.FunctionSpy:
        """Spy on the tracker's bulk metadata fetching.

        Args:
            supports_bug_info (bool, optional):
                Whether the service should report bug info support.

            bugs_info (dict, optional):
                The bug info the service should return. This defaults to
                info for a single bug, ``123``.

        Returns:
            kgb.FunctionSpy:
            The spy on the bulk fetch method.
        """
        if bugs_info is None:
            bugs_info = {
                '123': {
                    'description': '',
                    'status': 'open',
                    'summary': 'Bug 123',
                },
            }

        service_cls = type(self.bug_tracker.service)

        self.spy_on(
            service_cls.get_bugs_info,
            owner=service_cls,
            op=kgb.SpyOpReturn(bugs_info))

        old_value = service_cls.supports_bug_info
        service_cls.supports_bug_info = supports_bug_info
        self.addCleanup(setattr, service_cls, 'supports_bug_info', old_value)

        return service_cls.get_bugs_info.spy


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
