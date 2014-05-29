from __future__ import unicode_literals

import re

from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.backends import INVALID_USERNAME_CHAR_REGEX
from reviewboard.accounts.forms.pages import AccountPageForm
from reviewboard.accounts.models import LocalSiteProfile, Trophy
from reviewboard.accounts.pages import (AccountPage, get_page_classes,
                                        register_account_page_class,
                                        unregister_account_page_class,
                                        _clear_page_defaults)
from reviewboard.testing import TestCase


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


class TrophyTests(TestCase):
    """Testing the Trophy Case."""
    fixtures = ['test_users']

    def test_is_fish_trophy_awarded_for_new_review_request(self):
        """Testing if a fish trophy is awarded for a new review request."""
        user1 = User.objects.get(username='doc')
        category = 'fish'
        review_request = self.create_review_request(publish=True, id=3223,
                                                    submitter=user1)
        trophies = Trophy.objects.get_trophies(review_request)
        self.assertEqual(trophies[0].category, category)
        self.assertTrue(
            trophies[0].review_request.extra_data['calculated_trophies'])

    def test_is_fish_trophy_awarded_for_older_review_request(self):
        """Testing if a fish trophy is awarded for an older review request."""
        user1 = User.objects.get(username='doc')
        category = 'fish'
        review_request = self.create_review_request(publish=True, id=1001,
                                                    submitter=user1)
        del review_request.extra_data['calculated_trophies']
        trophies = Trophy.objects.get_trophies(review_request)
        self.assertEqual(trophies[0].category, category)
        self.assertTrue(
            trophies[0].review_request.extra_data['calculated_trophies'])

    def test_is_milestone_trophy_awarded_for_new_review_request(self):
        """Testing if a milestone trophy is awarded for a new review request.
        """
        user1 = User.objects.get(username='doc')
        category = 'milestone'
        review_request = self.create_review_request(publish=True, id=1000,
                                                    submitter=user1)
        trophies = Trophy.objects.compute_trophies(review_request)
        self.assertEqual(trophies[0].category, category)
        self.assertTrue(
            trophies[0].review_request.extra_data['calculated_trophies'])

    def test_is_milestone_trophy_awarded_for_older_review_request(self):
        """Testing if a milestone trophy is awarded for an older review
        request.
        """
        user1 = User.objects.get(username='doc')
        category = 'milestone'
        review_request = self.create_review_request(publish=True, id=10000,
                                                    submitter=user1)
        del review_request.extra_data['calculated_trophies']
        trophies = Trophy.objects.compute_trophies(review_request)
        self.assertEqual(trophies[0].category, category)
        self.assertTrue(
            trophies[0].review_request.extra_data['calculated_trophies'])

    def test_is_no_trophy_awarded(self):
        """Testing if no trophy is awarded."""
        user1 = User.objects.get(username='doc')
        review_request = self.create_review_request(publish=True, id=999,
                                                    submitter=user1)
        trophies = Trophy.objects.compute_trophies(review_request)
        self.assertFalse(trophies)
