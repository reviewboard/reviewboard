from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from reviewboard.reviews.forms import (DefaultReviewerForm, GroupForm,
                                       UploadDiffForm)
from reviewboard.reviews.models import DefaultReviewer, Group
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class DefaultReviewerFormTests(TestCase):
    """Unit tests for DefaultReviewerForm."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(DefaultReviewerFormTests, self).setUp()

        self.local_site = LocalSite.objects.create(name='test')

        # Create repositories for the test.
        self.local_site_repo = self.create_repository(
            name='Test 1',
            local_site=self.local_site)
        self.global_site_repo = self.create_repository(name='Test 2')

        # Create users for the test.
        self.local_site_user = User.objects.create_user(username='testuser1')
        self.local_site.users.add(self.local_site_user)

        self.global_site_user = User.objects.create_user(username='testuser2')

        # Create groups for the test.
        self.local_site_group = self.create_review_group(
            name='test1',
            local_site=self.local_site)
        self.global_site_group = self.create_review_group(name='test2')

    def test_without_localsite(self):
        """Testing DefaultReviewerForm without a LocalSite"""
        # Make sure the initial state and querysets are what we expect on init.
        form = DefaultReviewerForm()

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['repository'].queryset),
                         [self.local_site_repo, self.global_site_repo])
        self.assertEqual(list(form.fields['people'].queryset),
                         [self.local_site_user, self.global_site_user])
        self.assertEqual(list(form.fields['groups'].queryset),
                         [self.local_site_group, self.global_site_group])

        # Now test what happens when it's been fed data and validated.
        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'repository': [self.global_site_repo.pk],
            'people': [self.global_site_user.pk],
            'groups': [self.global_site_group.pk],
        })

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['repository'].queryset),
                         [self.local_site_repo, self.global_site_repo])
        self.assertEqual(list(form.fields['people'].queryset),
                         [self.local_site_user, self.global_site_user])
        self.assertEqual(list(form.fields['groups'].queryset),
                         [self.local_site_group, self.global_site_group])
        self.assertIsNone(form.fields['people'].widget.local_site_name)

        self.assertTrue(form.is_valid())

        # Make sure any overridden querysets have been restored, so users can
        # still change entries.
        self.assertEqual(list(form.fields['repository'].queryset),
                         [self.local_site_repo, self.global_site_repo])
        self.assertEqual(list(form.fields['people'].queryset),
                         [self.local_site_user, self.global_site_user])
        self.assertEqual(list(form.fields['groups'].queryset),
                         [self.local_site_group, self.global_site_group])

        default_reviewer = form.save()

        self.assertIsNone(default_reviewer.local_site)
        self.assertEqual(list(default_reviewer.repository.all()),
                         [self.global_site_repo])
        self.assertEqual(list(default_reviewer.people.all()),
                         [self.global_site_user])
        self.assertEqual(list(default_reviewer.groups.all()),
                         [self.global_site_group])

    def test_without_localsite_and_instance(self):
        """Testing DefaultReviewerForm without a LocalSite and editing instance
        """
        default_reviewer = DefaultReviewer.objects.create(
            name='Test',
            file_regex='.*',
            local_site=self.local_site)

        form = DefaultReviewerForm(
            data={
                'name': 'Test',
                'file_regex': '.*',
            },
            instance=default_reviewer)
        self.assertTrue(form.is_valid())

        new_default_reviewer = form.save()
        self.assertEqual(default_reviewer.pk, new_default_reviewer.pk)
        self.assertIsNone(new_default_reviewer.local_site)

    def test_without_localsite_and_with_local_site_user(self):
        """Testing DefaultReviewerForm without a LocalSite and User on a
        LocalSite
        """
        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'people': [self.local_site_user.pk],
        })

        # Note that unlike others, this scenario is allowed.
        self.assertTrue(form.is_valid())

    def test_without_localsite_and_with_local_site_group(self):
        """Testing DefaultReviewerForm without a LocalSite and Group on a
        LocalSite
        """
        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'groups': [self.local_site_group.pk],
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'groups': ['Select a valid choice. 1 is not one of the '
                           'available choices.'],
            })

    def test_without_localsite_and_with_local_site_repo(self):
        """Testing DefaultReviewerForm without a LocalSite and Repository on a
        LocalSite
        """
        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'repository': [self.local_site_repo.pk],
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'repository': ['A repository with ID 1 was not found.'],
            })

    def test_with_limited_localsite(self):
        """Testing DefaultReviewerForm limited to a LocalSite"""
        form = DefaultReviewerForm(limit_to_local_site=self.local_site)

        self.assertEqual(form.limited_to_local_site, self.local_site)
        self.assertNotIn('local_site', form.fields)
        self.assertEqual(list(form.fields['repository'].queryset),
                         [self.local_site_repo])
        self.assertEqual(list(form.fields['people'].queryset),
                         [self.local_site_user])
        self.assertEqual(list(form.fields['groups'].queryset),
                         [self.local_site_group])
        self.assertEqual(form.fields['people'].widget.local_site_name,
                         self.local_site.name)

    def test_with_limited_localsite_and_changing_site(self):
        """Testing DefaultReviewerForm limited to a LocalSite and changing
        LocalSite
        """
        site2 = LocalSite.objects.create(name='test-site-2')

        form = DefaultReviewerForm(
            data={
                'name': 'Test',
                'file_regex': '.*',
                'local_site': site2,
            },
            limit_to_local_site=self.local_site)

        self.assertEqual(form.limited_to_local_site, self.local_site)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['local_site'], self.local_site)

        default_reviewer = form.save()
        self.assertEqual(default_reviewer.local_site, self.local_site)

    def test_with_limited_localsite_and_compatible_instance(self):
        """Testing DefaultReviewerForm limited to a LocalSite and editing
        compatible instance
        """
        default_reviewer = DefaultReviewer.objects.create(
            name='Test',
            file_regex='.*',
            local_site=self.local_site)

        # This should just simply not raise an exception.
        DefaultReviewerForm(instance=default_reviewer,
                            limit_to_local_site=self.local_site)

    def test_with_limited_localsite_and_incompatible_instance(self):
        """Testing DefaultReviewerForm limited to a LocalSite and editing
        incompatible instance
        """
        default_reviewer = DefaultReviewer.objects.create(
            name='Test',
            file_regex='.*')

        error_message = (
            'The provided instance is not associated with a LocalSite '
            'compatible with this form. Please contact support.'
        )

        with self.assertRaisesMessage(ValueError, error_message):
            DefaultReviewerForm(instance=default_reviewer,
                                limit_to_local_site=self.local_site)

    def test_with_limited_localsite_and_invalid_user(self):
        """Testing DefaultReviewerForm limited to a LocalSite with a User
        not on the LocalSite
        """
        form = DefaultReviewerForm(
            data={
                'name': 'Test',
                'file_regex': '.*',
                'people': [self.global_site_user.pk],
            },
            limit_to_local_site=self.local_site)

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'people': ['A user with ID 2 was not found.'],
            })

    def test_with_limited_localsite_and_invalid_group(self):
        """Testing DefaultReviewerForm limited to a LocalSite with a Group
        not on the LocalSite
        """
        form = DefaultReviewerForm(
            data={
                'name': 'Test',
                'file_regex': '.*',
                'groups': [self.global_site_group.pk],
            },
            limit_to_local_site=self.local_site)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'groups': ['Select a valid choice. 2 is not one of the '
                           'available choices.'],
            })

    def test_with_limited_localsite_and_invalid_repo(self):
        """Testing DefaultReviewerForm limited to a LocalSite with a
        Repository not on the LocalSite
        """
        form = DefaultReviewerForm(
            data={
                'name': 'Test',
                'file_regex': '.*',
                'repository': [self.global_site_repo.pk],
            },
            limit_to_local_site=self.local_site)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'repository': ['A repository with ID 2 was not found.'],
            })

    def test_with_localsite_in_data(self):
        """Testing DefaultReviewerForm with a LocalSite in form data"""
        # Make sure the initial state and querysets are what we expect on init.
        form = DefaultReviewerForm()

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['repository'].queryset),
                         [self.local_site_repo, self.global_site_repo])
        self.assertEqual(list(form.fields['people'].queryset),
                         [self.local_site_user, self.global_site_user])
        self.assertEqual(list(form.fields['groups'].queryset),
                         [self.local_site_group, self.global_site_group])
        self.assertIsNone(form.fields['people'].widget.local_site_name)

        # Now test what happens when it's been fed data and validated.
        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'local_site': self.local_site.pk,
            'repository': [self.local_site_repo.pk],
            'people': [self.local_site_user.pk],
            'groups': [self.local_site_group.pk],
        })

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['repository'].queryset),
                         [self.local_site_repo, self.global_site_repo])
        self.assertEqual(list(form.fields['people'].queryset),
                         [self.local_site_user, self.global_site_user])
        self.assertEqual(list(form.fields['groups'].queryset),
                         [self.local_site_group, self.global_site_group])
        self.assertIsNone(form.fields['people'].widget.local_site_name)

        self.assertTrue(form.is_valid())

        # Make sure any overridden querysets have been restored, so users can
        # still change entries.
        self.assertEqual(list(form.fields['repository'].queryset),
                         [self.local_site_repo, self.global_site_repo])
        self.assertEqual(list(form.fields['people'].queryset),
                         [self.local_site_user, self.global_site_user])
        self.assertEqual(list(form.fields['groups'].queryset),
                         [self.local_site_group, self.global_site_group])
        self.assertIsNone(form.fields['people'].widget.local_site_name)

        default_reviewer = form.save()

        self.assertEqual(default_reviewer.local_site, self.local_site)
        self.assertEqual(list(default_reviewer.repository.all()),
                         [self.local_site_repo])
        self.assertEqual(list(default_reviewer.people.all()),
                         [self.local_site_user])
        self.assertEqual(list(default_reviewer.groups.all()),
                         [self.local_site_group])

    def test_with_localsite_in_data_and_instance(self):
        """Testing DefaultReviewerform with a LocalSite in form data and
        editing instance
        """
        default_reviewer = DefaultReviewer.objects.create(
            name='Test',
            file_regex='.*')

        form = DefaultReviewerForm(
            data={
                'name': 'Test',
                'file_regex': '.*',
                'local_site': self.local_site.pk,
            },
            instance=default_reviewer)
        self.assertTrue(form.is_valid())

        new_default_reviewer = form.save()
        self.assertEqual(default_reviewer.pk, new_default_reviewer.pk)
        self.assertEqual(new_default_reviewer.local_site, self.local_site)

    def test_with_localsite_in_data_and_invalid_user(self):
        """Testing DefaultReviewerForm with a LocalSite in form data and User
        not on the LocalSite
        """
        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'local_site': self.local_site.pk,
            'people': [self.global_site_user.pk],
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'people': ['A user with ID 2 was not found.'],
            })

    def test_with_localsite_in_data_and_invalid_group(self):
        """Testing DefaultReviewerForm with a LocalSite in form data and Group
        not on the LocalSite
        """
        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'local_site': self.local_site.pk,
            'groups': [self.global_site_group.pk],
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'groups': ['Select a valid choice. 2 is not one of the '
                           'available choices.'],
            })

    def test_with_localsite_in_data_and_invalid_repo(self):
        """Testing DefaultReviewerForm with a LocalSite in form data and
        Repository not on the LocalSite
        """
        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'local_site': self.local_site.pk,
            'repository': [self.global_site_repo.pk],
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'repository': [
                    'A repository with ID 2 was not found.',
                ],
            })

    def test_form_with_positional_argument(self):
        """Testing DefaultReviewerForm when passing data as a positional
        argument
        """
        # This was a regression caused by the change to add the new related
        # user selector.
        form = DefaultReviewerForm({
            'name': 'test',
            'file_regex': '.*',
        })
        self.assertTrue(form.is_valid())


class GroupFormTests(TestCase):
    """Unit tests for GroupForm."""

    def setUp(self):
        super(GroupFormTests, self).setUp()

        self.local_site = LocalSite.objects.create(name='test')

        # Create users for the test.
        self.local_site_user = User.objects.create_user(username='testuser1')
        self.local_site.users.add(self.local_site_user)

        self.global_site_user = User.objects.create_user(username='testuser2')

    def test_without_localsite(self):
        """Testing GroupForm without a LocalSite"""
        # Make sure the initial state and querysets are what we expect on init.
        form = GroupForm()

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [self.local_site_user, self.global_site_user])
        self.assertIsNone(form.fields['users'].widget.local_site_name)

        # Now test what happens when it's been fed data and validated.
        form = GroupForm(data={
            'name': 'test',
            'display_name': 'Test',
            'users': [self.global_site_user.pk],
        })

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [self.local_site_user, self.global_site_user])
        self.assertIsNone(form.fields['users'].widget.local_site_name)

        self.assertTrue(form.is_valid())

        # Make sure any overridden querysets have been restored, so users can
        # still change entries.
        self.assertEqual(list(form.fields['users'].queryset),
                         [self.local_site_user, self.global_site_user])

        group = form.save()

        self.assertIsNone(group.local_site)
        self.assertEqual(list(group.users.all()), [self.global_site_user])

    def test_without_localsite_and_instance(self):
        """Testing GroupForm without a LocalSite and editing instance"""
        group = self.create_review_group(local_site=self.local_site)

        form = GroupForm(
            data={
                'name': 'test',
                'display_name': 'Test',
            },
            instance=group)
        self.assertTrue(form.is_valid())

        new_group = form.save()
        self.assertEqual(group.pk, new_group.pk)
        self.assertIsNone(new_group.local_site)

    def test_without_localsite_and_with_local_site_user(self):
        """Testing GroupForm without a LocalSite and User on a LocalSite"""
        form = GroupForm(data={
            'name': 'test',
            'display_name': 'Test',
            'users': [self.local_site_user.pk],
        })
        self.assertTrue(form.is_valid())

    def test_with_limited_localsite(self):
        """Testing GroupForm limited to a LocalSite"""
        form = GroupForm(limit_to_local_site=self.local_site)

        self.assertEqual(form.limited_to_local_site, self.local_site)
        self.assertNotIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [self.local_site_user])
        self.assertEqual(form.fields['users'].widget.local_site_name,
                         self.local_site.name)

    def test_with_limited_localsite_and_changing_site(self):
        """Testing GroupForm limited to a LocalSite and changing LocalSite"""
        site2 = LocalSite.objects.create(name='test-site-2')

        form = GroupForm(
            data={
                'name': 'test',
                'display_name': 'Test',
                'users': [self.local_site_user.pk],
                'local_site': site2.pk,
            },
            limit_to_local_site=self.local_site)

        self.assertEqual(form.limited_to_local_site, self.local_site)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['local_site'], self.local_site)

        group = form.save()
        self.assertEqual(group.local_site, self.local_site)

    def test_with_limited_localsite_and_compatible_instance(self):
        """Testing GroupForm limited to a LocalSite and editing compatible
        instance
        """
        group = self.create_review_group(local_site=self.local_site)

        # This should just simply not raise an exception.
        GroupForm(instance=group,
                  limit_to_local_site=self.local_site)

    def test_with_limited_localsite_and_incompatible_instance(self):
        """Testing GroupForm limited to a LocalSite and editing incompatible
        instance
        """
        group = self.create_review_group()

        error_message = (
            'The provided instance is not associated with a LocalSite '
            'compatible with this form. Please contact support.'
        )

        with self.assertRaisesMessage(ValueError, error_message):
            GroupForm(instance=group,
                      limit_to_local_site=self.local_site)

    def test_with_limited_localsite_and_invalid_user(self):
        """Testing GroupForm limited to a LocalSite with a User not on the
        LocalSite
        """
        form = GroupForm(
            data={
                'name': 'test',
                'display_name': 'Test',
                'users': [self.global_site_user.pk],
            },
            limit_to_local_site=self.local_site)

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'users': ['A user with ID 2 was not found.'],
            })

    def test_with_localsite_in_data(self):
        """Testing GroupForm with a LocalSite in form data"""
        # Make sure the initial state and querysets are what we expect on init.
        form = GroupForm()

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [self.local_site_user, self.global_site_user])
        self.assertIsNone(form.fields['users'].widget.local_site_name)

        # Now test what happens when it's been fed data and validated.
        form = GroupForm(data={
            'name': 'test',
            'display_name': 'Test',
            'local_site': self.local_site.pk,
            'users': [self.local_site_user.pk],
        })

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [self.local_site_user, self.global_site_user])
        self.assertIsNone(form.fields['users'].widget.local_site_name)

        self.assertTrue(form.is_valid())

        # Make sure any overridden querysets have been restored, so users can
        # still change entries.
        self.assertEqual(list(form.fields['users'].queryset),
                         [self.local_site_user, self.global_site_user])

        group = form.save()
        self.assertEqual(group.local_site, self.local_site)
        self.assertEqual(list(group.users.all()), [self.local_site_user])

    def test_with_localsite_in_data_and_instance(self):
        """Testing GroupForm with a LocalSite in form data and editing instance
        """
        group = self.create_review_group()

        form = GroupForm(
            data={
                'name': 'test',
                'display_name': 'Test',
                'local_site': self.local_site.pk,
            },
            instance=group)
        self.assertTrue(form.is_valid())

        new_group = form.save()
        self.assertEqual(group.pk, new_group.pk)
        self.assertEqual(new_group.local_site, self.local_site)

    def test_with_localsite_in_data_and_invalid_user(self):
        """Testing GroupForm with a LocalSite in form data and User not on the
        LocalSite
        """
        form = GroupForm(data={
            'name': 'test',
            'display_name': 'Test',
            'local_site': self.local_site.pk,
            'users': [self.global_site_user.pk],
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'users': ['A user with ID 2 was not found.'],
            })

    def test_form_with_positional_argument(self):
        """Testing GroupForm when passing data as a positional argument"""
        # This was a regression caused by the change to add the new related
        # user selector.
        form = GroupForm({
            'name': 'test',
            'display_name': 'Test',
        })

        self.assertTrue(form.is_valid())


class UploadDiffFormTests(TestCase):
    """Unit tests for UploadDiffForm."""

    fixtures = ['test_users', 'test_scmtools']

    def test_clean_with_no_history(self):
        """Testing UploadDiffForm.clean with a review request created without
        history support
        """
        review_request = self.create_review_request(create_repository=True)
        form = UploadDiffForm(
            review_request=review_request,
            data={
                'basedir': '',
            },
            files={
                'path': SimpleUploadedFile('diff',
                                           self.DEFAULT_GIT_FILEDIFF_DATA_DIFF),
            })

        self.assertTrue(form.is_valid())

    def test_clean_with_history(self):
        """Testing UploadDiffForm.clean with a review request created with
        history support
        """
        review_request = self.create_review_request(create_repository=True,
                                                    create_with_history=True)

        form = UploadDiffForm(
            review_request=review_request,
            data={
                'basedir': '',
            },
            files={
                'path': SimpleUploadedFile('diff',
                                           self.DEFAULT_GIT_FILEDIFF_DATA_DIFF),
            })

        self.assertFalse(form.is_valid())
        self.assertNotEqual(form.non_field_errors, [])
