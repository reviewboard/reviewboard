"""Tests for the tracker-qualified bug views.

Version Added:
    9.0
"""

from __future__ import annotations

from djblets.conditions import Condition, ConditionSet

from reviewboard.accounts.conditions import UserInGroupChoice
from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.hostingsvcs.splat import Splat
from reviewboard.testing import TestCase


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
            service: Splat,
            *,
            config: (ConfiguredBugTracker | None) = None,
            bug_id: str,
            repository: object = None,
        ) -> dict:
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
