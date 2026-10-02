"""Unit tests for ConnectedServiceBugTrackersView.

Version Added:
    9.0
"""

from __future__ import annotations

from django.urls import reverse

from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.testing.testcase import TestCase


class ConnectedServiceBugTrackersViewTests(TestCase):
    """Unit tests for ConnectedServiceBugTrackersView.

    Version Added:
        9.0
    """

    fixtures = ['test_users']

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case class."""
        super().setUpClass()

        cls.url = cls._get_url('splat')

    @classmethod
    def _get_url(
        cls,
        service_id: str,
    ) -> str:
        """Return the URL for a service's bug tracker list.

        Args:
            service_id (str):
                The ID of the hosting service.

        Returns:
            str:
            The URL for the list.
        """
        return reverse('connected-services-bug-trackers',
                       kwargs={'service_id': service_id})

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.client.login(username='admin', password='admin')

    def test_get(self) -> None:
        """Testing ConnectedServiceBugTrackersView GET"""
        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Splat Tracker',
            service_name='splat',
            settings={'splat_org_name': 'my-org'})
        ConfiguredBugTracker.objects.create(
            name='My Disabled Tracker',
            service_name='splat',
            enabled=False,
            settings={'splat_org_name': 'other-org'})

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        content = response.content
        self.assertIn(b'My Splat Tracker', content)
        self.assertIn(b'My Disabled Tracker', content)
        self.assertIn(b'(disabled)', content)

        # Each configuration links to its database administration page.
        change_url = reverse('admin:hostingsvcs_configuredbugtracker_change',
                             args=(bug_tracker.pk,))
        self.assertIn(change_url.encode('utf-8'), content)

        self.assertEqual(response.headers['X-Total-Count'], '2')
        self.assertEqual(response.headers['X-Page-Number'], '1')
        self.assertEqual(response.headers['X-Num-Pages'], '1')

    def test_get_scopes_to_service(self) -> None:
        """Testing ConnectedServiceBugTrackersView GET only returns
        configurations for the requested service
        """
        ConfiguredBugTracker.objects.create(
            name='My Splat Tracker',
            service_name='splat',
            settings={'splat_org_name': 'my-org'})
        ConfiguredBugTracker.objects.create(
            name='My JIRA Tracker',
            service_name='jira',
            settings={})

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'My Splat Tracker', response.content)
        self.assertNotIn(b'My JIRA Tracker', response.content)

    def test_get_with_search(self) -> None:
        """Testing ConnectedServiceBugTrackersView GET with a search term"""
        ConfiguredBugTracker.objects.create(
            name='Team Alpha Bugs',
            service_name='splat',
            settings={'splat_org_name': 'alpha'})
        ConfiguredBugTracker.objects.create(
            name='Team Beta Bugs',
            service_name='splat',
            settings={'splat_org_name': 'beta'})

        response = self.client.get(self.url, {'q': 'beta'})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Team Beta Bugs', response.content)
        self.assertNotIn(b'Team Alpha Bugs', response.content)

    def test_get_with_no_match(self) -> None:
        """Testing ConnectedServiceBugTrackersView GET with a search term
        matching nothing
        """
        ConfiguredBugTracker.objects.create(
            name='My Splat Tracker',
            service_name='splat',
            settings={'splat_org_name': 'my-org'})

        response = self.client.get(self.url, {'q': 'xxx'})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No bug trackers match your filter.', response.content)

    def test_get_with_pagination(self) -> None:
        """Testing ConnectedServiceBugTrackersView GET paginates the
        configurations
        """
        ConfiguredBugTracker.objects.bulk_create(
            ConfiguredBugTracker(name=f'Tracker {i:02d}',
                                 service_name='splat',
                                 settings={'splat_org_name': f'org-{i}'})
            for i in range(26)
        )

        response = self.client.get(self.url, {'page': '2'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['X-Total-Count'], '26')
        self.assertEqual(response.headers['X-Page-Number'], '2')
        self.assertEqual(response.headers['X-Num-Pages'], '2')

        # The list is sorted by name, so page 2 has only the last tracker.
        self.assertIn(b'Tracker 25', response.content)
        self.assertNotIn(b'Tracker 00', response.content)

    def test_get_never_returns_sentinel(self) -> None:
        """Testing ConnectedServiceBugTrackersView GET never returns the
        sentinel bug tracker
        """
        sentinel = ConfiguredBugTracker.objects.get_sentinel()

        # The sentinel's pseudo-service is not a registered hosting
        # service, so requesting it is a 404 rather than a listing.
        response = self.client.get(self._get_url(sentinel.service_name))

        self.assertEqual(response.status_code, 404)

    def test_get_with_invalid_service(self) -> None:
        """Testing ConnectedServiceBugTrackersView GET with an invalid
        service
        """
        response = self.client.get(self._get_url('xxx'))

        self.assertEqual(response.status_code, 404)

    def test_get_with_in_repo_service(self) -> None:
        """Testing ConnectedServiceBugTrackersView GET with an in-repo bug
        tracker service
        """
        ConfiguredBugTracker.objects.create(
            name='GitHub Issues',
            service_name='github',
            settings={})

        response = self.client.get(self._get_url('github'))

        self.assertEqual(response.status_code, 404)

    def test_get_with_anonymous(self) -> None:
        """Testing ConnectedServiceBugTrackersView GET with an anonymous
        user
        """
        self.client.logout()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
