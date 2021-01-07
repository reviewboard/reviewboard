"""Unit tests for reviewboard.search.views.RBSearchView."""

from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.utils.six.moves.urllib.parse import urlencode

from reviewboard.testing.testcase import TestCase


class SearchViewTests(TestCase):
    """Unit tests for reviewboard.search.views.RBSearchView."""

    def test_get_enabled_no_query(self):
        """Testing the search view without a query redirects to all review
        requests
        """
        with self.siteconfig_settings({'search_enable': True},
                                      reload_settings=False):
            rsp = self.client.get(reverse('search'))

        self.assertRedirects(rsp, '/r/')

    def test_get_enabled_query(self):
        """Testing the search view with a query"""
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
        """Testing the search view with search disabled"""
        with self.siteconfig_settings({'search_enable': False},
                                      reload_settings=False):
            rsp = self.client.get(reverse('search'))

        self.assertEqual(rsp.status_code, 200)
        self.assertIn(
            b'<title>Indexed search not enabled',
            rsp.content)
        self.assertNotIn(b'<form', rsp.content)
