"""Unit tests for reviewboard.reviews.views.NewReviewRequestView."""

from __future__ import unicode_literals

from django.contrib.auth.models import User

from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.decorators import add_fixtures

from reviewboard.testing import TestCase


class NewReviewRequestViewTests(TestCase):
    """Unit tests for reviewboard.reviews.views.NewReviewRequestView."""

    fixtures = ['test_users']

    # TODO: Split this up into multiple unit tests, and do a better job of
    #       checking for expected results.
    def test_get(self):
        """Testing NewReviewRequestView.get"""
        with self.siteconfig_settings({'auth_require_sitewide_login': False},
                                      reload_settings=False):
            response = self.client.get('/r/new')
            self.assertEqual(response.status_code, 301)

            response = self.client.get('/r/new/')
            self.assertEqual(response.status_code, 302)

            self.client.login(username='grumpy', password='grumpy')

            response = self.client.get('/r/new/')
            self.assertEqual(response.status_code, 200)

    def test_read_only_mode_for_users(self):
        """Testing NewReviewRequestView when in read-only mode for regular
        users
        """
        self.siteconfig = SiteConfiguration.objects.get_current()
        settings = {
            'site_read_only': True,
        }

        with self.siteconfig_settings(settings):
            # Ensure user is redirected when trying to create new review
			# request.
            self.client.logout()
            self.client.login(username='doc', password='doc')

            resp = self.client.get('/r/new/')

            self.assertEqual(resp.status_code, 302)

    def test_read_only_mode_for_superusers(self):
        """Testing NewReviewRequestView when in read-only mode for superusers
        """
        self.siteconfig = SiteConfiguration.objects.get_current()
        settings = {
            'site_read_only': True,
        }

        with self.siteconfig_settings(settings):
            # Ensure admin can still access new while in read-only mode.
            self.client.logout()
            self.client.login(username='admin', password='admin')

            resp = self.client.get('/r/new/')

            self.assertEqual(resp.status_code, 200)

    def test_get_context_data_with_no_repos(self):
        """Testing NewReviewRequestView.get_context_data with no repositories
        """
        self.client.login(username='grumpy', password='grumpy')
        response = self.client.get('/r/new/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_model_attrs'], {
            'repositories': [
                {
                    'filesOnly': True,
                    'localSitePrefix': '',
                    'name': '(None - File attachments only)',
                    'scmtoolName': '',
                    'supportsPostCommit': False,
                },
            ],
        })

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_get_context_data_with_repos(self):
        """Testing NewReviewRequestView.get_context_data with repositories"""
        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')

        # These will be shown in the repository list.
        repo1 = self.create_repository(
            name='Repository 1',
            tool_name='Git')
        repo2 = self.create_repository(
            name='Repository 2',
            tool_name='Subversion')
        repo3 = self.create_repository(
            name='Repository 3',
            tool_name='Perforce',
            public=False)

        repo3.users.add(user)

        # These won't be shown.
        self.create_repository(
            name='Repository 4',
            tool_name='Git',
            public=False)
        self.create_repository(
            name='Repository 5',
            tool_name='Git',
            with_local_site=True)

        response = self.client.get('/r/new/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_model_attrs'], {
            'repositories': [
                {
                    'filesOnly': True,
                    'localSitePrefix': '',
                    'name': '(None - File attachments only)',
                    'scmtoolName': '',
                    'supportsPostCommit': False,
                },
                {
                    'filesOnly': False,
                    'id': repo1.pk,
                    'localSitePrefix': '',
                    'name': 'Repository 1',
                    'requiresBasedir': False,
                    'requiresChangeNumber': False,
                    'scmtoolName': 'Git',
                    'supportsPostCommit': False,
                },
                {
                    'filesOnly': False,
                    'id': repo2.pk,
                    'localSitePrefix': '',
                    'name': 'Repository 2',
                    'requiresBasedir': True,
                    'requiresChangeNumber': False,
                    'scmtoolName': 'Subversion',
                    'supportsPostCommit': True,
                },
                {
                    'filesOnly': False,
                    'id': repo3.pk,
                    'localSitePrefix': '',
                    'name': 'Repository 3',
                    'requiresBasedir': False,
                    'requiresChangeNumber': True,
                    'scmtoolName': 'Perforce',
                    'supportsPostCommit': False,
                },
            ],
        })

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_get_context_data_with_repos_and_local_site(self):
        """Testing NewReviewRequestView.get_context_data with repositories
        and Local Site
        """
        user = User.objects.get(username='grumpy')
        self.get_local_site(self.local_site_name).users.add(user)

        self.client.login(username='grumpy', password='grumpy')

        # These will be shown in the repository list.
        repo1 = self.create_repository(
            name='Repository 1',
            tool_name='Git',
            with_local_site=True)
        repo2 = self.create_repository(
            name='Repository 2',
            tool_name='Subversion',
            with_local_site=True)
        repo3 = self.create_repository(
            name='Repository 3',
            tool_name='Perforce',
            public=False,
            with_local_site=True)

        repo3.users.add(user)

        # These won't be shown.
        self.create_repository(
            name='Repository 4',
            tool_name='Git',
            public=False,
            with_local_site=True)
        self.create_repository(
            name='Repository 5',
            tool_name='Git')

        local_site_prefix = 's/%s/' % self.local_site_name
        response = self.client.get('/%sr/new/' % local_site_prefix)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_model_attrs'], {
            'repositories': [
                {
                    'filesOnly': True,
                    'localSitePrefix': local_site_prefix,
                    'name': '(None - File attachments only)',
                    'scmtoolName': '',
                    'supportsPostCommit': False,
                },
                {
                    'filesOnly': False,
                    'id': repo1.pk,
                    'localSitePrefix': local_site_prefix,
                    'name': 'Repository 1',
                    'requiresBasedir': False,
                    'requiresChangeNumber': False,
                    'scmtoolName': 'Git',
                    'supportsPostCommit': False,
                },
                {
                    'filesOnly': False,
                    'id': repo2.pk,
                    'localSitePrefix': local_site_prefix,
                    'name': 'Repository 2',
                    'requiresBasedir': True,
                    'requiresChangeNumber': False,
                    'scmtoolName': 'Subversion',
                    'supportsPostCommit': True,
                },
                {
                    'filesOnly': False,
                    'id': repo3.pk,
                    'localSitePrefix': local_site_prefix,
                    'name': 'Repository 3',
                    'requiresBasedir': False,
                    'requiresChangeNumber': True,
                    'scmtoolName': 'Perforce',
                    'supportsPostCommit': False,
                },
            ],
        })
