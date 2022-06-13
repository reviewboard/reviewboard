"""Unit tests for reviewboard.site.middleware.LocalSiteMiddleware."""

from django.http import HttpRequest, HttpResponse

from reviewboard.site.middleware import LocalSiteMiddleware
from reviewboard.site.models import LocalSite
from reviewboard.testing.testcase import TestCase


class LocalSiteMiddlewareTests(TestCase):
    """Unit tests for reviewboard.site.middleware.LocalSiteMiddleware."""

    def setUp(self):
        super().setUp()

        self.middleware = LocalSiteMiddleware(lambda: HttpResponse(''))

    def test_request_local_site_empty(self):
        """Testing LocalSiteMiddleware's request.local_site with no LocalSite
        """
        request = HttpRequest()
        self.middleware.process_view(request=request, view_func=None,
                                     view_args=None, view_kwargs={})

        self.assertTrue(hasattr(request, '_local_site_name'))
        self.assertTrue(hasattr(request, 'local_site'))
        self.assertIsNone(request._local_site_name)
        self.assertIsNone(request.local_site)

    def test_request_local_site_not_empty(self):
        """Testing LocalSiteMiddleware's request.local_site with a LocalSite"""
        local_site = LocalSite.objects.create(name='test-site')

        request = HttpRequest()
        self.middleware.process_view(
            request=request,
            view_func=None,
            view_args=None,
            view_kwargs={
                'local_site_name': local_site.name,
            })

        self.assertTrue(hasattr(request, '_local_site_name'))
        self.assertTrue(hasattr(request, 'local_site'))
        self.assertEqual(request._local_site_name, 'test-site')
        self.assertEqual(request.local_site, local_site)
