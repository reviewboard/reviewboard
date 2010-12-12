from django.contrib.auth.models import User
from django.test import TestCase

from reviewboard.site.models import LocalSite


class BasicTests(TestCase):
    """Tests basic LocalSite functionality"""
    fixtures = ['test_users', 'test_site']

    def testAccess(self):
        """Test LocalSite.is_accessible_by"""
        doc = User.objects.get(username="doc")
        dopey = User.objects.get(username="dopey")
        self.assertTrue(doc)
        self.assertTrue(dopey)

        site = LocalSite.objects.get(name="local-site-1")
        self.assertTrue(site)

        self.assertTrue(site.is_accessible_by(doc))
        self.assertTrue(not site.is_accessible_by(dopey))
