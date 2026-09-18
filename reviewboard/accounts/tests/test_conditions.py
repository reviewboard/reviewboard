"""Tests for reviewboard.accounts.conditions.

Version Added:
    9.0
"""

from __future__ import annotations

from django.contrib.auth.models import User
from djblets.conditions import Condition, ConditionSet

from reviewboard.accounts.conditions import (
    UserInGroupChoice,
    UserIsOneOfChoice,
    UserIsSuperuserChoice,
    user_condition_choices,
)
from reviewboard.testing import TestCase


class UserInGroupChoiceTests(TestCase):
    """Unit tests for UserInGroupChoice.

    Version Added:
        9.0
    """

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.choice = UserInGroupChoice()
        self.user = User.objects.create_user(username='test-user')

    def test_get_queryset_with_local_site(self) -> None:
        """Testing UserInGroupChoice.get_queryset with a LocalSite"""
        local_site = self.create_local_site()
        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2',
                                          local_site=local_site)

        self.choice.extra_state['local_site'] = local_site

        queryset = self.choice.get_queryset()
        self.assertNotIn(group1, queryset)
        self.assertIn(group2, queryset)

    def test_matches_with_contains_any(self) -> None:
        """Testing UserInGroupChoice matches with contains-any operator"""
        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')
        group1.users.add(self.user)

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('contains-any'),
                      [group1]),
        ])

        self.assertTrue(condition_set.matches(user=self.user))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('contains-any'),
                      [group2]),
        ])

        self.assertFalse(condition_set.matches(user=self.user))

    def test_matches_with_does_not_contain_any(self) -> None:
        """Testing UserInGroupChoice matches with does-not-contain-any
        operator
        """
        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')
        group1.users.add(self.user)

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-contain-any'),
                      [group2]),
        ])

        self.assertTrue(condition_set.matches(user=self.user))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-contain-any'),
                      [group1]),
        ])

        self.assertFalse(condition_set.matches(user=self.user))

    def test_matches_with_any(self) -> None:
        """Testing UserInGroupChoice matches with any operator"""
        group = self.create_review_group(name='group1')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('any')),
        ])

        self.assertFalse(condition_set.matches(user=self.user))

        group.users.add(self.user)

        self.assertTrue(condition_set.matches(user=self.user))

    def test_matches_with_none(self) -> None:
        """Testing UserInGroupChoice matches with none operator"""
        group = self.create_review_group(name='group1')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('none')),
        ])

        self.assertTrue(condition_set.matches(user=self.user))

        group.users.add(self.user)

        self.assertFalse(condition_set.matches(user=self.user))

    def test_matches_caches_groups(self) -> None:
        """Testing UserInGroupChoice matches caches the group list across
        conditions
        """
        group = self.create_review_group(name='group1')
        group.users.add(self.user)

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('contains-any'),
                      [group]),
            Condition(self.choice, self.choice.get_operator('any')),
        ])

        with self.assertNumQueries(1):
            self.assertTrue(condition_set.matches(user=self.user))


class UserIsSuperuserChoiceTests(TestCase):
    """Unit tests for UserIsSuperuserChoice.

    Version Added:
        9.0
    """

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.choice = UserIsSuperuserChoice()

    def test_matches(self) -> None:
        """Testing UserIsSuperuserChoice matches"""
        user = User.objects.create_user(username='test-user')
        superuser = User.objects.create_user(username='test-admin')
        superuser.is_superuser = True
        superuser.save(update_fields=('is_superuser',))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('is'), True),
        ])

        self.assertFalse(condition_set.matches(user=user))
        self.assertTrue(condition_set.matches(user=superuser))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('is'), False),
        ])

        self.assertTrue(condition_set.matches(user=user))
        self.assertFalse(condition_set.matches(user=superuser))


class UserIsOneOfChoiceTests(TestCase):
    """Unit tests for UserIsOneOfChoice.

    Version Added:
        9.0
    """

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.choice = UserIsOneOfChoice()

    def test_matches_with_one_of(self) -> None:
        """Testing UserIsOneOfChoice matches with one-of operator"""
        user1 = User.objects.create_user(username='test-user1')
        user2 = User.objects.create_user(username='test-user2')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('one-of'),
                      [user1]),
        ])

        self.assertTrue(condition_set.matches(user=user1))
        self.assertFalse(condition_set.matches(user=user2))

    def test_matches_with_not_one_of(self) -> None:
        """Testing UserIsOneOfChoice matches with not-one-of operator"""
        user1 = User.objects.create_user(username='test-user1')
        user2 = User.objects.create_user(username='test-user2')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('not-one-of'),
                      [user1]),
        ])

        self.assertFalse(condition_set.matches(user=user1))
        self.assertTrue(condition_set.matches(user=user2))


class UserConditionChoicesTests(TestCase):
    """Unit tests for the user_condition_choices registry.

    Version Added:
        9.0
    """

    def test_default_choices(self) -> None:
        """Testing user_condition_choices contains the default choices"""
        self.assertEqual(
            [
                choice_cls.choice_id
                for choice_cls in user_condition_choices
            ],
            [
                'user-in-group',
                'user-is-superuser',
                'user-is-one-of',
            ])
