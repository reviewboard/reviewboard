"""Tests for reviewboard.hostingsvcs.models.ConfiguredBugTracker.

Version Added:
    9.0
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.test.client import RequestFactory
from djblets.conditions import Condition, ConditionSet

from reviewboard.accounts.conditions import (
    UserIsSuperuserChoice,
)
from reviewboard.hostingsvcs.models import (
    ConfiguredBugTracker,
    HostingServiceAccount,
)
from reviewboard.testing import TestCase


class ConfiguredBugTrackerTests(TestCase):
    """Unit tests for ConfiguredBugTracker.

    Version Added:
        9.0
    """

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.user = User.objects.create_user(username='test-user')

    def test_service(self) -> None:
        """Testing ConfiguredBugTracker.service with a hosting account"""
        account = HostingServiceAccount.objects.create(
            service_name='splat',
            username='test-user')
        bug_tracker = self.create_bug_tracker(
            name='My Splat',
            service_name='splat',
            hosting_account=account)

        service = bug_tracker.service
        self.assertEqual(service.hosting_service_id, 'splat')
        self.assertIs(service.account, account)

    def test_service_without_account(self) -> None:
        """Testing ConfiguredBugTracker.service without a hosting account"""
        bug_tracker = self.create_bug_tracker(
            name='My Splat',
            service_name='splat')

        service = bug_tracker.service
        self.assertEqual(service.hosting_service_id, 'splat')
        self.assertIsNone(service.account.pk)
        self.assertEqual(service.account.service_name, 'splat')

    def test_is_usable_by_with_empty_conditions(self) -> None:
        """Testing ConfiguredBugTracker.is_usable_by with empty conditions"""
        bug_tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='splat')

        self.assertTrue(bug_tracker.is_usable_by(self.user))

    def test_is_usable_by_with_empty_condition_list(self) -> None:
        """Testing ConfiguredBugTracker.is_usable_by with a serialized empty
        condition list
        """
        bug_tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='splat',
            user_conditions={
                'mode': 'all',
                'conditions': [],
            })

        self.assertTrue(bug_tracker.is_usable_by(self.user))

    def test_is_usable_by_with_matching_conditions(self) -> None:
        """Testing ConfiguredBugTracker.is_usable_by with matching conditions
        """
        group = self.create_review_group(name='group1')
        group.users.add(self.user)

        bug_tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='splat',
            limit_to_groups=[group])

        self.assertTrue(bug_tracker.is_usable_by(self.user))

    def test_is_usable_by_without_matching_conditions(self) -> None:
        """Testing ConfiguredBugTracker.is_usable_by without matching
        conditions
        """
        group = self.create_review_group(name='group1')

        bug_tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='splat',
            limit_to_groups=[group])

        self.assertFalse(bug_tracker.is_usable_by(self.user))

    def test_is_usable_by_with_superuser_condition(self) -> None:
        """Testing ConfiguredBugTracker.is_usable_by with a superuser condition
        """
        superuser = User.objects.create_user(username='test-admin')
        superuser.is_superuser = True
        superuser.save(update_fields=('is_superuser',))

        choice = UserIsSuperuserChoice()
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(choice, choice.get_operator('is'), True),
        ])

        bug_tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='splat',
            user_conditions=condition_set.serialize())

        self.assertFalse(bug_tracker.is_usable_by(self.user))
        self.assertTrue(bug_tracker.is_usable_by(superuser))

    def test_is_usable_by_with_bad_conditions(self) -> None:
        """Testing ConfiguredBugTracker.is_usable_by fails closed with bad
        condition data
        """
        bug_tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='splat',
            user_conditions={
                'mode': 'all',
                'conditions': [
                    {
                        'choice': 'xxx-invalid-choice',
                        'op': 'is',
                        'value': True,
                    },
                ],
            })

        self.assertFalse(bug_tracker.is_usable_by(self.user))

    def test_is_usable_by_caches_on_request(self) -> None:
        """Testing ConfiguredBugTracker.is_usable_by caches results on the
        request
        """
        group = self.create_review_group(name='group1')
        group.users.add(self.user)

        bug_tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='splat',
            limit_to_groups=[group])

        request = RequestFactory().get('/')

        self.assertTrue(bug_tracker.is_usable_by(self.user, request=request))

        with self.assertNumQueries(0):
            self.assertTrue(bug_tracker.is_usable_by(self.user,
                                                     request=request))

    def test_is_mutable_by(self) -> None:
        """Testing ConfiguredBugTracker.is_mutable_by"""
        bug_tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='splat')

        admin = User.objects.create_user(username='test-admin')
        admin.is_superuser = True
        admin.save(update_fields=('is_superuser',))

        self.assertFalse(bug_tracker.is_mutable_by(self.user))
        self.assertTrue(bug_tracker.is_mutable_by(admin))

    def test_display_mode(self) -> None:
        """Testing ConfiguredBugTracker.display_mode"""
        bug_tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='splat',
            settings={
                'display_mode': ConfiguredBugTracker.DISPLAY_MODE_DETAILED,
            })

        self.assertEqual(bug_tracker.display_mode,
                         ConfiguredBugTracker.DISPLAY_MODE_DETAILED)

    def test_display_mode_defaults_to_compact(self) -> None:
        """Testing ConfiguredBugTracker.display_mode defaults to compact"""
        bug_tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='splat')

        self.assertEqual(bug_tracker.display_mode,
                         ConfiguredBugTracker.DISPLAY_MODE_COMPACT)

    def test_display_mode_with_unknown_value(self) -> None:
        """Testing ConfiguredBugTracker.display_mode with an unknown stored
        value
        """
        bug_tracker = self.create_bug_tracker(
            name='Tracker',
            service_name='splat',
            settings={
                'display_mode': 'xxx-invalid',
            })

        self.assertEqual(bug_tracker.display_mode,
                         ConfiguredBugTracker.DISPLAY_MODE_COMPACT)
