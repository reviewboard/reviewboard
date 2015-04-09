from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.management import call_command
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.decorators import add_fixtures

from reviewboard.admin.server import build_server_url
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing.testcase import TestCase


class SearchTests(TestCase):
    """Unit tests for search functionality."""

    fixtures = ['test_users']

    @classmethod
    def setUpClass(cls):
        """Set some initial state for all search-related tests.

        This will enable search and reset Haystack's configuration based
        on that, allowing the search tests to run.
        """
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('search_enable', True)
        siteconfig.save()

        load_site_config()

    def test_search_all(self):
        """Testing search with review requests and users"""
        # We already have doc. Now let's create a review request.
        review_request = self.create_review_request(submitter='doc',
                                                    publish=True)
        self.reindex()

        # Perform the search.
        response = self.search('doc')
        context = response.context
        self.assertEqual(context['hits_returned'], 2)

        results = context['page'].object_list
        self.assertEqual(results[0].content_type(), 'auth.user')
        self.assertEqual(results[0].username, 'doc')
        self.assertEqual(results[1].content_type(), 'reviews.reviewrequest')
        self.assertEqual(results[1].summary, review_request.summary)

    def test_filter_review_requests(self):
        """Testing search with filtering for review requests"""
        # We already have doc. Now let's create a review request.
        review_request = self.create_review_request(submitter='doc',
                                                    publish=True)
        self.reindex()

        # Perform the search.
        response = self.search('doc', filter_by='reviewrequests')
        context = response.context
        self.assertEqual(context['hits_returned'], 1)

        results = context['page'].object_list
        self.assertEqual(results[0].content_type(), 'reviews.reviewrequest')
        self.assertEqual(results[0].summary, review_request.summary)

    def test_filter_users(self):
        """Testing search with filtering for review requests"""
        # We already have doc. Now let's create a review request.
        self.create_review_request(submitter='doc', publish=True)
        self.reindex()

        # Perform the search.
        response = self.search('doc', filter_by='users')
        context = response.context
        self.assertEqual(context['hits_returned'], 1)

        results = context['page'].object_list
        self.assertEqual(results[0].content_type(), 'auth.user')
        self.assertEqual(results[0].username, 'doc')

    @add_fixtures(['test_scmtools'])
    def test_review_requests_without_private_repo_access(self):
        """Testing search with private review requests without access to
        private repositories
        """
        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertFalse(review_request.is_accessible_by(user))
        self.reindex()

        # Perform the search.
        response = self.search(review_request.summary)
        context = response.context
        self.assertEqual(context['hits_returned'], 0)

    @add_fixtures(['test_scmtools'])
    def test_review_requests_with_private_repo_access(self):
        """Testing search with private review requests with access to
        private repositories
        """
        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)
        repository.users.add(user)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)

        self.assertTrue(review_request.is_accessible_by(user))
        self.reindex()

        # Perform the search.
        response = self.search(review_request.summary)
        context = response.context
        self.assertEqual(context['hits_returned'], 1)

        results = context['page'].object_list
        self.assertEqual(results[0].content_type(), 'reviews.reviewrequest')
        self.assertEqual(results[0].summary, review_request.summary)

    @add_fixtures(['test_scmtools'])
    def test_review_requests_with_private_repo_access_through_group(self):
        """Testing search with private review requests with access to
        private repositories through groups
        """
        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')

        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        repository = self.create_repository(public=False)
        repository.review_groups.add(group)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)

        self.assertTrue(review_request.is_accessible_by(user))
        self.reindex()

        # Perform the search.
        response = self.search(review_request.summary)
        context = response.context
        self.assertEqual(context['hits_returned'], 1)

        results = context['page'].object_list
        self.assertEqual(results[0].content_type(), 'reviews.reviewrequest')
        self.assertEqual(results[0].summary, review_request.summary)

    def test_review_requests_without_private_group_access(self):
        """Testing search with private review requests without access to
        a private group
        """
        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')

        group = self.create_review_group(invite_only=True)

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        self.assertFalse(review_request.is_accessible_by(user))
        self.reindex()

        # Perform the search.
        response = self.search(review_request.summary)
        context = response.context
        self.assertEqual(context['hits_returned'], 0)

    def test_review_requests_with_private_group_access(self):
        """Testing search with private review requests with access to
        a private group
        """
        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')

        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        self.assertTrue(review_request.is_accessible_by(user))
        self.reindex()

        # Perform the search.
        response = self.search(review_request.summary)
        context = response.context
        self.assertEqual(context['hits_returned'], 1)

        results = context['page'].object_list
        self.assertEqual(results[0].content_type(), 'reviews.reviewrequest')
        self.assertEqual(results[0].summary, review_request.summary)

    @add_fixtures(['test_scmtools'])
    def test_review_requests_with_private_repo_access_no_private_group(self):
        """Testing search with private review requests with access to
        a private repository and without access to a private_group
        """
        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')

        group = self.create_review_group(invite_only=True)

        repository = self.create_repository(public=False)
        repository.users.add(user)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        review_request.target_groups.add(group)

        self.assertFalse(review_request.is_accessible_by(user))
        self.reindex()

        # Perform the search.
        response = self.search(review_request.summary)
        context = response.context
        self.assertEqual(context['hits_returned'], 0)

    @add_fixtures(['test_scmtools'])
    def test_review_requests_with_private_repository_as_submitter(self):
        """Testing search with private review requests without access to
        a private repository as the submitter
        """
        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)
        repository.users.add(user)

        review_request = self.create_review_request(repository=repository,
                                                    submitter=user,
                                                    publish=True)

        self.assertTrue(review_request.is_accessible_by(user))
        self.reindex()

        # Perform the search.
        response = self.search(review_request.summary)
        context = response.context
        self.assertEqual(context['hits_returned'], 1)

        results = context['page'].object_list
        self.assertEqual(results[0].content_type(), 'reviews.reviewrequest')
        self.assertEqual(results[0].summary, review_request.summary)

    @add_fixtures(['test_scmtools'])
    def test_review_requests_with_private_repository_and_target_people(self):
        """Testing search with private review requests without access to
        a private repository and user in target_people
        """
        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        review_request.target_people.add(user)

        self.assertFalse(review_request.is_accessible_by(user))
        self.reindex()

        # Perform the search.
        response = self.search(review_request.summary)
        context = response.context
        self.assertEqual(context['hits_returned'], 0)

    def test_review_requests_with_private_group_and_target_people(self):
        """Testing search with private review requests without access to
        a private group and user in target_people
        """
        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)
        review_request.target_people.add(user)

        self.assertTrue(review_request.is_accessible_by(user))
        self.reindex()

        # Perform the search.
        response = self.search(review_request.summary)
        context = response.context
        self.assertEqual(context['hits_returned'], 1)

        results = context['page'].object_list
        self.assertEqual(results[0].content_type(), 'reviews.reviewrequest')
        self.assertEqual(results[0].summary, review_request.summary)

    def test_search_review_request_id(self):
        """Testing search with a review request ID"""
        site = Site.objects.get_current()
        site.domain = 'testserver'
        site.save()

        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')

        review_request = self.create_review_request(publish=True)

        self.assertTrue(review_request.is_accessible_by(user))
        self.reindex()

        # Perform the search.
        response = self.search('%d' % review_request.id)

        self.assertEqual(response.url,
                         build_server_url(review_request.get_absolute_url()))

    def test_search_numeric_non_id(self):
        """Testing search with a numeric query that is not a review request
        ID
        """
        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')

        review_request = self.create_review_request(bugs_closed='123,456',
                                                    publish=True)

        self.assertTrue(review_request.is_accessible_by(user))
        self.reindex()

        # Perform the search.
        response = self.search('456')
        context = response.context
        self.assertEqual(context['hits_returned'], 1)

        results = context['page'].object_list
        self.assertEqual(results[0].content_type(), 'reviews.reviewrequest')
        self.assertEqual(results[0].summary, review_request.summary)

    def reindex(self):
        """Re-index the search database for the unit tests."""
        call_command('rebuild_index', interactive=False)

    def search(self, q, filter_by=None):
        """Perform a search with the given query and optional filters.

        The resulting response object is returned. The search results can be
        inspected by looking at ``response.context``.
        """
        options = {
            'q': q,
        }

        if filter_by:
            options['filter'] = filter_by

        return self.client.get(local_site_reverse('search'), options)
