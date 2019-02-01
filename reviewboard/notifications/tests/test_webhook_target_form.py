"""Unit tests for reviewboard.notifications.forms.WebHookTargetForm."""

from __future__ import unicode_literals

from reviewboard.notifications.forms import WebHookTargetForm
from reviewboard.notifications.models import WebHookTarget
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class WebHookTargetFormTests(TestCase):
    """Unit tests for reviewboard.notifications.forms.WebHookTargetForm."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(WebHookTargetFormTests, self).setUp()

        self.local_site = LocalSite.objects.create(name='test')

        # Create repositories for the test.
        self.local_site_repo = self.create_repository(
            name='local-site-repo',
            local_site=self.local_site)

        self.global_site_repo = self.create_repository(
            name='global-site-repo')

    def test_without_localsite(self):
        """Testing WebHookTargetForm without a LocalSite"""
        # Make sure the initial state and querysets are what we expect on init.
        form = WebHookTargetForm()

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['repositories'].queryset),
                         [self.global_site_repo, self.local_site_repo])

        # Now test what happens when it's been fed data and validated.
        form = WebHookTargetForm(data={
            'apply_to': WebHookTarget.APPLY_TO_SELECTED_REPOS,
            'encoding': WebHookTarget.ENCODING_JSON,
            'events': ['*'],
            'url': 'https://example.com/',
            'repositories': [self.global_site_repo.pk],
        })

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['repositories'].queryset),
                         [self.global_site_repo, self.local_site_repo])

        self.assertTrue(form.is_valid())

        # Make sure any overridden querysets have been restored, so users can
        # still change entries.
        self.assertEqual(list(form.fields['repositories'].queryset),
                         [self.global_site_repo, self.local_site_repo])

        webhook = form.save()
        self.assertIsNone(webhook.local_site)
        self.assertEqual(list(webhook.repositories.all()),
                         [self.global_site_repo])

    def test_without_localsite_and_instance(self):
        """Testing WebHookTargetForm without a LocalSite and editing instance
        """
        webhook = WebHookTarget.objects.create()

        form = WebHookTargetForm(
            data={
                'apply_to': WebHookTarget.APPLY_TO_ALL,
                'encoding': WebHookTarget.ENCODING_JSON,
                'events': ['*'],
                'url': 'https://example.com/',
                'repositories': [self.global_site_repo.pk],
            },
            instance=webhook)
        self.assertTrue(form.is_valid())

        new_webhook = form.save()
        self.assertEqual(webhook.pk, new_webhook.pk)
        self.assertIsNone(new_webhook.local_site)

    def test_without_localsite_and_with_local_site_repo(self):
        """Testing WebHookTargetForm without a LocalSite and Repository on a
        LocalSite
        """
        form = WebHookTargetForm(data={
            'apply_to': WebHookTarget.APPLY_TO_ALL,
            'encoding': WebHookTarget.ENCODING_JSON,
            'events': ['*'],
            'url': 'https://example.com/',
            'repositories': [self.local_site_repo.pk],
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'repositories': ['Select a valid choice. 1 is not one of the '
                                 'available choices.'],
            })

    def test_with_limited_localsite(self):
        """Testing WebHookTargetForm limited to a LocalSite"""
        form = WebHookTargetForm(limit_to_local_site=self.local_site)

        self.assertEqual(form.limited_to_local_site, self.local_site)
        self.assertNotIn('local_site', form.fields)
        self.assertEqual(list(form.fields['repositories'].queryset),
                         [self.local_site_repo])

    def test_with_limited_localsite_and_changing_site(self):
        """Testing WebHookTargetForm limited to a LocalSite and changing
        LocalSite
        """
        site2 = LocalSite.objects.create(name='test-site-2')

        form = WebHookTargetForm(
            data={
                'apply_to': WebHookTarget.APPLY_TO_ALL,
                'encoding': WebHookTarget.ENCODING_JSON,
                'events': ['*'],
                'url': 'https://example.com/',
                'repositories': [self.local_site_repo.pk],
                'local_site': site2.pk,
            },
            limit_to_local_site=self.local_site)

        self.assertEqual(form.limited_to_local_site, self.local_site)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['local_site'], self.local_site)

        webhook = form.save()
        self.assertEqual(webhook.local_site, self.local_site)

    def test_with_limited_localsite_and_compatible_instance(self):
        """Testing WebHookTargetForm limited to a LocalSite and editing
        compatible instance
        """
        webhook = WebHookTarget(local_site=self.local_site)

        # This should just simply not raise an exception.
        WebHookTargetForm(instance=webhook,
                          limit_to_local_site=self.local_site)

    def test_with_limited_localsite_and_incompatible_instance(self):
        """Testing WebHookTargetForm limited to a LocalSite and editing
        incompatible instance
        """
        webhook = WebHookTarget.objects.create()

        error_message = (
            'The provided instance is not associated with a LocalSite '
            'compatible with this form. Please contact support.'
        )

        with self.assertRaisesMessage(ValueError, error_message):
            WebHookTargetForm(instance=webhook,
                              limit_to_local_site=self.local_site)

    def test_with_limited_localsite_and_invalid_repository(self):
        """Testing WebHookTargetForm limited to a LocalSite with a Repository
        not on the LocalSite
        """
        form = WebHookTargetForm(
            data={
                'apply_to': WebHookTarget.APPLY_TO_ALL,
                'encoding': WebHookTarget.ENCODING_JSON,
                'events': ['*'],
                'url': 'https://example.com/',
                'repositories': [self.global_site_repo.pk],
            },
            limit_to_local_site=self.local_site)

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'repositories': ['Select a valid choice. 2 is not one of the '
                                 'available choices.'],
            })

    def test_with_localsite_in_data(self):
        """Testing WebHookTargetForm with a LocalSite in form data"""
        # Make sure the initial state and querysets are what we expect on init.
        form = WebHookTargetForm()

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['repositories'].queryset),
                         [self.global_site_repo, self.local_site_repo])

        # Now test what happens when it's been fed data and validated.
        form = WebHookTargetForm(data={
            'apply_to': WebHookTarget.APPLY_TO_SELECTED_REPOS,
            'encoding': WebHookTarget.ENCODING_JSON,
            'events': ['*'],
            'url': 'https://example.com/',
            'local_site': self.local_site.pk,
            'repositories': [self.local_site_repo.pk],
        })

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['repositories'].queryset),
                         [self.global_site_repo, self.local_site_repo])

        self.assertTrue(form.is_valid())

        # Make sure any overridden querysets have been restored, so users can
        # still change entries.
        self.assertEqual(list(form.fields['repositories'].queryset),
                         [self.global_site_repo, self.local_site_repo])

        webhook = form.save()
        self.assertEqual(webhook.local_site, self.local_site)
        self.assertEqual(list(webhook.repositories.all()),
                         [self.local_site_repo])

    def test_with_localsite_in_data_and_instance(self):
        """Testing WebHookTargetForm with a LocalSite in form data and editing
        instance
        """
        webhook = WebHookTarget.objects.create()

        form = WebHookTargetForm(
            data={
                'apply_to': WebHookTarget.APPLY_TO_ALL,
                'encoding': WebHookTarget.ENCODING_JSON,
                'events': ['*'],
                'url': 'https://example.com/',
                'local_site': self.local_site.pk,
            },
            instance=webhook)
        self.assertTrue(form.is_valid())

        new_webhook = form.save()
        self.assertEqual(webhook.pk, new_webhook.pk)
        self.assertEqual(new_webhook.local_site, self.local_site)

    def test_with_localsite_in_data_and_invalid_repository(self):
        """Testing WebHookTargetForm with a LocalSite in form data and
        Repository not on the LocalSite
        """
        form = WebHookTargetForm(data={
            'apply_to': WebHookTarget.APPLY_TO_ALL,
            'encoding': WebHookTarget.ENCODING_JSON,
            'events': ['*'],
            'url': 'https://example.com/',
            'local_site': self.local_site.pk,
            'repositories': [self.global_site_repo.pk],
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'repositories': ['Select a valid choice. 2 is not one of the '
                                 'available choices.'],
            })
