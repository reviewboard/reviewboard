from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.template import Context, Template
from django.test.client import RequestFactory

from reviewboard.accounts.models import Profile
from reviewboard.testing import TestCase


class MarkdownTemplateTagsTests(TestCase):
    """Unit tests for Markdown-related template tags."""

    def setUp(self):
        super(MarkdownTemplateTagsTests, self).setUp()

        self.user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=self.user, default_use_rich_text=False)

        request_factory = RequestFactory()
        request = request_factory.get('/')

        request.user = self.user
        self.context = Context({
            'request': request,
        })

    def test_normalize_text_for_edit_escape_html(self):
        """Testing {% normalize_text_for_edit %} escaping for HTML"""
        t = Template(
            "{% load reviewtags %}"
            "{% normalize_text_for_edit '&lt;foo **bar**' True %}")

        self.assertEqual(t.render(self.context), '&amp;lt;foo **bar**')

    def test_normalize_text_for_edit_escaping_js(self):
        """Testing {% normalize_text_for_edit %} escaping for JavaScript"""
        t = Template(
            "{% load reviewtags %}"
            "{% normalize_text_for_edit '&lt;foo **bar**' True True %}")

        self.assertEqual(t.render(self.context),
                         '\\u0026lt\\u003Bfoo **bar**')
