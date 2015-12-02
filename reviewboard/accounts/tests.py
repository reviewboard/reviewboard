from __future__ import unicode_literals

import re

from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.backends import (get_enabled_auth_backends,
                                           INVALID_USERNAME_CHAR_REGEX,
                                           StandardAuthBackend)
from reviewboard.accounts.forms.pages import AccountPageForm
from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.accounts.pages import (AccountPage, get_page_classes,
                                        register_account_page_class,
                                        unregister_account_page_class,
                                        _clear_page_defaults)
from reviewboard.testing import TestCase


class AuthBackendTests(TestCase):
    """Testing authentication backends."""

    def _get_standard_auth_backend(self):
        backend = None

        for backend in get_enabled_auth_backends():
            # We do not use isinstance here because we specifically want a
            # StandardAuthBackend and not an instance of a subclass of it.
            if type(backend) is StandardAuthBackend:
                break

        self.assertIs(type(backend), StandardAuthBackend)

        return backend

    @add_fixtures(['test_users'])
    def test_get_or_create_user_exists(self):
        """Testing StandardAuthBackend.get_or_create_user when the requested
        user already exists
        """
        original_count = User.objects.count()

        user = User.objects.get(username='doc')
        backend = self._get_standard_auth_backend()
        result = backend.get_or_create_user('doc', None)

        self.assertEqual(original_count, User.objects.count())
        self.assertEqual(user, result)

    def test_get_or_create_user_new(self):
        """Testing StandardAuthBackend.get_or_create_user when the requested
        user does not exist
        """
        backend = self._get_standard_auth_backend()
        self.assertIsInstance(backend, StandardAuthBackend)
        user = backend.get_or_create_user('doc', None)

        self.assertIsNone(user)

    @add_fixtures(['test_users'])
    def test_get_user_exists(self):
        """Testing StandardAuthBackend.get_user when the requested user already
        exists
        """
        user = User.objects.get(username='doc')
        backend = self._get_standard_auth_backend()
        result = backend.get_user(user.pk)

        self.assertEqual(user, result)

    def test_get_user_not_exists(self):
        """Testing StandardAuthBackend.get_user when the requested user does
        not exist
        """
        backend = self._get_standard_auth_backend()
        result = backend.get_user(1)

        self.assertIsNone(result)


class ProfileTests(TestCase):
    """Testing the Profile model."""
    fixtures = ['test_users']

    def test_is_profile_visible_with_public(self):
        """Testing User.is_profile_public with public profiles."""
        user1 = User.objects.get(username='admin')
        user2 = User.objects.get(username='doc')

        self.assertTrue(user1.is_profile_visible(user2))

    def test_is_profile_visible_with_private(self):
        """Testing User.is_profile_public with private profiles."""
        user1 = User.objects.get(username='admin')
        user2 = User.objects.get(username='doc')

        profile = user1.get_profile()
        profile.is_private = True
        profile.save()

        self.assertFalse(user1.is_profile_visible(user2))
        self.assertTrue(user1.is_profile_visible(user1))

        user2.is_staff = True
        self.assertTrue(user1.is_profile_visible(user2))

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_is_star_unstar_updating_count_correctly(self):
        """Testing if star, unstar affect review request counts correctly."""
        user1 = User.objects.get(username='admin')
        profile1 = user1.get_profile()
        review_request = self.create_review_request(publish=True)

        site_profile = profile1.site_profiles.get(local_site=None)

        profile1.star_review_request(review_request)
        site_profile = LocalSiteProfile.objects.get(pk=site_profile.pk)

        self.assertTrue(review_request in
                        profile1.starred_review_requests.all())
        self.assertEqual(site_profile.starred_public_request_count, 1)

        profile1.unstar_review_request(review_request)
        site_profile = LocalSiteProfile.objects.get(pk=site_profile.pk)

        self.assertFalse(review_request in
                         profile1.starred_review_requests.all())
        self.assertEqual(site_profile.starred_public_request_count, 0)


