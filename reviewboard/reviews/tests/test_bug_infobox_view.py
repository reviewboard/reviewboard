"""Unit tests for the bug infobox."""

from __future__ import annotations

import kgb

from django.http import HttpResponseNotFound

from reviewboard.hostingsvcs.github import GitHub
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class BugInfoboxViewTests(kgb.SpyAgency, TestCase):
    """Unit tests for the bug infobox."""

    fixtures = ['test_users', 'test_scmtools', 'test_site']

    def test_with_attachment_only_review_request(self) -> None:
        """Testing the BugInfoboxView with a review request that does not have
        a repository
        """
        review_request = self.create_review_request(publish=True)
        url = local_site_reverse('bug_infobox',
                                 args=(review_request.display_id, '1'))
        response = self.client.get(url)

        self.assertIsInstance(response, HttpResponseNotFound)

    def test_with_bug_url(self) -> None:
        """Testing the BugInfoboxView with link to bug tracker"""
        hosting_account = HostingServiceAccount.objects.create(
            service_name='github',
        )
        repository = self.create_repository(
            hosting_account=hosting_account,
            bug_tracker='http://bugs.example.com/%%s',
            extra_data={
                'bug_tracker_use_hosting': True,
                'github_private_repo_name': 'test',
                'repository_plan': 'private',
            })
        review_request = self.create_review_request(
            repository=repository,
            publish=True)

        self.spy_on(
            GitHub.get_bug_info,
            owner=GitHub,
            op=kgb.SpyOpReturn({
                'description': 'Bug description',
                'status': 'open',
                'summary': 'Bug summary',
            }))

        url = local_site_reverse(
            'bug_infobox',
            args=(review_request.display_id, '1'))

        self.client.login(username='doc', password='doc')

        response = self.client.get(url)
        self.assertIn('<a href="/r/1/bugs/1/">',
                      response.content.decode())

    def test_with_local_site(self) -> None:
        """Testing the BugInfoboxView with a review request on a local site"""
        local_site = self.get_local_site(name=self.local_site_name)
        hosting_account = HostingServiceAccount.objects.create(
            service_name='github',
            local_site=local_site)
        repository = self.create_repository(
            local_site=local_site,
            hosting_account=hosting_account,
            bug_tracker='http://bugs.example.com/%%s',
            extra_data={
                'bug_tracker_use_hosting': True,
                'github_private_repo_name': 'test',
                'repository_plan': 'private',
            })
        review_request = self.create_review_request(
            repository=repository,
            local_site=local_site,
            publish=True)

        self.spy_on(
            GitHub.get_bug_info,
            owner=GitHub,
            op=kgb.SpyOpReturn({
                'description': 'Bug description',
                'status': 'open',
                'summary': 'Bug summary',
            }))

        url = local_site_reverse(
            'bug_infobox',
            local_site_name=self.local_site_name,
            args=(review_request.display_id, '1'))

        self.client.login(username='doc', password='doc')

        response = self.client.get(url)
        self.assertIn('<a href="/s/local-site-1/r/1001/bugs/1/">',
                      response.content.decode())

    def test_with_local_site_permission_denied(self) -> None:
        """Testing the BugInfoboxView with a review request on a local site
        with a user who is not a member of that site
        """
        local_site = self.get_local_site(name=self.local_site_name)
        hosting_account = HostingServiceAccount.objects.create(
            service_name='github',
            local_site=local_site)
        repository = self.create_repository(
            local_site=local_site,
            hosting_account=hosting_account,
            bug_tracker='http://bugs.example.com/%%s',
            extra_data={
                'bug_tracker_use_hosting': True,
                'github_private_repo_name': 'test',
                'repository_plan': 'private',
            })
        review_request = self.create_review_request(
            repository=repository,
            local_site=local_site,
            publish=True)

        url = local_site_reverse(
            'bug_infobox',
            local_site_name=self.local_site_name,
            args=(review_request.display_id, '1'))

        self.client.login(username='dopey', password='dopey')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
