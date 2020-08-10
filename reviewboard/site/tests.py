from __future__ import unicode_literals

import importlib

from django import forms
from django.contrib.auth.models import AnonymousUser, Permission, User
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template import Context, Template
from django.views.generic.base import View
from djblets.features.testing import override_feature_check
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.oauth.features import oauth2_service_feature
from reviewboard.oauth.models import Application
from reviewboard.reviews.models import DefaultReviewer, Group
from reviewboard.site.context_processors import AllPermsWrapper
from reviewboard.site.middleware import LocalSiteMiddleware
from reviewboard.site.mixins import (CheckLocalSiteAccessViewMixin,
                                     LocalSiteAwareModelFormMixin)
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing.testcase import TestCase


class BasicTests(TestCase):
    """Tests basic LocalSite functionality"""
    fixtures = ['test_users', 'test_site']

    def test_access(self):
        """Test LocalSite.is_accessible_by"""
        doc = User.objects.get(username="doc")
        dopey = User.objects.get(username="dopey")
        site = LocalSite.objects.get(name="local-site-1")

        self.assertTrue(site.is_accessible_by(doc))
        self.assertFalse(site.is_accessible_by(dopey))

    def test_access_with_public(self):
        """Test LocalSite.is_accessible_by with public LocalSites"""
        doc = User.objects.get(username="doc")
        dopey = User.objects.get(username="dopey")
        site = LocalSite.objects.get(name="local-site-1")
        site.public = True

        self.assertTrue(site.is_accessible_by(doc))
        self.assertTrue(site.is_accessible_by(dopey))

    def test_local_site_reverse_with_no_local_site(self):
        """Testing local_site_reverse with no local site"""
        request = HttpRequest()

        self.assertEqual(local_site_reverse('dashboard'),
                         '/dashboard/')
        self.assertEqual(local_site_reverse('dashboard', request=request),
                         '/dashboard/')
        self.assertEqual(local_site_reverse('user', args=['sample-user']),
                         '/users/sample-user/')
        self.assertEqual(
            local_site_reverse('user', kwargs={'username': 'sample-user'}),
            '/users/sample-user/')

    def test_local_site_reverse_with_local_site(self):
        """Testing local_site_reverse with a local site"""
        request = HttpRequest()
        request.GET['local_site_name'] = 'test'

        self.assertEqual(local_site_reverse('dashboard', request=request),
                         '/dashboard/')
        self.assertEqual(local_site_reverse('user', args=['sample-user'],
                                            request=request),
                         '/users/sample-user/')
        self.assertEqual(
            local_site_reverse('user', kwargs={'username': 'sample-user'},
                               request=request),
            '/users/sample-user/')


class LocalSiteMiddlewareTests(TestCase):
    """Unit tests for reviewboard.site.middleware.LocalSiteMiddleware."""

    def setUp(self):
        super(LocalSiteMiddlewareTests, self).setUp()

        self.middleware = LocalSiteMiddleware()

    def test_request_local_site_empty(self):
        """Testing LocalSiteMiddleware's request.local_site with no LocalSite
        """
        request = HttpRequest()
        self.middleware.process_view(request=request, view_func=None,
                                     view_args=None, view_kwargs={})

        self.assertTrue(hasattr(request, '_local_site_name'))
        self.assertTrue(hasattr(request, 'local_site'))
        self.assertIsNone(request._local_site_name)
        self.assertIsNone(request.local_site)

    def test_request_local_site_not_empty(self):
        """Testing LocalSiteMiddleware's request.local_site with a LocalSite"""
        local_site = LocalSite.objects.create(name='test-site')

        request = HttpRequest()
        self.middleware.process_view(
            request=request,
            view_func=None,
            view_args=None,
            view_kwargs={
                'local_site_name': local_site.name,
            })

        self.assertTrue(hasattr(request, '_local_site_name'))
        self.assertTrue(hasattr(request, 'local_site'))
        self.assertEqual(request._local_site_name, 'test-site')
        self.assertEqual(request.local_site, local_site)


class PermissionWrapperTests(TestCase):
    """Testing the LocalSite-aware permissions wrapper."""
    def setUp(self):
        super(PermissionWrapperTests, self).setUp()

        self.user = User.objects.get(username='doc')
        self.assertFalse(self.user.is_superuser)

    @add_fixtures(['test_users', 'test_site'])
    def test_lookup_global_permission(self):
        """Testing AllPermsWrapper with global permission lookup"""
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))

        perms = AllPermsWrapper(self.user, self.local_site_name)

        self.assertIn('reviews.delete_reviewrequest', perms)
        self.assertNotIn('reviews.fake_permission', perms)

    @add_fixtures(['test_users', 'test_site'])
    def test_lookup_site_permission(self):
        """Testing AllPermsWrapper with site permission lookup"""
        local_site = LocalSite.objects.get(name=self.local_site_name)

        local_site_profile = self.user.get_site_profile(local_site)
        local_site_profile.permissions['reviews.can_change_status'] = True
        local_site_profile.save(update_fields=('permissions',))

        perms = AllPermsWrapper(self.user, self.local_site_name)

        self.assertIn('reviews.can_change_status', perms)
        self.assertNotIn('reviews.fake_permission', perms)