class AccountPageTests(TestCase):
    """Testing account page functionality."""
    def tearDown(self):
        # Force the next request to re-populate the list of default pages.
        _clear_page_defaults()

    def test_default_pages(self):
        """Testing default list of account pages"""
        page_classes = list(get_page_classes())
        self.assertEqual(len(page_classes), 4)

        page_class_ids = [page_cls.page_id for page_cls in page_classes]
        self.assertEqual(
            set(page_class_ids),
            set(['settings', 'authentication', 'profile', 'groups']))

    def test_register_account_page_class(self):
        """Testing register_account_page_class"""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        register_account_page_class(MyPage)

        page_classes = list(get_page_classes())
        self.assertEqual(len(page_classes), 5)
        self.assertEqual(page_classes[-1], MyPage)

    def test_register_account_page_class_with_duplicate(self):
        """Testing register_account_page_class with duplicate page"""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        register_account_page_class(MyPage)
        self.assertRaises(KeyError,
                          lambda: register_account_page_class(MyPage))

    def test_unregister_account_page_class(self):
        """Testing unregister_account_page_class"""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        register_account_page_class(MyPage)
        unregister_account_page_class(MyPage)

        page_classes = list(get_page_classes())
        self.assertEqual(len(page_classes), 4)

    def test_unregister_unknown_account_page_class(self):
        """Testing unregister_account_page_class with unknown page"""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        self.assertRaises(KeyError,
                          lambda: unregister_account_page_class(MyPage))

    def test_add_form_to_page(self):
        """Testing AccountPage.add_form"""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        class MyForm(AccountPageForm):
            form_id = 'test-form'

        register_account_page_class(MyPage)
        MyPage.add_form(MyForm)

        self.assertEqual(MyPage.form_classes, [MyForm])

    def test_add_duplicate_form_to_page(self):
        """Testing AccountPage.add_form with duplicate form ID"""
        class MyForm(AccountPageForm):
            form_id = 'test-form'

        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'
            form_classes = [MyForm]

        register_account_page_class(MyPage)
        self.assertRaises(KeyError, lambda: MyPage.add_form(MyForm))
        self.assertEqual(MyPage.form_classes, [MyForm])

    def test_remove_form_from_page(self):
        """Testing AccountPage.remove_form"""
        class MyForm(AccountPageForm):
            form_id = 'test-form'

        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'
            form_classes = [MyForm]

        register_account_page_class(MyPage)
        MyPage.remove_form(MyForm)

        self.assertEqual(MyPage.form_classes, [])

    def test_remove_unknown_form_from_page(self):
        """Testing AccountPage.remove_form with unknown form"""
        class MyForm(AccountPageForm):
            form_id = 'test-form'

        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        register_account_page_class(MyPage)
        self.assertRaises(KeyError, lambda: MyPage.remove_form(MyForm))

    def test_default_form_classes_for_page(self):
        """Testing AccountPage._default_form_classes persistence"""
        class MyForm(AccountPageForm):
            form_id = 'test-form'

        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'
            form_classes = [MyForm]

        register_account_page_class(MyPage)
        self.assertEqual(MyPage.form_classes, [MyForm])
        unregister_account_page_class(MyPage)
        self.assertEqual(MyPage.form_classes, [])
        register_account_page_class(MyPage)
        self.assertEqual(MyPage.form_classes, [MyForm])

    def test_empty_default_form_classes_for_page(self):
        """Testing AccountPage._default_form_classes with no form_classes"""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        class MyForm(AccountPageForm):
            form_id = 'test-form'

        register_account_page_class(MyPage)
        self.assertEqual(MyPage.form_classes, [])
        MyPage.add_form(MyForm)
        self.assertEqual(MyPage.form_classes, [MyForm])
        unregister_account_page_class(MyPage)
        self.assertEqual(MyPage.form_classes, [])
        register_account_page_class(MyPage)
        self.assertEqual(MyPage.form_classes, [])


class UsernameTests(TestCase):
    cases = [
        ('spaces  ', 'spaces'),
        ('spa ces', 'spaces'),
        ('CASES', 'cases'),
        ('CaSeS', 'cases'),
        ('Spec!al', 'specal'),
        ('email@example.com', 'email@example.com'),
        ('da-shes', 'da-shes'),
        ('un_derscores', 'un_derscores'),
        ('mu ^lt&^ipl Es', 'multiples'),
    ]

    def test(self):
        """Testing username regex for LDAP/AD backends"""
        for orig, new in self.cases:
            self.assertEqual(
                re.sub(INVALID_USERNAME_CHAR_REGEX, '', orig).lower(),
                new)
