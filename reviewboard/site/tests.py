from __future__ import unicode_literals

from django.contrib.auth.models import Permission, User
from django.http import HttpRequest
from django.template import Context, Template
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.site.context_processors import AllPermsWrapper
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing.testcase import TestCase


class BasicTests(TestCase):
    """Tests basic LocalSite functionality"""
    fixtures = ['test_users', 'test_site']

    def test_access(self):
        """Test LocalSite.is_accessible_by"""
        doc = User.objects.get(username="doc")
        dopey = User.objects.get(username="dopey")
        site = LocalSite.objects.get(name="local-site-1")

        self.assertTrue(site.is_accessible_by(doc))
        self.assertFalse(site.is_accessible_by(dopey))

    def test_access_with_public(self):
        """Test LocalSite.is_accessible_by with public LocalSites"""
        doc = User.objects.get(username="doc")
        dopey = User.objects.get(username="dopey")
        site = LocalSite.objects.get(name="local-site-1")
        site.public = True

        self.assertTrue(site.is_accessible_by(doc))
        self.assertTrue(site.is_accessible_by(dopey))

    def test_local_site_reverse_with_no_local_site(self):
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

    def test_local_site_reverse_with_local_site(self):
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


class PermissionWrapperTests(TestCase):
    """Testing the LocalSite-aware permissions wrapper."""
    def setUp(self):
        super(PermissionWrapperTests, self).setUp()

        self.user = User.objects.get(username='doc')
        self.assertFalse(self.user.is_superuser)

    @add_fixtures(['test_users', 'test_site'])
    def test_lookup_global_permission(self):
        """Testing AllPermsWrapper with global permission lookup"""
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))

        perms = AllPermsWrapper(self.user, self.local_site_name)

        self.assertIn('reviews.delete_reviewrequest', perms)
        self.assertNotIn('reviews.fake_permission', perms)

    @add_fixtures(['test_users', 'test_site'])
    def test_lookup_site_permission(self):
        """Testing AllPermsWrapper with site permission lookup"""
        local_site  = LocalSite.objects.get(name=self.local_site_name)

        local_site_profile = LocalSiteProfile.objects.create(
            user=self.user,
            profile=self.user.get_profile(),
            local_site=local_site)
        local_site_profile.permissions['reviews.can_change_status'] = True
        local_site_profile.save()

        perms = AllPermsWrapper(self.user, self.local_site_name)

        self.assertIn('reviews.can_change_status', perms)
        self.assertNotIn('reviews.fake_permission', perms)


class TemplateTagTests(TestCase):
    def test_local_site_url_with_no_local_site(self):
        """Testing localsite's {% url %} with no local site"""
        context = Context({})

        t = Template('{% url "dashboard" %}')
        self.assertEquals(t.render(context), '/dashboard/')

        t = Template('{% url "user" "sample-user" %}')
        self.assertEquals(t.render(context), '/users/sample-user/')

    def test_local_site_url_with_local_site(self):
        """Testing localsite's {% url %} with local site"""

        # Make sure that {% url %} is registered as a built-in tag.
        from reviewboard.site import templatetags

        context = Context({
            'local_site_name': 'test',
        })

        t = Template('{% url "dashboard" %}')
        self.assertEquals(t.render(context), '/s/test/dashboard/')

        t = Template('{% url "user" "sample-user" %}')
        self.assertEquals(t.render(context), '/s/test/users/sample-user/')
