from django.contrib.auth.models import User
from django.http import HttpRequest
from django.template import Context, Template
from django.test import TestCase

from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse


class BasicTests(TestCase):
    """Tests basic LocalSite functionality"""
    fixtures = ['test_users', 'test_site']

    def test_access(self):
        """Test LocalSite.is_accessible_by"""
        doc = User.objects.get(username="doc")
        dopey = User.objects.get(username="dopey")
        self.assertTrue(doc)
        self.assertTrue(dopey)

        site = LocalSite.objects.get(name="local-site-1")
        self.assertTrue(site)

        self.assertTrue(site.is_accessible_by(doc))
        self.assertTrue(not site.is_accessible_by(dopey))

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
            local_site_reverse('user', kwargs={'username': 'sample-user' }),
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
            local_site_reverse('user', kwargs={'username': 'sample-user' },
                               request=request),
            '/users/sample-user/')


class TemplateTagTests(TestCase):
    def test_local_site_url_with_no_local_site(self):
        """Testing localsite's {% url %} with no local site"""
        context = Context({})

        t = Template('{% url dashboard %}')
        self.assertEquals(t.render(context), '/dashboard/')

        t = Template('{% url user "sample-user" %}')
        self.assertEquals(t.render(context), '/users/sample-user/')

    def test_local_site_url_with_local_site(self):
        """Testing localsite's {% url %} with local site"""

        # Make sure that {% url %} is registered as a built-in tag.
        from reviewboard.site import templatetags

        context = Context({
            'local_site_name': 'test',
        })

        t = Template('{% url dashboard %}')
        self.assertEquals(t.render(context), '/s/test/dashboard/')

        t = Template('{% url user "sample-user" %}')
        self.assertEquals(t.render(context), '/s/test/users/sample-user/')
