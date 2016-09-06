from __future__ import unicode_literals

from djblets.conditions import ConditionSet, Condition

from reviewboard.scmtools.conditions import (IsRepositoryPrivateOperator,
                                             IsRepositoryPublicOperator,
                                             RepositoryTypeChoice,
                                             RepositoriesChoice)
from reviewboard.site.models import LocalSite
from reviewboard.testing.testcase import TestCase


class RepositoryOperatorTests(TestCase):
    """Unit tests for repository condition operators."""

    fixtures = ['test_scmtools']

    def test_is_private_with_match(self):
        """Testing IsRepositoryPrivateOperator with match"""
        repository = self.create_repository(public=False)

        self.assertTrue(self._check_match(
            IsRepositoryPrivateOperator,
            repository))

    def test_is_private_without_match(self):
        """Testing IsRepositoryPrivateOperator without match"""
        repository = self.create_repository(public=True)

        self.assertFalse(self._check_match(
            IsRepositoryPrivateOperator,
            repository))
        self.assertFalse(self._check_match(
            IsRepositoryPrivateOperator,
            None))

    def test_is_public_with_match(self):
        """Testing IsRepositoryPublicOperator with match"""
        repository = self.create_repository(public=True)

        self.assertTrue(self._check_match(
            IsRepositoryPublicOperator,
            repository))

    def test_is_public_without_match(self):
        """Testing IsRepositoryPublicOperator without match"""
        repository = self.create_repository(public=False)

        self.assertFalse(self._check_match(
            IsRepositoryPublicOperator,
            repository))
        self.assertFalse(self._check_match(
            IsRepositoryPublicOperator,
            None))

    def _check_match(self, op_cls, match_value, condition_value=None):
        op = op_cls(None)
        return op.matches(match_value=match_value,
                          condition_value=condition_value)


class RepositoriesChoiceTests(TestCase):
    """Unit tests for reviewboard.scmtools.conditions.RepositoriesChoice."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(RepositoriesChoiceTests, self).setUp()

        self.choice = RepositoriesChoice()

    def test_get_queryset(self):
        """Testing RepositoriesChoice.get_queryset"""
        repo1 = self.create_repository(name='repo1')
        repo2 = self.create_repository(name='repo2')

        self.assertQuerysetEqual(
            self.choice.get_queryset().order_by('id'),
            [repo1.pk, repo2.pk],
            transform=lambda repo: repo.pk)

    def test_get_queryset_with_local_site(self):
        """Testing RepositoriesChoice.get_queryset with LocalSite"""
        good_site = LocalSite.objects.create(name='good-site')
        bad_site = LocalSite.objects.create(name='bad-site')

        # These should match.
        repo1 = self.create_repository(name='repo1', local_site=good_site)
        repo2 = self.create_repository(name='repo2', local_site=good_site)

        # These should not match.
        self.create_repository(name='repo3')
        self.create_repository(name='repo4', local_site=bad_site)

        self.choice.extra_state['local_site'] = good_site

        self.assertQuerysetEqual(
            self.choice.get_queryset().order_by('id'),
            [repo1.pk, repo2.pk],
            transform=lambda repo: repo.pk)

    def test_matches_with_any_op(self):
        """Testing RepositoriesChoice.matches with "any" operator"""
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('any')),
        ])

        self.assertTrue(condition_set.matches(
            repository=self.create_repository()))
        self.assertFalse(condition_set.matches(repository=None))

    def test_matches_with_none_op(self):
        """Testing RepositoriesChoice.matches with "none" operator"""
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('none')),
        ])

        self.assertTrue(condition_set.matches(repository=None))
        self.assertFalse(condition_set.matches(
            repository=self.create_repository()))

    def test_matches_with_one_of_op(self):
        """Testing RepositoriesChoice.matches with "one-of" operator"""
        repository1 = self.create_repository(name='repo1')
        repository2 = self.create_repository(name='repo2')
        repository3 = self.create_repository(name='repo3')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('one-of'),
                      [repository1, repository2])
        ])

        self.assertTrue(condition_set.matches(repository=repository1))
        self.assertTrue(condition_set.matches(repository=repository2))
        self.assertFalse(condition_set.matches(repository=repository3))

    def test_matches_with_not_one_of_op(self):
        """Testing RepositoriesChoice.matches with "not-one-of" operator"""
        repository1 = self.create_repository(name='repo1')
        repository2 = self.create_repository(name='repo2')
        repository3 = self.create_repository(name='repo3')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('not-one-of'),
                      [repository1, repository2])
        ])

        self.assertFalse(condition_set.matches(repository=repository1))
        self.assertFalse(condition_set.matches(repository=repository2))
        self.assertTrue(condition_set.matches(repository=repository3))

    def test_matches_with_is_public_op(self):
        """Testing RepositoriesChoice.matches with "is-public" operator"""
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('is-public')),
        ])

        self.assertTrue(condition_set.matches(
            repository=self.create_repository(name='repo1', public=True)))
        self.assertFalse(condition_set.matches(
            repository=self.create_repository(name='repo2', public=False)))

    def test_matches_with_is_private_op(self):
        """Testing RepositoriesChoice.matches with "is-private" operator"""
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('is-private')),
        ])

        self.assertTrue(condition_set.matches(
            repository=self.create_repository(name='repo1', public=False)))
        self.assertFalse(condition_set.matches(
            repository=self.create_repository(name='repo2', public=True)))


class RepositoryTypeChoiceTests(TestCase):
    """Unit tests for reviewboard.scmtools.conditions.RepositoryTypeChoice."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(RepositoryTypeChoiceTests, self).setUp()

        self.choice = RepositoryTypeChoice()

    def test_matches_with_one_of_op(self):
        """Testing RepositoryTypeChoice.matches with "one-of" operator"""
        repository1 = self.create_repository(name='repo1',
                                             tool_name='Git')
        repository2 = self.create_repository(name='repo2',
                                             tool_name='Subversion')
        repository3 = self.create_repository(name='repo3',
                                             tool_name='CVS')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('one-of'),
                      [repository1.tool, repository2.tool])
        ])

        self.assertTrue(condition_set.matches(repository=repository1))
        self.assertTrue(condition_set.matches(repository=repository2))
        self.assertFalse(condition_set.matches(repository=repository3))

    def test_matches_with_not_one_of_op(self):
        """Testing RepositoryTypeChoice.matches with "not-one-of" operator"""
        repository1 = self.create_repository(name='repo1',
                                             tool_name='Git')
        repository2 = self.create_repository(name='repo2',
                                             tool_name='Subversion')
        repository3 = self.create_repository(name='repo3',
                                             tool_name='CVS')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('not-one-of'),
                      [repository1.tool, repository2.tool])
        ])

        self.assertFalse(condition_set.matches(repository=repository1))
        self.assertFalse(condition_set.matches(repository=repository2))
        self.assertTrue(condition_set.matches(repository=repository3))
