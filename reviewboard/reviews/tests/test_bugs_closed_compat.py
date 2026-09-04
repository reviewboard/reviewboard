"""Tests for bugs_closed compatibility with migrated bug relations.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import ClassVar

from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.reviews.models import Bug
from reviewboard.reviews.models.bug import BUGS_MIGRATED_KEY
from reviewboard.testing import TestCase


class GetBugListCompatTests(TestCase):
    """Unit tests for marker-keyed get_bug_list reads.

    Version Added:
        9.0
    """

    fixtures: ClassVar[list[str]] = ['test_users', 'test_scmtools']

    def test_unmigrated_reads_string(self) -> None:
        """Testing get_bug_list on an unmigrated review request"""
        review_request = self.create_review_request()
        review_request.bugs_closed = '10, 2, 3'

        # Reads key on the migration marker.
        self.assertEqual(review_request.get_bug_list(),
                         ['2', '3', '10'])

    def test_migrated_reads_relations(self) -> None:
        """Testing get_bug_list on a migrated review request"""
        repository = self.create_repository()
        review_request = self.create_review_request(repository=repository)

        tracker = ConfiguredBugTracker.objects.create(name='Tracker',
                                                      service_name='splat')
        other_tracker = ConfiguredBugTracker.objects.create(
            name='Other',
            service_name='splat')
        repository.default_bug_tracker = tracker
        repository.save(update_fields=('default_bug_tracker',))

        sentinel = ConfiguredBugTracker.objects.get_sentinel()

        for bug_tracker, bug_id in ((tracker, '10'),
                                    (sentinel, '2'),
                                    (other_tracker, '99')):
            review_request.bugs.add(Bug.objects.get_or_create_bug(
                bug_tracker=bug_tracker,
                bug_id=bug_id))

        # The frozen string plays no part in the derived view.
        review_request.bugs_closed = '1,2,3'
        review_request.extra_data[BUGS_MIGRATED_KEY] = True

        # Bugs on other trackers never appear in the legacy view. Reads
        # key on the migration marker.
        self.assertEqual(review_request.get_bug_list(),
                         ['2', '10'])

    def test_migrated_without_default_tracker(self) -> None:
        """Testing get_bug_list on a migrated review request without a
        default tracker only shows unattributed bugs
        """
        review_request = self.create_review_request()

        tracker = ConfiguredBugTracker.objects.create(name='Tracker',
                                                      service_name='splat')
        sentinel = ConfiguredBugTracker.objects.get_sentinel()

        for bug_tracker, bug_id in ((tracker, '10'),
                                    (sentinel, '2')):
            review_request.bugs.add(Bug.objects.get_or_create_bug(
                bug_tracker=bug_tracker,
                bug_id=bug_id))

        review_request.extra_data[BUGS_MIGRATED_KEY] = True

        # Reads key on the migration marker.
        self.assertEqual(review_request.get_bug_list(), ['2'])
