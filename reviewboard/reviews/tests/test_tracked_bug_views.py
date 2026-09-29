"""Tests for the tracker-qualified bug views.

Version Added:
    9.0
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from django.utils import timezone
from djblets.conditions import Condition, ConditionSet

from reviewboard.accounts.conditions import UserInGroupChoice
from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.hostingsvcs.splat import Splat
from reviewboard.reviews.models import Bug
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from collections.abc import Generator

    from reviewboard.hostingsvcs.base.bug_tracker import BugInfo


class TrackedBugViewsTests(TestCase):
    """Unit tests for the tracker-qualified bug views.

    Version Added:
        9.0
    """

    fixtures = ['test_users', 'test_scmtools']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.client.login(username='doc', password='doc')

        self.review_request = self.create_review_request(publish=True)
        self.tracker = ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='custom-bug-tracker',
            settings={
                'url_template': 'https://bugs.example.com/%s',
            })

    def _get_url(
        self,
        suffix: str = '',
    ) -> str:
        """Return the tracker-qualified bug URL.

        Args:
            suffix (str, optional):
                An optional suffix, such as ``infobox/``.

        Returns:
            str:
            The URL.
        """
        return (f'/r/{self.review_request.display_id}/'
                f'bug-trackers/{self.tracker.pk}/bugs/123/{suffix}')

    def test_redirect(self) -> None:
        """Testing the tracker-qualified bug redirect"""
        response = self.client.get(self._get_url())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'],
                         'https://bugs.example.com/123')

    def test_redirect_with_disabled_tracker(self) -> None:
        """Testing the tracker-qualified bug redirect with a disabled
        tracker
        """
        self.tracker.enabled = False
        self.tracker.save(update_fields=('enabled',))

        response = self.client.get(self._get_url())

        self.assertEqual(response.status_code, 404)

    def test_redirect_with_failing_user_conditions(self) -> None:
        """Testing the tracker-qualified bug redirect with a user failing
        the tracker's conditions
        """
        self._limit_tracker_access()

        response = self.client.get(self._get_url())

        self.assertEqual(response.status_code, 403)

    def test_infobox_with_failing_user_conditions(self) -> None:
        """Testing the tracker-qualified bug infobox with a user failing
        the tracker's conditions
        """
        self._limit_tracker_access()

        response = self.client.get(self._get_url('infobox/'))

        self.assertEqual(response.status_code, 403)

    def test_infobox_without_bug_info_support(self) -> None:
        """Testing the tracker-qualified bug infobox on a tracker without
        metadata support
        """
        response = self.client.get(self._get_url('infobox/'))

        self.assertEqual(response.status_code, 404)

    def test_infobox(self) -> None:
        """Testing the tracker-qualified bug infobox"""
        splat_tracker = ConfiguredBugTracker.objects.create(
            name='Splat Tracker',
            service_name='splat',
            settings={
                'splat_org_name': 'test-org',
            })

        def _fake_get_bug_info(
            self: Splat,
            *,
            config: (ConfiguredBugTracker | None) = None,
            bug_id: str,
            repository: object = None,
        ) -> BugInfo:
            return {
                'summary': f'Bug {bug_id} on config {config.pk}',
                'description': 'A bug.',
                'status': 'open',
            }

        Splat.get_bug_info_uncached = _fake_get_bug_info

        url = (f'/r/{self.review_request.display_id}/'
               f'bug-trackers/{splat_tracker.pk}/bugs/123/infobox/')

        try:
            response = self.client.get(url)
        finally:
            del Splat.get_bug_info_uncached

        self.assertEqual(response.status_code, 200)
        self.assertIn(f'Bug 123 on config {splat_tracker.pk}'.encode(),
                      response.content)

    def _limit_tracker_access(self) -> None:
        """Limit the test tracker to an empty review group."""
        group = self.create_review_group(name='limited-group')

        choice = UserInGroupChoice()
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(choice,
                      choice.get_operator('contains-any'),
                      [group]),
        ])

        self.tracker.user_conditions = condition_set.serialize()
        self.tracker.save(update_fields=('user_conditions',))


class TrackedBugInfoViewTests(TestCase):
    """Unit tests for TrackedBugInfoView.

    Version Added:
        9.0
    """

    fixtures = ['test_users', 'test_scmtools']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.review_request = self.create_review_request(publish=True)
        self.tracker = ConfiguredBugTracker.objects.create(
            name='Splat Tracker',
            service_name='splat',
            settings={
                'splat_org_name': 'test-org',
            })

    def test_get(self) -> None:
        """Testing TrackedBugInfoView"""
        bug = Bug.objects.create(bug_tracker=self.tracker, bug_id='123')
        self.review_request.bugs.add(bug)

        with self._fake_bug_info():
            response = self.client.get(self._get_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'bugs': {
                '123': {
                    'status': 'open',
                    'summary': 'Bug 123',
                },
            },
        })

        # The fetched metadata is cached on the bug.
        bug.refresh_from_db()
        self.assertEqual(bug.summary, 'Bug 123')

    def test_get_with_cached_metadata(self) -> None:
        """Testing TrackedBugInfoView serves cached metadata"""
        Bug.objects.create(bug_tracker=self.tracker,
                           bug_id='123',
                           summary='A crash',
                           status='open',
                           metadata_timestamp=timezone.now())

        response = self.client.get(self._get_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'bugs': {
                '123': {
                    'status': 'open',
                    'summary': 'A crash',
                },
            },
        })

    def test_get_without_bug_ids(self) -> None:
        """Testing TrackedBugInfoView without any bug IDs"""
        response = self.client.get(self._get_url(bug_ids=''))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'bugs': {}})

    def test_get_with_anonymous_user(self) -> None:
        """Testing TrackedBugInfoView with an anonymous user"""
        Bug.objects.create(bug_tracker=self.tracker,
                           bug_id='123',
                           summary='A crash',
                           status='open',
                           metadata_timestamp=timezone.now())

        response = self.client.get(self._get_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['bugs']['123']['summary'],
                         'A crash')

    def test_get_with_disabled_tracker(self) -> None:
        """Testing TrackedBugInfoView with a disabled tracker"""
        self.tracker.enabled = False
        self.tracker.save(update_fields=('enabled',))

        response = self.client.get(self._get_url())

        self.assertEqual(response.status_code, 404)

    def test_get_with_failing_user_conditions(self) -> None:
        """Testing TrackedBugInfoView with a user failing the tracker's
        conditions
        """
        group = self.create_review_group(name='limited-group')

        choice = UserInGroupChoice()
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(choice,
                      choice.get_operator('contains-any'),
                      [group]),
        ])

        self.tracker.user_conditions = condition_set.serialize()
        self.tracker.save(update_fields=('user_conditions',))

        response = self.client.get(self._get_url())

        self.assertEqual(response.status_code, 403)

    @contextmanager
    def _fake_bug_info(self) -> Generator[None, None, None]:
        """Serve fake bug metadata from the Splat service.

        Context:
            The service returns metadata for any requested bug.
        """
        def _fake_get_bug_info(
            self: Splat,
            *,
            config: (ConfiguredBugTracker | None) = None,
            bug_id: str,
            repository: object = None,
        ) -> BugInfo:
            return {
                'summary': f'Bug {bug_id}',
                'description': 'A bug.',
                'status': 'open',
            }

        Splat.get_bug_info_uncached = _fake_get_bug_info

        try:
            yield
        finally:
            del Splat.get_bug_info_uncached

    def _get_url(
        self,
        bug_ids: str = '123',
    ) -> str:
        """Return the bug metadata URL.

        Args:
            bug_ids (str, optional):
                The comma-separated bug IDs to query.

        Returns:
            str:
            The URL.
        """
        return (f'/r/{self.review_request.display_id}/'
                f'bug-trackers/{self.tracker.pk}/bug-info/'
                f'?bug-ids={bug_ids}')
