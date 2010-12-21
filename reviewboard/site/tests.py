from django.contrib.auth.models import User
from django.template import Context, Template
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
