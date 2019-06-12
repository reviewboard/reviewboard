"""Unit tests for reviewboard.accounts.views.edit_oauth_app."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from reviewboard.testing import TestCase


class EditOAuthAppViewTests(TestCase):
    """Unit tests for edit_oauth_app."""

    fixtures = ['test_users']

    def test_get(self):
        """Testing edit_oauth_app GET"""
        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        app = self.create_oauth_application(user=user)
        url = reverse('edit-oauth-app', kwargs={
            'app_id': app.pk,
        })

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/edit_oauth_app.html')
        self.assertEqual(response.context['app'], app)
