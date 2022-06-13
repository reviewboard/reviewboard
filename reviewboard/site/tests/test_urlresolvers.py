"""Unit tests for reviewboard.site.urlresolvers."""

from django.http import HttpRequest

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing.testcase import TestCase


class LocalSiteReverseTests(TestCase):
    """Unit tests for local_site_reverse."""

    def test_with_no_local_site(self):
        """Testing local_site_reverse with no local site"""
        request = HttpRequest()

        self.assertEqual(local_site_reverse('dashboard'),
                         '/dashboard/')
        self.assertEqual(local_site_reverse('dashboard', request=request),
                         '/dashboard/')
        self.assertEqual(local_site_reverse('user', args=['sample-user']),
                         '/users/sample-user/')
        self.assertEqual(
            local_site_reverse('user', kwargs={'username': 'sample-user'}),
            '/users/sample-user/')

    def test_with_local_site(self):
        """Testing local_site_reverse with a local site"""
        request = HttpRequest()
        request.GET['local_site_name'] = 'test'

        self.assertEqual(local_site_reverse('dashboard', request=request),
                         '/dashboard/')
        self.assertEqual(local_site_reverse('user', args=['sample-user'],
                                            request=request),
                         '/users/sample-user/')
        self.assertEqual(
            local_site_reverse('user', kwargs={'username': 'sample-user'},
                               request=request),
            '/users/sample-user/')
