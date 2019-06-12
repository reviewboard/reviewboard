from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils import six

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import (register_hosting_service,
                                             unregister_hosting_service)
from reviewboard.scmtools.forms import RepositoryForm
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.testing.hosting_services import (SelfHostedTestService,
                                                  TestService)
from reviewboard.testing.testcase import TestCase


class RepositoryFormTests(TestCase):
    """Unit tests for the repository form."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(RepositoryFormTests, self).setUp()

        register_hosting_service('test', TestService)
        register_hosting_service('self_hosted_test', SelfHostedTestService)

        self.git_tool_id = Tool.objects.get(name='Git').pk

    def tearDown(self):
        super(RepositoryFormTests, self).tearDown()

        unregister_hosting_service('self_hosted_test')
        unregister_hosting_service('test')

    def test_without_localsite(self):
        """Testing RepositoryForm without a LocalSite"""
        local_site = LocalSite.objects.create(name='test')
        local_site_user = User.objects.create_user(username='testuser1')
        local_site.users.add(local_site_user)

        global_site_user = User.objects.create_user(username='testuser2')

        local_site_group = self.create_review_group(name='test1',
                                                    invite_only=True,
                                                    local_site=local_site)
        global_site_group = self.create_review_group(name='test2',
                                                     invite_only=True)

        local_site_account = HostingServiceAccount.objects.create(
            username='local-test-user',
            service_name='test',
            local_site=local_site)
        global_site_account = HostingServiceAccount.objects.create(
            username='global-test-user',
            service_name='test')

        # Make sure the initial state and querysets are what we expect on init.
        form = RepositoryForm()

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [local_site_user, global_site_user])
        self.assertEqual(list(form.fields['review_groups'].queryset),
                         [local_site_group, global_site_group])
        self.assertEqual(list(form.fields['hosting_account'].queryset),
                         [local_site_account, global_site_account])

        # Now test what happens when it's been fed data and validated.
        form = RepositoryForm(data={
            'name': 'test',
            'hosting_type': 'custom',
            'tool': self.git_tool_id,
            'path': '/path/to/test.git',
            'bug_tracker_type': 'none',
            'users': [global_site_user.pk],
            'review_groups': [global_site_group.pk],
        })

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [local_site_user, global_site_user])
        self.assertEqual(list(form.fields['review_groups'].queryset),
                         [local_site_group, global_site_group])
        self.assertIsNone(form.fields['users'].widget.local_site_name)
        self.assertEqual(list(form.fields['hosting_account'].queryset),
                         [local_site_account, global_site_account])

        self.assertTrue(form.is_valid())

        # Make sure any overridden querysets have been restored, so users can
        # still change entries.
        self.assertEqual(list(form.fields['users'].queryset),
                         [local_site_user, global_site_user])
        self.assertEqual(list(form.fields['review_groups'].queryset),
                         [local_site_group, global_site_group])
        self.assertEqual(list(form.fields['hosting_account'].queryset),
                         [local_site_account, global_site_account])

        repository = form.save()
        form.save_m2m()

        self.assertIsNone(repository.local_site)
        self.assertEqual(list(repository.users.all()), [global_site_user])
        self.assertEqual(list(repository.review_groups.all()),
                         [global_site_group])

    def test_without_localsite_and_instance(self):
        """Testing RepositoryForm without a LocalSite and editing instance"""
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository(local_site=local_site)

        form = RepositoryForm(
            data={
                'name': 'test',
                'hosting_type': 'custom',
                'tool': self.git_tool_id,
                'path': '/path/to/test.git',
                'bug_tracker_type': 'none',
            },
            instance=repository)
        self.assertTrue(form.is_valid())

        new_repository = form.save()
        self.assertEqual(repository.pk, new_repository.pk)
        self.assertIsNone(new_repository.local_site)

    def test_without_localsite_and_with_local_site_user(self):
        """Testing RepositoryForm without a LocalSite and User on a LocalSite
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.create_user(username='testuser1')
        local_site.users.add(user)

        form = RepositoryForm(data={
            'name': 'test',
            'hosting_type': 'custom',
            'tool': self.git_tool_id,
            'path': '/path/to/test.git',
            'bug_tracker_type': 'none',
            'users': [user.pk],
        })
        self.assertTrue(form.is_valid())

    def test_without_localsite_and_with_local_site_group(self):
        """Testing RepositoryForm without a LocalSite and Group on a LocalSite
        """
        local_site = LocalSite.objects.create(name='test')
        group = self.create_review_group(local_site=local_site)

        form = RepositoryForm(data={
            'name': 'test',
            'hosting_type': 'custom',
            'tool': self.git_tool_id,
            'path': '/path/to/test.git',
            'bug_tracker_type': 'none',
            'review_groups': [group.pk],
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'review_groups': [
                    'Select a valid choice. 1 is not one of the available '
                    'choices.',
                ],
            })

    def test_without_localsite_and_with_local_site_hosting_account(self):
        """Testing RepositoryForm without a LocalSite and
        HostingServiceAccount on a LocalSite
        """
        local_site = LocalSite.objects.create(name='test')

        hosting_account = HostingServiceAccount.objects.create(
            username='test-user',
            service_name='test',
            local_site=local_site)

        form = RepositoryForm(data={
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': hosting_account.pk,
            'test_repo_name': 'test',
            'tool': self.git_tool_id,
            'bug_tracker_type': 'none',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'hosting_account': [
                    'Select a valid choice. That choice is not one of the '
                    'available choices.',
                ],
            })

    def test_with_limited_localsite(self):
        """Testing RepositoryForm limited to a LocalSite"""
        local_site = LocalSite.objects.create(name='test')
        local_site_user = User.objects.create_user(username='testuser1')
        local_site.users.add(local_site_user)

        User.objects.create_user(username='testuser2')

        local_site_group = self.create_review_group(name='test1',
                                                    invite_only=True,
                                                    local_site=local_site)
        self.create_review_group(name='test2', invite_only=True)

        form = RepositoryForm(limit_to_local_site=local_site)

        self.assertEqual(form.limited_to_local_site, local_site)
        self.assertNotIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [local_site_user])
        self.assertEqual(list(form.fields['review_groups'].queryset),
                         [local_site_group])
        self.assertEqual(form.fields['users'].widget.local_site_name,
                         local_site.name)

    def test_with_limited_localsite_and_changing_site(self):
        """Testing RepositoryForm limited to a LocalSite and changing
        LocalSite
        """
        local_site1 = LocalSite.objects.create(name='test-site-1')
        local_site2 = LocalSite.objects.create(name='test-site-2')

        form = RepositoryForm(
            data={
                'name': 'test',
                'hosting_type': 'custom',
                'tool': self.git_tool_id,
                'path': '/path/to/test.git',
                'bug_tracker_type': 'none',
                'local_site': local_site2.pk,
            },
            limit_to_local_site=local_site1)

        self.assertEqual(form.limited_to_local_site, local_site1)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['local_site'], local_site1)

        repository = form.save()
        self.assertEqual(repository.local_site, local_site1)

    def test_with_limited_localsite_and_compatible_instance(self):
        """Testing RepositoryForm limited to a LocalSite and editing compatible
        instance
        """
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository(local_site=local_site)

        # This should just simply not raise an exception.
        RepositoryForm(instance=repository,
                       limit_to_local_site=local_site)

    def test_with_limited_localsite_and_incompatible_instance(self):
        """Testing RepositoryForm limited to a LocalSite and editing
        incompatible instance
        """
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository()

        error_message = (
            'The provided instance is not associated with a LocalSite '
            'compatible with this form. Please contact support.'
        )

        with self.assertRaisesMessage(ValueError, error_message):
            RepositoryForm(instance=repository,
                           limit_to_local_site=local_site)

    def test_with_limited_localsite_and_invalid_user(self):
        """Testing DefaultReviewerForm limited to a LocalSite with a User
        not on the LocalSite
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.create_user(username='test')

        form = RepositoryForm(
            data={
                'name': 'test',
                'hosting_type': 'custom',
                'tool': self.git_tool_id,
                'path': '/path/to/test.git',
                'bug_tracker_type': 'none',
                'users': [user.pk]
            },
            limit_to_local_site=local_site)

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'users': [
                    'Select a valid choice. 1 is not one of the available '
                    'choices.',
                ],
            })

    def test_with_limited_localsite_and_invalid_group(self):
        """Testing DefaultReviewerForm limited to a LocalSite with a Group
        not on the LocalSite
        """
        local_site = LocalSite.objects.create(name='test')
        group = self.create_review_group()

        form = RepositoryForm(
            data={
                'name': 'test',
                'hosting_type': 'custom',
                'tool': self.git_tool_id,
                'path': '/path/to/test.git',
                'bug_tracker_type': 'none',
                'review_groups': [group.pk]
            },
            limit_to_local_site=local_site)

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'review_groups': [
                    'Select a valid choice. 1 is not one of the available '
                    'choices.',
                ],
            })

    def test_with_limited_localsite_and_invalid_hosting_account(self):
        """Testing DefaultReviewerForm limited to a LocalSite with a
        HostingServiceAccount not on the LocalSite
        """
        local_site = LocalSite.objects.create(name='test')

        hosting_account = HostingServiceAccount.objects.create(
            username='test-user',
            service_name='test')

        form = RepositoryForm(
            data={
                'name': 'test',
                'hosting_type': 'test',
                'hosting_account': hosting_account.pk,
                'test_repo_name': 'test',
                'tool': self.git_tool_id,
                'bug_tracker_type': 'none',
            },
            limit_to_local_site=local_site)

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'hosting_account': [
                    'Select a valid choice. That choice is not one of the '
                    'available choices.',
                ],
            })

    def test_with_localsite_in_data(self):
        """Testing RepositoryForm with a LocalSite in form data"""
        local_site = LocalSite.objects.create(name='test')
        local_site_user = User.objects.create_user(username='testuser1')
        local_site.users.add(local_site_user)

        global_site_user = User.objects.create_user(username='testuser2')

        local_site_group = self.create_review_group(name='test1',
                                                    invite_only=True,
                                                    local_site=local_site)
        global_site_group = self.create_review_group(name='test2',
                                                     invite_only=True)

        local_site_account = HostingServiceAccount.objects.create(
            username='local-test-user',
            service_name='test',
            local_site=local_site)
        local_site_account.data['password'] = 'testpass'
        local_site_account.save(update_fields=('data',))

        global_site_account = HostingServiceAccount.objects.create(
            username='global-test-user',
            service_name='test')

        # Make sure the initial state and querysets are what we expect on init.
        form = RepositoryForm()

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [local_site_user, global_site_user])
        self.assertEqual(list(form.fields['review_groups'].queryset),
                         [local_site_group, global_site_group])
        self.assertIsNone(form.fields['users'].widget.local_site_name)
        self.assertEqual(list(form.fields['hosting_account'].queryset),
                         [local_site_account, global_site_account])

        # Now test what happens when it's been fed data and validated.
        form = RepositoryForm(data={
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': local_site_account.pk,
            'test_repo_name': 'test',
            'tool': self.git_tool_id,
            'path': '/path/to/test.git',
            'bug_tracker_type': 'none',
            'local_site': local_site.pk,
            'users': [local_site_user.pk],
            'review_groups': [local_site_group.pk],
        })

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['users'].queryset),
                         [local_site_user, global_site_user])
        self.assertEqual(list(form.fields['review_groups'].queryset),
                         [local_site_group, global_site_group])
        self.assertIsNone(form.fields['users'].widget.local_site_name)
        self.assertEqual(list(form.fields['hosting_account'].queryset),
                         [local_site_account, global_site_account])

        self.assertTrue(form.is_valid())

        # Make sure any overridden querysets have been restored, so users can
        # still change entries.
        self.assertEqual(list(form.fields['users'].queryset),
                         [local_site_user, global_site_user])
        self.assertEqual(list(form.fields['review_groups'].queryset),
                         [local_site_group, global_site_group])
        self.assertEqual(list(form.fields['hosting_account'].queryset),
                         [local_site_account, global_site_account])

        repository = form.save()
        form.save_m2m()

        self.assertEqual(repository.local_site, local_site)
        self.assertEqual(repository.hosting_account, local_site_account)
        self.assertEqual(list(repository.users.all()), [local_site_user])
        self.assertEqual(list(repository.review_groups.all()),
                         [local_site_group])

    def test_with_localsite_in_data_and_instance(self):
        """Testing RepositoryForm with a LocalSite in form data and editing
        instance
        """
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository()

        form = RepositoryForm(
            data={
                'name': 'test',
                'hosting_type': 'custom',
                'tool': self.git_tool_id,
                'path': '/path/to/test.git',
                'bug_tracker_type': 'none',
                'local_site': local_site.pk,
            },
            instance=repository)
        self.assertTrue(form.is_valid())

        new_repository = form.save()
        self.assertEqual(repository.pk, new_repository.pk)
        self.assertEqual(new_repository.local_site, local_site)

    def test_with_localsite_in_data_and_invalid_user(self):
        """Testing RepositoryForm with a LocalSite in form data and User not
        on the LocalSite
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.create_user(username='test-user')

        form = RepositoryForm(data={
            'name': 'test',
            'hosting_type': 'custom',
            'tool': self.git_tool_id,
            'path': '/path/to/test.git',
            'bug_tracker_type': 'none',
            'local_site': local_site.pk,
            'users': [user.pk],
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'users': [
                    'Select a valid choice. 1 is not one of the available '
                    'choices.',
                ],
            })

    def test_with_localsite_in_data_and_invalid_group(self):
        """Testing RepositoryForm with a LocalSite in form data and Group not
        on the LocalSite
        """
        local_site = LocalSite.objects.create(name='test')
        group = self.create_review_group()

        form = RepositoryForm(data={
            'name': 'test',
            'hosting_type': 'custom',
            'tool': self.git_tool_id,
            'path': '/path/to/test.git',
            'bug_tracker_type': 'none',
            'local_site': local_site.pk,
            'review_groups': [group.pk],
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'review_groups': [
                    'Select a valid choice. 1 is not one of the available '
                    'choices.',
                ],
            })

    def test_plain_repository(self):
        """Testing RepositoryForm with a plain repository"""
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'custom',
            'tool': self.git_tool_id,
            'path': '/path/to/test.git',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account, None)
        self.assertEqual(repository.extra_data, {})

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_plain_repository_with_missing_fields(self):
        """Testing RepositoryForm with a plain repository with missing fields
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'custom',
            'tool': self.git_tool_id,
            'bug_tracker_type': 'none',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('path', form.errors)

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_new_account(self):
        """Testing RepositoryForm with a hosting service and new account"""
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'test-hosting_account_username': 'testuser',
            'test-hosting_account_password': 'testpass',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())
        self.assertTrue(form.hosting_account_linked)

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account.username, 'testuser')
        self.assertEqual(repository.hosting_account.service_name, 'test')
        self.assertEqual(repository.hosting_account.local_site, None)
        self.assertEqual(repository.extra_data['repository_plan'], '')
        self.assertEqual(repository.path, 'http://example.com/testrepo/')
        self.assertEqual(repository.mirror_path, '')

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_new_account_auth_error(self):
        """Testing RepositoryForm with a hosting service and new account and
        authorization error
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'test-hosting_account_username': 'baduser',
            'test-hosting_account_password': 'testpass',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)
        self.assertIn('hosting_account', form.errors)
        self.assertEqual(form.errors['hosting_account'],
                         ['Unable to link the account: The username is '
                          'very very bad.'])

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_new_account_2fa_code_required(self):
        """Testing RepositoryForm with a hosting service and new account and
        two-factor auth code required
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'test-hosting_account_username': '2fa-user',
            'test-hosting_account_password': 'testpass',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)
        self.assertIn('hosting_account', form.errors)
        self.assertEqual(form.errors['hosting_account'],
                         ['Enter your 2FA code.'])
        self.assertTrue(
            form.hosting_service_info['test']['needs_two_factor_auth_code'])

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_new_account_2fa_code_provided(self):
        """Testing RepositoryForm with a hosting service and new account and
        two-factor auth code provided
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'test-hosting_account_username': '2fa-user',
            'test-hosting_account_password': 'testpass',
            'test-hosting_account_two_factor_auth_code': '123456',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())
        self.assertTrue(form.hosting_account_linked)
        self.assertFalse(
            form.hosting_service_info['test']['needs_two_factor_auth_code'])

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_new_account_missing_fields(self):
        """Testing RepositoryForm with a hosting service and new account and
        missing fields
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)

        self.assertIn('hosting_account_username', form.errors)
        self.assertIn('hosting_account_password', form.errors)

        # Make sure the auth form also contains the errors.
        auth_form = form.hosting_auth_forms.pop('test')
        self.assertIn('hosting_account_username', auth_form.errors)
        self.assertIn('hosting_account_password', auth_form.errors)

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_self_hosted_and_new_account(self):
        """Testing RepositoryForm with a self-hosted hosting service and new
        account
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'self_hosted_test-hosting_url': 'https://myserver.com',
            'self_hosted_test-hosting_account_username': 'testuser',
            'self_hosted_test-hosting_account_password': 'testpass',
            'test_repo_name': 'myrepo',
            'tool': self.git_tool_id,
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertTrue(form.is_valid())
        self.assertTrue(form.hosting_account_linked)

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account.hosting_url,
                         'https://myserver.com')
        self.assertEqual(repository.hosting_account.username, 'testuser')
        self.assertEqual(repository.hosting_account.service_name,
                         'self_hosted_test')
        self.assertEqual(repository.hosting_account.local_site, None)
        self.assertEqual(repository.extra_data['test_repo_name'], 'myrepo')
        self.assertEqual(repository.extra_data['hosting_url'],
                         'https://myserver.com')
        self.assertEqual(repository.path, 'https://myserver.com/myrepo/')
        self.assertEqual(repository.mirror_path, 'git@myserver.com:myrepo/')

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_self_hosted_and_blank_url(self):
        """Testing RepositoryForm with a self-hosted hosting service and blank
        URL
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'self_hosted_test-hosting_url': '',
            'self_hosted_test-hosting_account_username': 'testuser',
            'self_hosted_test-hosting_account_password': 'testpass',
            'test_repo_name': 'myrepo',
            'tool': self.git_tool_id,
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)

    def test_with_hosting_service_new_account_localsite(self):
        """Testing RepositoryForm with a hosting service, new account and
        LocalSite
        """
        local_site = LocalSite.objects.create(name='testsite')

        form = RepositoryForm(
            {
                'name': 'test',
                'hosting_type': 'test',
                'test-hosting_account_username': 'testuser',
                'test-hosting_account_password': 'testpass',
                'tool': self.git_tool_id,
                'test_repo_name': 'testrepo',
                'bug_tracker_type': 'none',
                'local_site': local_site.pk,
            },
            limit_to_local_site=local_site)

        self.assertTrue(form.is_valid())
        self.assertTrue(form.hosting_account_linked)

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.local_site, local_site)
        self.assertEqual(repository.hosting_account.username, 'testuser')
        self.assertEqual(repository.hosting_account.service_name, 'test')
        self.assertEqual(repository.hosting_account.local_site, local_site)
        self.assertEqual(repository.extra_data['repository_plan'], '')

    def test_with_hosting_service_existing_account(self):
        """Testing RepositoryForm with a hosting service and existing
        account
        """
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')
        account.data['password'] = 'testpass'
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())
        self.assertFalse(form.hosting_account_linked)

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account, account)
        self.assertEqual(repository.extra_data['repository_plan'], '')

    def test_with_hosting_service_existing_account_needs_reauth(self):
        """Testing RepositoryForm with a hosting service and existing
        account needing re-authorization
        """
        # We won't be setting the password, so that is_authorized() will
        # fail.
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)
        self.assertEqual(set(form.errors.keys()),
                         set(['hosting_account_username',
                              'hosting_account_password']))

    def test_with_hosting_service_existing_account_reauthing(self):
        """Testing RepositoryForm with a hosting service and existing
        account with re-authorizating
        """
        # We won't be setting the password, so that is_authorized() will
        # fail.
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'test-hosting_account_username': 'testuser2',
            'test-hosting_account_password': 'testpass2',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())
        self.assertTrue(form.hosting_account_linked)

        account = HostingServiceAccount.objects.get(pk=account.pk)
        self.assertEqual(account.username, 'testuser2')
        self.assertEqual(account.data['password'], 'testpass2')

    def test_with_hosting_service_self_hosted_and_existing_account(self):
        """Testing RepositoryForm with a self-hosted hosting service and
        existing account
        """
        account = HostingServiceAccount.objects.create(
            username='testuser',
            service_name='self_hosted_test',
            hosting_url='https://example.com')
        account.data['password'] = 'testpass'
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'self_hosted_test-hosting_url': 'https://example.com',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'myrepo',
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertTrue(form.is_valid())
        self.assertFalse(form.hosting_account_linked)

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account, account)
        self.assertEqual(repository.extra_data['hosting_url'],
                         'https://example.com')

    def test_with_self_hosted_and_invalid_account_service(self):
        """Testing RepositoryForm with a self-hosted hosting service and
        invalid existing account due to mismatched service type
        """
        account = HostingServiceAccount.objects.create(
            username='testuser',
            service_name='self_hosted_test',
            hosting_url='https://example1.com')
        account.data['password'] = 'testpass'
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'myrepo',
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)

    def test_with_self_hosted_and_invalid_account_local_site(self):
        """Testing RepositoryForm with a self-hosted hosting service and
        invalid existing account due to mismatched Local Site
        """
        account = HostingServiceAccount.objects.create(
            username='testuser',
            service_name='self_hosted_test',
            hosting_url='https://example1.com',
            local_site=LocalSite.objects.create(name='test-site'))
        account.data['password'] = 'testpass'
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'myrepo',
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)

    def test_with_hosting_service_custom_bug_tracker(self):
        """Testing RepositoryForm with a custom bug tracker"""
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')
        account.data['password'] = 'testpass'
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'custom',
            'bug_tracker': 'http://example.com/issue/%s',
        })

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertFalse(repository.extra_data['bug_tracker_use_hosting'])
        self.assertEqual(repository.bug_tracker, 'http://example.com/issue/%s')
        self.assertNotIn('bug_tracker_type', repository.extra_data)

    def test_with_hosting_service_bug_tracker_service(self):
        """Testing RepositoryForm with a bug tracker service"""
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')
        account.data['password'] = 'testpass'
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'test',
            'bug_tracker_hosting_account_username': 'testuser',
            'bug_tracker-test_repo_name': 'testrepo',
        })

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertFalse(repository.extra_data['bug_tracker_use_hosting'])
        self.assertEqual(repository.bug_tracker,
                         'http://example.com/testuser/testrepo/issue/%s')
        self.assertEqual(repository.extra_data['bug_tracker_type'],
                         'test')
        self.assertEqual(
            repository.extra_data['bug_tracker-test_repo_name'],
            'testrepo')
        self.assertEqual(
            repository.extra_data['bug_tracker-hosting_account_username'],
            'testuser')

    def test_with_hosting_service_self_hosted_bug_tracker_service(self):
        """Testing RepositoryForm with a self-hosted bug tracker service"""
        account = HostingServiceAccount.objects.create(
            username='testuser',
            service_name='self_hosted_test',
            hosting_url='https://example.com')
        account.data['password'] = 'testpass'
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'hosting_url': 'https://example.com',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'self_hosted_test',
            'bug_tracker_hosting_url': 'https://example.com',
            'bug_tracker-test_repo_name': 'testrepo',
        })
        form.validate_repository = False

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertFalse(repository.extra_data['bug_tracker_use_hosting'])
        self.assertEqual(repository.bug_tracker,
                         'https://example.com/testrepo/issue/%s')
        self.assertEqual(repository.extra_data['bug_tracker_type'],
                         'self_hosted_test')
        self.assertEqual(
            repository.extra_data['bug_tracker-test_repo_name'],
            'testrepo')
        self.assertEqual(
            repository.extra_data['bug_tracker_hosting_url'],
            'https://example.com')

    def test_with_hosting_service_with_hosting_bug_tracker(self):
        """Testing RepositoryForm with hosting service's bug tracker"""
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')
        account.data['password'] = 'testpass'
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_use_hosting': True,
            'bug_tracker_type': 'googlecode',
        })
        form.validate_repository = False

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertTrue(repository.extra_data['bug_tracker_use_hosting'])
        self.assertEqual(repository.bug_tracker,
                         'http://example.com/testuser/testrepo/issue/%s')
        self.assertNotIn('bug_tracker_type', repository.extra_data)
        self.assertFalse('bug_tracker-test_repo_name'
                         in repository.extra_data)
        self.assertFalse('bug_tracker-hosting_account_username'
                         in repository.extra_data)

    def test_with_hosting_service_with_hosting_bug_tracker_and_self_hosted(
            self):
        """Testing RepositoryForm with self-hosted hosting service's bug
        tracker
        """
        account = HostingServiceAccount.objects.create(
            username='testuser',
            service_name='self_hosted_test',
            hosting_url='https://example.com')
        account.data['password'] = 'testpass'
        account.save()

        account.data['authorization'] = {
            'token': '1234',
        }
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'hosting_url': 'https://example.com',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_use_hosting': True,
            'bug_tracker_type': 'googlecode',
        })
        form.validate_repository = False

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertTrue(repository.extra_data['bug_tracker_use_hosting'])
        self.assertEqual(repository.bug_tracker,
                         'https://example.com/testrepo/issue/%s')
        self.assertNotIn('bug_tracker_type', repository.extra_data)
        self.assertFalse('bug_tracker-test_repo_name'
                         in repository.extra_data)
        self.assertFalse('bug_tracker_hosting_url'
                         in repository.extra_data)

    def test_with_hosting_service_no_bug_tracker(self):
        """Testing RepositoryForm with no bug tracker"""
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')
        account.data['password'] = 'testpass'
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertFalse(repository.extra_data['bug_tracker_use_hosting'])
        self.assertEqual(repository.bug_tracker, '')
        self.assertNotIn('bug_tracker_type', repository.extra_data)

    def test_with_hosting_service_with_existing_custom_bug_tracker(self):
        """Testing RepositoryForm with existing custom bug tracker"""
        repository = Repository(name='test',
                                bug_tracker='http://example.com/issue/%s')

        form = RepositoryForm(instance=repository)
        self.assertFalse(form._get_field_data('bug_tracker_use_hosting'))
        self.assertEqual(form._get_field_data('bug_tracker_type'), 'custom')
        self.assertEqual(form.initial['bug_tracker'],
                         'http://example.com/issue/%s')

    def test_with_hosting_service_with_existing_bug_tracker_service(self):
        """Testing RepositoryForm with existing bug tracker service"""
        repository = Repository(name='test')
        repository.extra_data['bug_tracker_type'] = 'test'
        repository.extra_data['bug_tracker-test_repo_name'] = 'testrepo'
        repository.extra_data['bug_tracker-hosting_account_username'] = \
            'testuser'

        form = RepositoryForm(instance=repository)
        self.assertFalse(form._get_field_data('bug_tracker_use_hosting'))
        self.assertEqual(form._get_field_data('bug_tracker_type'), 'test')
        self.assertEqual(
            form._get_field_data('bug_tracker_hosting_account_username'),
            'testuser')

        self.assertIn('test', form.bug_tracker_forms)
        self.assertIn('default', form.bug_tracker_forms['test'])
        bitbucket_form = form.bug_tracker_forms['test']['default']
        self.assertEqual(
            bitbucket_form.fields['test_repo_name'].initial,
            'testrepo')

    def test_with_hosting_service_with_existing_bug_tracker_using_hosting(
            self):
        """Testing RepositoryForm with existing bug tracker using hosting
        service
        """
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')
        repository = Repository(name='test',
                                hosting_account=account)
        repository.extra_data['bug_tracker_use_hosting'] = True
        repository.extra_data['test_repo_name'] = 'testrepo'

        form = RepositoryForm(instance=repository)
        self.assertTrue(form._get_field_data('bug_tracker_use_hosting'))

    def test_bound_forms_with_post_with_repository_service(self):
        """Testing RepositoryForm binds hosting service forms only if matching
        posted repository hosting_service using default plan
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
        })

        # Make sure only the relevant forms are bound.
        for hosting_type, repo_forms in six.iteritems(form.repository_forms):
            for plan_id, repo_form in six.iteritems(repo_forms):
                self.assertEqual(repo_form.is_bound,
                                 hosting_type == 'test' and
                                 plan_id == form.DEFAULT_PLAN_ID)

        # Bug tracker info wasn't set in the form above.
        for hosting_type, bug_forms in six.iteritems(form.bug_tracker_forms):
            for plan_id, bug_form in six.iteritems(bug_forms):
                self.assertFalse(bug_form.is_bound)

        # Auth forms are never bound on initialize.
        for hosting_type, auth_form in six.iteritems(form.hosting_auth_forms):
            self.assertFalse(auth_form.is_bound)

    def test_bound_forms_with_post_with_bug_tracker_service(self):
        """Testing RepositoryForm binds hosting service forms only if matching
        posted bug tracker hosting_service using default plan
        """
        form = RepositoryForm({
            'name': 'test',
            'bug_tracker_type': 'test',
        })

        # Make sure only the relevant forms are bound.
        for hosting_type, bug_forms in six.iteritems(form.bug_tracker_forms):
            for plan_id, bug_form in six.iteritems(bug_forms):
                self.assertEqual(bug_form.is_bound,
                                 hosting_type == 'test' and
                                 plan_id == form.DEFAULT_PLAN_ID)

        # Repository info wasn't set in the form above.
        for hosting_type, repo_forms in six.iteritems(form.repository_forms):
            for plan_id, repo_form in six.iteritems(repo_forms):
                self.assertFalse(repo_form.is_bound)

        # Auth forms are never bound on initialize.
        for hosting_type, auth_form in six.iteritems(form.hosting_auth_forms):
            self.assertFalse(auth_form.is_bound)

    def test_bound_forms_with_post_with_repo_service_and_plan(self):
        """Testing RepositoryForm binds hosting service forms only if matching
        posted repository hosting_service with specific plans
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'github',
            'repository_plan': 'public',
        })

        # Make sure only the relevant forms are bound.
        for hosting_type, repo_forms in six.iteritems(form.repository_forms):
            for plan_id, repo_form in six.iteritems(repo_forms):
                self.assertEqual(repo_form.is_bound,
                                 hosting_type == 'github' and
                                 plan_id == 'public')

        # Bug tracker info wasn't set in the form above.
        for hosting_type, bug_forms in six.iteritems(form.bug_tracker_forms):
            for plan_id, bug_form in six.iteritems(bug_forms):
                self.assertFalse(bug_form.is_bound)

        # Auth forms are never bound on initialize.
        for hosting_type, auth_form in six.iteritems(form.hosting_auth_forms):
            self.assertFalse(auth_form.is_bound)

    def test_bound_forms_with_post_with_bug_tracker_service_and_plan(self):
        """Testing RepositoryForm binds hosting service forms only if matching
        posted bug tracker hosting_service with specific plans
        """
        form = RepositoryForm({
            'name': 'test',
            'bug_tracker_type': 'github',
            'bug_tracker_plan': 'public',
        })

        # Make sure only the relevant forms are bound.
        for hosting_type, bug_forms in six.iteritems(form.bug_tracker_forms):
            for plan_id, bug_form in six.iteritems(bug_forms):
                self.assertEqual(bug_form.is_bound,
                                 hosting_type == 'github' and
                                 plan_id == 'public')

        # Repository info wasn't set in the form above.
        for hosting_type, repo_forms in six.iteritems(form.repository_forms):
            for plan_id, repo_form in six.iteritems(repo_forms):
                self.assertFalse(repo_form.is_bound)

        # Auth forms are never bound on initialize.
        for hosting_type, auth_form in six.iteritems(form.hosting_auth_forms):
            self.assertFalse(auth_form.is_bound)

    def test_with_set_access_list(self):
        """Testing RepositoryForm with setting users access list"""
        user1 = User.objects.create(username='user1')
        user2 = User.objects.create(username='user2')
        User.objects.create(username='user3')

        group1 = self.create_review_group(name='group1', invite_only=True)
        group2 = self.create_review_group(name='group2', invite_only=True)
        self.create_review_group(name='group3', invite_only=True)

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'custom',
            'tool': self.git_tool_id,
            'path': '/path/to/test.git',
            'bug_tracker_type': 'none',
            'public': False,
            'users': [user1.pk, user2.pk],
            'review_groups': [group1.pk, group2.pk],
        })

        form.is_valid()
        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertFalse(repository.public)
        self.assertEqual(list(repository.users.all()), [user1, user2])
        self.assertEqual(list(repository.review_groups.all()),
                         [group1, group2])
