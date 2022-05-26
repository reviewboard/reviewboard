"""Unit tests for reviewboard.site.templatetags.local_site."""

from django.template import Context, Template

from reviewboard.testing.testcase import TestCase


class TemplateTagTests(TestCase):
    """Unit tests for reviewboard.site.templatetags.local_site."""

    def test_local_site_url_with_no_local_site(self):
        """Testing localsite's {% url %} with no local site"""
        context = Context({})

        t = Template('{% url "dashboard" %}')
        self.assertEqual(t.render(context), '/dashboard/')

        t = Template('{% url "user" "sample-user" %}')
        self.assertEqual(t.render(context), '/users/sample-user/')

    def test_local_site_url_with_local_site(self):
        """Testing localsite's {% url %} with local site"""
        context = Context({
            'local_site_name': 'test',
        })

        t = Template('{% url "dashboard" %}')
        self.assertEqual(t.render(context), '/s/test/dashboard/')

        t = Template('{% url "user" "sample-user" %}')
        self.assertEqual(t.render(context), '/s/test/users/sample-user/')