class AdminPermissionTests(TestCase):
    fixtures = ['test_users', 'test_site']

    def setUp(self):
        super(AdminPermissionTests, self).setUp()

        self.user = User.objects.get(username='doc')
        self.assertFalse(self.user.is_superuser)

        self.local_site = LocalSite.objects.get(name=self.local_site_name)
        self.local_site.admins.add(self.user)

    def test_assigned_permissions(self):
        """Testing LocalSite assigned admin permissions"""
        self.assertTrue(self.user.has_perm(
            'hostingsvcs.change_hostingserviceaccount', self.local_site))
        self.assertTrue(self.user.has_perm(
            'hostingsvcs.create_hostingserviceaccount', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.can_change_status', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.can_edit_reviewrequest', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.can_submit_as_another_user', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.change_default_reviewer', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.add_group', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.change_group', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.delete_file', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.delete_screenshot', self.local_site))
        self.assertTrue(self.user.has_perm(
            'scmtools.add_repository', self.local_site))
        self.assertTrue(self.user.has_perm(
            'scmtools.change_repository', self.local_site))

    def test_invalid_permissions(self):
        """Testing LocalSite invalid admin permissions"""
        self.assertFalse(self.user.has_perm(
            'reviews.delete_reviewrequest', self.local_site))
        self.assertFalse(self.user.has_perm(
            'dummy.permission', self.local_site))


class TemplateTagTests(TestCase):
    def test_local_site_url_with_no_local_site(self):
        """Testing localsite's {% url %} with no local site"""
        context = Context({})

        t = Template('{% url "dashboard" %}')
        self.assertEqual(t.render(context), '/dashboard/')

        t = Template('{% url "user" "sample-user" %}')
        self.assertEqual(t.render(context), '/users/sample-user/')

    def test_local_site_url_with_local_site(self):
        """Testing localsite's {% url %} with local site"""

        # Make sure that {% url %} is registered as a built-in tag.
        importlib.import_module('reviewboard.site.templatetags')

        context = Context({
            'local_site_name': 'test',
        })

        t = Template('{% url "dashboard" %}')
        self.assertEqual(t.render(context), '/s/test/dashboard/')

        t = Template('{% url "user" "sample-user" %}')
        self.assertEqual(t.render(context), '/s/test/users/sample-user/')


class CheckLocalSiteAccessViewMixinTests(TestCase):
    """Unit tests for CheckLocalSiteAccessViewMixin."""

    @add_fixtures(['test_site', 'test_users'])
    def test_dispatch_with_local_site_and_allowed(self):
        """Testing CheckLocalSiteAccessViewMixin.dispatch with LocalSite and
        access allowed
        """
        class MyView(CheckLocalSiteAccessViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertIsNotNone(view.local_site)
                self.assertEqual(view.local_site.name, 'local-site-1')

                return HttpResponse('success')

        local_site = self.get_local_site(self.local_site_name)
        request = self.create_http_request(user=local_site.users.all()[0],
                                           local_site=local_site)

        view = MyView.as_view()
        response = view(request, local_site_name=local_site.name)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'success')

    @add_fixtures(['test_site', 'test_users'])
    def test_dispatch_with_local_site_and_not_allowed(self):
        """Testing CheckLocalSiteAccessViewMixin.dispatch with LocalSite and
        access not allowed
        """
        class MyView(CheckLocalSiteAccessViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertIsNotNone(view.local_site)
                self.assertEqual(view.local_site.name, 'local-site-1')

                return HttpResponse('success')

        view = MyView.as_view()

        local_site = self.get_local_site(self.local_site_name)
        request = self.create_http_request(
            user=User.objects.create_user(username='test123',
                                          email='test123@example.com'),
            local_site=local_site,
            view=view)

        response = view(request, local_site_name=local_site.name)
        self.assertEqual(response.status_code, 403)

    @add_fixtures(['test_site'])
    def test_dispatch_with_local_site_and_anonymous(self):
        """Testing CheckLocalSiteAccessViewMixin.dispatch with LocalSite and
        anonymous user
        """
        class MyView(CheckLocalSiteAccessViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertIsNotNone(view.local_site)
                self.assertEqual(view.local_site.name, 'local-site-1')

                return HttpResponse('success')

        view = MyView.as_view()

        local_site = self.get_local_site(self.local_site_name)
        request = self.create_http_request(local_site=local_site,
                                           view=view)

        response = view(request, local_site_name=local_site.name)
        self.assertIsInstance(response, HttpResponseRedirect)

    @add_fixtures(['test_site', 'test_users'])
    def test_dispatch_with_no_local_site(self):
        """Testing CheckLocalSiteAccessViewMixin.dispatch with no LocalSite"""
        class MyView(CheckLocalSiteAccessViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertIsNone(view.local_site)

                return HttpResponse('success')

        view = MyView.as_view()

        request = self.create_http_request(
            user=User.objects.get(username='doc'),
            view=view)

        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'success')


class OAuth2ApplicationTests(TestCase):
    """Testing Applicications assigned to a Local Site."""

    fixtures = ['test_users', 'test_site']

    def test_disable_reassign_to_admin(self):
        """Testing an Application is disabled and re-assigned to a Local Site
        admin when its owner is removed from a Local Site
        """
        with override_feature_check(oauth2_service_feature.feature_id, True):
            local_site = LocalSite.objects.get(pk=1)
            user = User.objects.get(username='doc')
            admin = User.objects.get(username='admin')
            application = self.create_oauth_application(user=user,
                                                        local_site=local_site)

            local_site.users.remove(user)

            application = Application.objects.get(pk=application.pk)
            self.assertTrue(application.is_disabled_for_security)
            self.assertEqual(application.original_user_id, user.pk)
            self.assertEqual(application.user_id, admin.pk)
            self.assertFalse(application.enabled)


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
