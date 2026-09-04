"""Tests for bugs_closed compatibility with migrated bug relations.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING
from urllib.parse import urlencode

from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.reviews.models import (
    Bug,
    ReviewRequest,
    ReviewRequestDraft,
)
from reviewboard.reviews.models.bug import BUGS_MIGRATED_KEY
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from typing import Any

    from typelets.json import JSONDict


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


class LegacyBugWriteCompatTests(TestCase):
    """Unit tests for legacy bugs_closed writes through the API.

    Version Added:
        9.0
    """

    fixtures = ['test_users', 'test_scmtools']

    def _api_put_draft(
        self,
        review_request: ReviewRequest,
        fields: dict[str, Any],
    ) -> JSONDict:
        """PUT to a review request's draft API resource.

        Args:
            review_request (ReviewRequest):
                The review request to update the draft of.

            fields (dict):
                The field values to send.

        Returns:
            dict:
            The JSON response payload.
        """
        response = self.client.put(
            f'/api/review-requests/{review_request.pk}/draft/',
            data=urlencode(fields),
            content_type='application/x-www-form-urlencoded')

        self.assertEqual(response.status_code, 200)

        return response.json()

    def test_write_materializes_bug_relations(self) -> None:
        """Testing a bugs_closed API write materializes bug relations"""
        repository = self.create_repository()
        review_request = self.create_review_request(
            repository=repository,
            submitter='doc',
            publish=True)

        tracker = ConfiguredBugTracker.objects.create(name='Tracker',
                                                      service_name='splat')
        repository.default_bug_tracker = tracker
        repository.save(update_fields=('default_bug_tracker',))

        self.client.login(username='doc', password='doc')

        rsp = self._api_put_draft(review_request, {'bugs_closed': '4,2'})

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['draft']['bugs_closed'],  # type:ignore
            ['2', '4'])

        draft = ReviewRequestDraft.objects.get(
            review_request=review_request)
        self.assertTrue(draft.extra_data.get(BUGS_MIGRATED_KEY))
        self.assertEqual(
            sorted(draft.bugs.values_list('bug_id', flat=True)),
            ['2', '4'])
        self.assertEqual(
            list(draft.bugs.values_list('bug_tracker', flat=True).distinct()),
            [tracker.pk])

        # The stored string is never written for migrated drafts.
        self.assertEqual(draft.bugs_closed, '')

    def test_write_without_default_tracker_uses_sentinel(self) -> None:
        """Testing a bugs_closed API write without a default tracker
        attributes bugs to the sentinel
        """
        review_request = self.create_review_request(submitter='doc',
                                                    publish=True)

        self.client.login(username='doc', password='doc')

        rsp = self._api_put_draft(review_request, {'bugs_closed': '7'})

        self.assertEqual(rsp['stat'], 'ok')

        draft = ReviewRequestDraft.objects.get(
            review_request=review_request)
        sentinel = ConfiguredBugTracker.objects.get_sentinel()
        self.assertEqual(
            list(draft.bugs.values_list('bug_id', 'bug_tracker')),
            [('7', sentinel.pk)])


class PublishBugsCompatTests(TestCase):
    """Unit tests for publishing drafts with migrated bugs.

    Version Added:
        9.0
    """

    fixtures: ClassVar[list[str]] = ['test_users', 'test_scmtools']

    def _create_published_review_request(
        self,
    ) -> tuple[ReviewRequest, ConfiguredBugTracker]:
        """Return a published review request with a default tracker.

        Returns:
            tuple:
            The review request and its default bug tracker.
        """
        repository = self.create_repository()
        review_request = self.create_review_request(
            repository=repository,
            submitter='doc',
            target_people=[self.create_user(username='reviewer')],
            publish=True)

        tracker = ConfiguredBugTracker.objects.create(name='Tracker',
                                                      service_name='splat')
        repository.default_bug_tracker = tracker
        repository.save(update_fields=('default_bug_tracker',))

        return review_request, tracker

    def test_publish_migrated_draft(self) -> None:
        """Testing publishing a draft with migrated bugs"""
        review_request, tracker = self._create_published_review_request()

        other_tracker = ConfiguredBugTracker.objects.create(
            name='Other Tracker',
            service_name='splat')

        draft = ReviewRequestDraft.create(review_request)
        draft.summary = 'New summary'
        Bug.objects.sync_legacy_bug_list(review_request_details=draft,
                                         bug_ids=['1', '2'])
        draft.bugs.add(Bug.objects.get_or_create_bug(
            bug_tracker=other_tracker,
            bug_id='500'))
        draft.save()

        review_request.publish(review_request.submitter)

        review_request.refresh_from_db()
        self.assertTrue(review_request.extra_data.get(BUGS_MIGRATED_KEY))
        self.assertEqual(review_request.get_bug_list(), ['1', '2'])
        self.assertEqual(
            sorted(review_request.bugs.values_list('bug_id', flat=True)),
            ['1', '2', '500'])

        # The stored string was never written.
        self.assertEqual(review_request.bugs_closed, '')

        # A change entry was recorded per affected tracker, plus the
        # legacy entry.
        changedesc = review_request.changedescs.latest()
        self.assertIn(f'bugs:{tracker.pk}', changedesc.fields_changed)
        self.assertIn(f'bugs:{other_tracker.pk}', changedesc.fields_changed)
        self.assertIn('bugs_closed', changedesc.fields_changed)
        self.assertEqual(
            changedesc.fields_changed[f'bugs:{tracker.pk}']['label'],
            'Tracker')
        self.assertEqual(
            sorted(
                item[0]
                for item in (changedesc.fields_changed
                             [f'bugs:{tracker.pk}']['added'])
            ),
            ['1', '2'])
