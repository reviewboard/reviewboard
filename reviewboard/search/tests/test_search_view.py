"""Unit tests for reviewboard.search.views.RBSearchView."""

from urllib.parse import urlencode

from django.urls import reverse

from reviewboard.diffviewer.models import DiffSetHistory
from reviewboard.reviews.models import ReviewRequest
from reviewboard.search.testing import reindex_search, search_enabled
from reviewboard.testing.testcase import TestCase


class SearchViewTests(TestCase):
    """Unit tests for reviewboard.search.views.RBSearchView."""

    def test_get_enabled_no_query(self):
        """Testing SearchView without a query redirects to all review requests
        """
        with self.siteconfig_settings({'search_enable': True},
                                      reload_settings=False):
            rsp = self.client.get(reverse('search'))

        self.assertRedirects(rsp, '/r/')

    def test_get_enabled_query(self):
        """Testing SearchView with a query"""
        with self.siteconfig_settings({'search_enable': True},
                                      reload_settings=False):
            rsp = self.client.get(
                '%s?%s'
                % (reverse('search'),
                   urlencode({'q': 'foo'}))
            )

        self.assertEqual(rsp.status_code, 200)

        # Check for the search form.
        self.assertIn(b'<form method="get" action="/search/" role="search">',
                      rsp.content)

        # And the filtered search links.
        self.assertIn(
            b'<a href="?q=foo&model_filter=reviewrequests" rel="nofollow">',
            rsp.content)
        self.assertIn(
            b'<a href="?q=foo&model_filter=users" rel="nofollow">',
            rsp.content)

    def test_get_disabled(self):
        """Testing SearchView with search disabled"""
        with self.siteconfig_settings({'search_enable': False},
                                      reload_settings=False):
            rsp = self.client.get(reverse('search'))

        self.assertEqual(rsp.status_code, 200)
        self.assertIn(
            b'<title>Indexed search not enabled',
            rsp.content)
        self.assertNotIn(b'<form', rsp.content)

    def test_pagination(self):
        """Testing SearchView pagination"""
        user = self.create_user()
        diffset_history = DiffSetHistory.objects.create()

        ReviewRequest.objects.bulk_create(
            ReviewRequest(diffset_history=diffset_history,
                          summary='Test %s' % i,
                          submitter=user,
                          public=True)
            for i in range(20)
        )

        siteconfig_settings = {
            'search_results_per_page': 1,
        }

        with search_enabled(backend_id='whoosh'):
            with self.siteconfig_settings(siteconfig_settings,
                                          reload_settings=False):
                reindex_search()
                rsp = self.client.get('%s?q=Test&page=10' % reverse('search'))

        self.assertEqual(rsp.status_code, 200)

        self.assertIn(
            b'<a href="?q=Test&amp;page=1" rel="nofollow">'
            b'&laquo; First Page</a>',
            rsp.content)
        self.assertIn(
            b'<a href="?q=Test&amp;page=9" rel="nofollow">'
            b'&lt; Previous</a>',
            rsp.content)
        self.assertIn(
            b'<a href="?q=Test&amp;page=11" rel="nofollow">'
            b'Next &gt;</a>',
            rsp.content)
        self.assertIn(
            b'<a href="?q=Test&amp;page=20" rel="nofollow">'
            b'Last Page &raquo;</a>',
            rsp.content)
