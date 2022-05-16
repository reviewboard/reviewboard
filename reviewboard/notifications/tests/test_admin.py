"""Unit tests for reviewboard.notifications.models"""

from django.urls import reverse

from reviewboard.notifications.models import WebHookTarget
from reviewboard.testing.testcase import TestCase


class WebhookTargetAdminTests(TestCase):
    """Tests for reviewboard.notifications.admin."""

    fixtures = ['test_users', 'test_scmtools']

    def test_webhooktarget_form_redirect(self):
        """Testing that a WebHookTarget form can render on page, and saves
        data correctly
        """
        self.assertTrue(self.client.login(username='admin', password='admin'))
        test_repo = self.create_repository()

        response = self.client.get(
            reverse('admin:notifications_webhooktarget_add'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse('admin:notifications_webhooktarget_add'),
            {
                'apply_to': WebHookTarget.APPLY_TO_SELECTED_REPOS,
                'enabled': True,
                'encoding': WebHookTarget.ENCODING_JSON,
                'repositories': test_repo.pk,
                'url': 'http://www.google.ca',
            })
        self.assertRedirects(
            response,
            reverse('admin:notifications_webhooktarget_changelist'))
        webhooktarget = WebHookTarget.objects.latest('pk')

        response = self.client.get(
            reverse('admin:notifications_webhooktarget_change',
                    args=(webhooktarget.pk,)))
