"""Unit tests for reviewboard.accounts.templatetags.accounts."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.template import Context, Template
from django.test.client import RequestFactory
from django.utils.safestring import SafeText

from reviewboard.testing import TestCase


class UserProfileDisplayNameTests(TestCase):
    """Unit tests for {% user_profile_display_name %}."""

    def test_escapes_name(self):
        """Testing {% user_profile_display_name %} escapes content"""
        user = User.objects.create(
            username='test',
            first_name='"><script>alert("unsafe");</script>',
            last_name='<"',
            email='test@example.com')
        request_user = User.objects.create(username='admin',
                                           email='admin@example.com',
                                           is_superuser=True)
        rendered = self._render_tag(user, request_user)

        self.assertEqual(
            rendered,
            '&quot;&gt;&lt;script&gt;alert(&quot;unsafe&quot;);&lt;/script&gt;'
            ' &lt;&quot;')

    def _render_tag(self, user, request_user):
        """Utility function to render the tag.

        This will render the template for the tag, providing all necessary
        arguments. It will also check the rendered string is of the expected
        type before returning it.

        Args:
            user (django.contrib.auth.models.User):
                The user to pass to the tag.

            request_user (django.contrib.auth.models.User):
                The requesting user.

        Returns:
            django.utils.safestring.SafeText:
            The rendered content.
        """
        request = RequestFactory().get('/')
        request.user = request_user

        t = Template('{% load accounts %}'
                     '{% user_profile_display_name user %}')

        rendered = t.render(Context({
            'request': request,
            'user': user,
        }))

        self.assertIsInstance(rendered, SafeText)

        return rendered
