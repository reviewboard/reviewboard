"""Unit tests for reviewboard.reviews.admin."""

from __future__ import unicode_literals

from django.core import urlresolvers

from reviewboard.reviews.models import DefaultReviewer
from reviewboard.testing.testcase import TestCase


class DefaultReviewerFormTests(TestCase):
    """Tests for reviewboard.reviews.admin:DefaultReviewerAdmin."""

    fixtures = ['test_users']

    def test_defaultreviewer_form_redirect(self):
        """Testing that a DefaultReviewer form can render on page, and saves
        data correctly
        """
        self.assertTrue(self.client.login(username='admin', password='admin'))
        test_group = self.create_review_group()

        response = self.client.get(
            urlresolvers.reverse('admin:reviews_defaultreviewer_add'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            urlresolvers.reverse('admin:reviews_defaultreviewer_add'),
            {
                'file_regex': '/',
                'groups': test_group.pk,
                'name': 'Test Group',
            })
        self.assertRedirects(
            response,
            urlresolvers.reverse('admin:reviews_defaultreviewer_changelist'))
        default_reviewer = DefaultReviewer.objects.latest('pk')

        response = self.client.get(
            urlresolvers.reverse('admin:reviews_defaultreviewer_change',
                                 args=(default_reviewer.pk,)))
