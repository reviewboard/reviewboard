"""Unit tests for reviewboard.site.mixins.LocalSiteAwareModelFormMixin."""

from django import forms
from django.contrib.auth.models import User

from reviewboard.reviews.models import DefaultReviewer, Group
from reviewboard.site.mixins import LocalSiteAwareModelFormMixin
from reviewboard.site.models import LocalSite
from reviewboard.testing.testcase import TestCase


class LocalSiteAwareModelFormMixinTests(TestCase):
    """Unit tests for LocalSiteAwareModelFormMixin."""

    class MyForm(LocalSiteAwareModelFormMixin, forms.ModelForm):
        users = forms.ModelMultipleChoiceField(
            queryset=User.objects.filter(is_active=True))

        inactive_user = forms.ModelChoiceField(
            queryset=User.objects.filter(is_active=False))

        default_reviewer = forms.ModelChoiceField(
            queryset=DefaultReviewer.objects.all())

        class Meta:
            model = Group
            fields = '__all__'

    def setUp(self):
        super(LocalSiteAwareModelFormMixinTests, self).setUp()

        self.global_user = User.objects.create(username='global-user')
        self.site_user = User.objects.create(username='site-user')
        self.inactive_global_user = User.objects.create(
            username='inactive-global-user',
            is_active=False)
        self.inactive_site_user = User.objects.create(
            username='inactive-site-user',
            is_active=False)

        self.local_site = LocalSite.objects.create(name='site1')
        self.local_site.users.add(self.site_user, self.inactive_site_user)

        self.global_default_reviewer = DefaultReviewer.objects.create(
            name='global-default-reviewer',
            file_regex='.')
        self.site_default_reviewer = DefaultReviewer.objects.create(
            name='site-default-reviewer',
            file_regex='.',
            local_site=self.local_site)

    def test_without_localsite(self):
        """Testing LocalSiteAwareModelFormMixin without a LocalSite"""
        # Make sure the initial state and querysets are what we expect on init.
        form = self.MyForm()

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [self.global_user, self.site_user])
        self.assertEqual(list(form.fields['inactive_user'].queryset),
                         [self.inactive_global_user, self.inactive_site_user])
        self.assertEqual(list(form.fields['default_reviewer'].queryset),
                         [self.global_default_reviewer,
                          self.site_default_reviewer])

        # Now test what happens when it's been fed data and validated.
        form = self.MyForm(data={
            'name': 'test-group',
            'display_name': 'Test Group',
            'users': [self.global_user.pk],
            'inactive_user': self.inactive_global_user.pk,
            'default_reviewer': self.global_default_reviewer.pk,
        })

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [self.global_user, self.site_user])
        self.assertEqual(list(form.fields['inactive_user'].queryset),
                         [self.inactive_global_user, self.inactive_site_user])
        self.assertEqual(list(form.fields['default_reviewer'].queryset),
                         [self.global_default_reviewer,
                          self.site_default_reviewer])

        form.is_valid()
        self.assertTrue(form.is_valid())

        # Make sure any overridden querysets have been restored, so users can
        # still change entries.
        self.assertEqual(list(form.fields['users'].queryset),
                         [self.global_user, self.site_user])
        self.assertEqual(list(form.fields['inactive_user'].queryset),
                         [self.inactive_global_user, self.inactive_site_user])
        self.assertEqual(list(form.fields['default_reviewer'].queryset),
                         [self.global_default_reviewer,
                          self.site_default_reviewer])

        new_group = form.save()
        self.assertEqual(list(new_group.users.all()), [self.global_user])
        self.assertIsNone(new_group.local_site_id)

    def test_without_localsite_and_edit_instance(self):
        """Testing LocalSiteAwareModelFormMixin without a LocalSite and
        editing an instance
        """
        group = self.create_review_group()

        form = self.MyForm(
            data={
                'name': 'new-group',
                'display_name': 'New Group',
                'users': [self.global_user.pk],
                'inactive_user': self.inactive_global_user.pk,
                'default_reviewer': self.global_default_reviewer.pk,
            },
            instance=group)
        self.assertTrue(form.is_valid())

        new_group = form.save()
        self.assertEqual(group.pk, new_group.pk)
        self.assertIsNone(new_group.local_site_id)

    def test_without_localsite_and_with_compatible_rel_values(self):
        """Testing LocalSiteAwareModelFormMixin without a LocalSite and
        compatible relation model values
        """
        # Note that Users are compatible even if on a Local Site, so long
        # as the form's model instance is not on a Local Site. However,
        # the DefaultReviewer is not compatible.
        form = self.MyForm(data={
            'name': 'new-group',
            'display_name': 'New Group',
            'users': [self.site_user.pk],
            'inactive_user': self.inactive_site_user.pk,
            'default_reviewer': self.global_default_reviewer.pk,
        })
        self.assertTrue(form.is_valid())

    def test_without_localsite_and_with_incompatible_rel_values(self):
        """Testing LocalSiteAwareModelFormMixin without a LocalSite and
        incompatible relation model values
        """
        form = self.MyForm(data={
            'name': 'new-group',
            'display_name': 'New Group',
            'users': [self.site_user.pk],
            'inactive_user': self.inactive_site_user.pk,
            'default_reviewer': self.site_default_reviewer.pk,
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'default_reviewer': [
                    'Select a valid choice. That choice is not one of the '
                    'available choices.',
                ],
            })

    def test_with_limited_localsite(self):
        """Testing LocalSiteAwareModelFormMixin limited to a LocalSite"""
        form = self.MyForm(limit_to_local_site=self.local_site)

        self.assertIs(form.limited_to_local_site, self.local_site)
        self.assertNotIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [self.site_user])
        self.assertEqual(list(form.fields['inactive_user'].queryset),
                         [self.inactive_site_user])
        self.assertEqual(list(form.fields['default_reviewer'].queryset),
                         [self.site_default_reviewer])

    def test_with_limited_localsite_and_changing_site(self):
        """Testing LocalSiteAwareModelFormMixin limited to a LocalSite and
        LocalSite in form data ignored
        """
        site2 = LocalSite.objects.create(name='test-site-2')

        form = self.MyForm(
            data={
                'name': 'new-group',
                'display_name': 'New Group',
                'users': [self.site_user.pk],
                'inactive_user': self.inactive_site_user.pk,
                'default_reviewer': self.site_default_reviewer.pk,
                'local_site': site2.pk,
            },
            limit_to_local_site=self.local_site)

        self.assertIs(form.limited_to_local_site, self.local_site)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['local_site'], self.local_site)

        group = form.save()
        self.assertEqual(group.local_site, self.local_site)

    def test_with_limited_localsite_and_compatible_instance(self):
        """Testing LocalSiteAwareModelFormMixin limited to a LocalSite and
        editing compatible instance
        """
        group = self.create_review_group(local_site=self.local_site)

        # This should just simply not raise an exception.
        self.MyForm(instance=group,
                    limit_to_local_site=self.local_site)

    def test_with_limited_localsite_and_incompatible_instance(self):
        """Testing LocalSiteAwareModelFormMixin limited to a LocalSite and
        editing incompatible instance
        """
        group = self.create_review_group()

        error_message = (
            'The provided instance is not associated with a LocalSite '
            'compatible with this form. Please contact support.'
        )

        # This should just simply not raise an exception.
        with self.assertRaisesMessage(ValueError, error_message):
            self.MyForm(instance=group,
                        limit_to_local_site=self.local_site)

    def test_with_limited_localsite_and_incompatible_rel_values(self):
        """Testing LocalSiteAwareModelFormMixin limited to a LocalSite and
        incompatible relation model values
        """
        form = self.MyForm(
            data={
                'name': 'new-group',
                'display_name': 'New Group',
                'users': [self.global_user.pk],
                'inactive_user': self.inactive_global_user.pk,
                'default_reviewer': self.global_default_reviewer.pk,
            },
            limit_to_local_site=self.local_site)

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'default_reviewer': [
                    'Select a valid choice. That choice is not one of the '
                    'available choices.',
                ],
                'inactive_user': [
                    'Select a valid choice. That choice is not one of the '
                    'available choices.',
                ],
                'users': [
                    'Select a valid choice. 1 is not one of the available '
                    'choices.',
                ],
            })

    def test_with_localsite_in_data(self):
        """Testing LocalSiteAwareModelFormMixin with a LocalSite in form data
        """
        # Make sure the initial state and querysets are what we expect on init.
        form = self.MyForm()

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [self.global_user, self.site_user])
        self.assertEqual(list(form.fields['inactive_user'].queryset),
                         [self.inactive_global_user, self.inactive_site_user])
        self.assertEqual(list(form.fields['default_reviewer'].queryset),
                         [self.global_default_reviewer,
                          self.site_default_reviewer])

        # Now test what happens when it's been fed data and validated.
        form = self.MyForm(data={
            'name': 'new-group',
            'display_name': 'New Group',
            'local_site': self.local_site.pk,
            'users': [self.site_user.pk],
            'inactive_user': self.inactive_site_user.pk,
            'default_reviewer': self.site_default_reviewer.pk,
        })

        self.assertIsNone(form.limited_to_local_site)
        self.assertTrue(form.is_valid())
        self.assertIn('local_site', form.fields)
        self.assertEqual(form.cleaned_data['local_site'], self.local_site)

        # Make sure any overridden querysets have been restored, so users can
        # still change entries.
        self.assertEqual(list(form.fields['users'].queryset),
                         [self.global_user, self.site_user])
        self.assertEqual(list(form.fields['inactive_user'].queryset),
                         [self.inactive_global_user, self.inactive_site_user])
        self.assertEqual(list(form.fields['default_reviewer'].queryset),
                         [self.global_default_reviewer,
                          self.site_default_reviewer])

        group = form.save()
        self.assertEqual(group.local_site, self.local_site)
        self.assertEqual(list(group.users.all()), [self.site_user])

    def test_with_localsite_in_data_and_edit_instance(self):
        """Testing LocalSiteAwareModelFormMixin with a LocalSite in form data
        and editing instance
        """
        group = self.create_review_group()

        form = self.MyForm(
            data={
                'name': 'new-group',
                'display_name': 'New Group',
                'local_site': self.local_site.pk,
                'users': [self.site_user.pk],
                'inactive_user': self.inactive_site_user.pk,
                'default_reviewer': self.site_default_reviewer.pk,
            },
            instance=group)
        self.assertTrue(form.is_valid())

        new_group = form.save()
        self.assertEqual(new_group.pk, group.pk)
        self.assertEqual(new_group.local_site, self.local_site)
        self.assertEqual(list(new_group.users.all()), [self.site_user])

    def test_with_localsite_in_data_and_incompatible_rel_values(self):
        """Testing LocalSiteAwareModelFormMixin with a LocalSite in form data
        and incompatible relation model values
        """
        form = self.MyForm(data={
            'name': 'new-group',
            'display_name': 'New Group',
            'local_site': self.local_site.pk,
            'users': [self.global_user.pk],
            'inactive_user': self.inactive_global_user.pk,
            'default_reviewer': self.global_default_reviewer.pk,
        })

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'default_reviewer': [
                    'Select a valid choice. That choice is not one of the '
                    'available choices.',
                ],
                'inactive_user': [
                    'Select a valid choice. That choice is not one of the '
                    'available choices.',
                ],
                'users': [
                    'Select a valid choice. 1 is not one of the available '
                    'choices.',
                ],
            })

    def test_with_localsite_in_data_with_bad_value(self):
        """Testing LocalSiteAwareModelFormMixin with a LocalSite in form data
        and ID is a non-integer
        """
        # This should just not crash.
        form = self.MyForm(data={
            'name': 'new-group',
            'display_name': 'New Group',
            'local_site': 'abc',
        })

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['local_site'],
            [
                'Select a valid choice. That choice is not one of the '
                'available choices.',
            ])
