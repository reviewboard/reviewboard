from __future__ import unicode_literals

import re

from django.contrib.auth.models import User
from django.test.client import RequestFactory
from djblets.conditions import ConditionSet, Condition

from reviewboard.reviews.conditions import (AnyReviewGroupsPublicOperator,
                                            AllReviewGroupsInviteOnlyOperator,
                                            ReviewGroupsChoice,
                                            ReviewRequestAllDiffFilesChoice,
                                            ReviewRequestAnyDiffFileChoice,
                                            ReviewRequestRepositoriesChoice,
                                            ReviewRequestRepositoryTypeChoice,
                                            ReviewRequestReviewGroupsChoice,
                                            ReviewRequestOwnerChoice,
                                            ReviewRequestReviewerChoice,
                                            ReviewRequestParticipantChoice)
from reviewboard.reviews.models import Group
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class ReviewGroupOperatorTests(TestCase):
    """Unit tests for review group condition operators."""

    def test_any_public_with_match(self):
        """Testing AnyReviewGroupsPublicOperator with match"""

        self.assertTrue(self._check_match(
            AnyReviewGroupsPublicOperator,
            [
                self.create_review_group(name='group1', invite_only=False),
                self.create_review_group(name='group2', invite_only=True),
            ]))

    def test_any_public_without_match(self):
        """Testing AnyReviewGroupsPublicOperator without match"""
        self.create_review_group(name='group1', invite_only=False)
        private_group = self.create_review_group(name='group2',
                                                 invite_only=True)

        self.assertFalse(self._check_match(
            AnyReviewGroupsPublicOperator,
            [private_group]))
        self.assertFalse(self._check_match(
            AnyReviewGroupsPublicOperator,
            []))

    def test_all_invite_only_with_match(self):
        """Testing AllReviewGroupsInviteOnlyOperator with match"""

        self.assertTrue(self._check_match(
            AllReviewGroupsInviteOnlyOperator,
            [
                self.create_review_group(name='group1', invite_only=True),
                self.create_review_group(name='group2', invite_only=True),
            ]))

    def test_all_invite_only_without_match(self):
        """Testing AllReviewGroupsInviteOnlyOperator without match"""
        group1 = self.create_review_group(name='group1', invite_only=False)
        group2 = self.create_review_group(name='group2', invite_only=True)

        self.assertFalse(self._check_match(
            AllReviewGroupsInviteOnlyOperator,
            [group1, group2]))
        self.assertFalse(self._check_match(
            AllReviewGroupsInviteOnlyOperator,
            []))

    def _check_match(self, op_cls, match_value, condition_value=None):
        op = op_cls(None)
        return op.matches(match_value=match_value,
                          condition_value=condition_value)


class ReviewGroupsChoiceTests(TestCase):
    """Unit tests for reviewboard.reviews.conditions.ReviewGroupsChoice."""

    def setUp(self):
        super(ReviewGroupsChoiceTests, self).setUp()

        self.request = RequestFactory().request()
        self.request.user = User.objects.create(username='test-user')

        self.choice = ReviewGroupsChoice(request=self.request)

    def test_get_queryset(self):
        """Testing ReviewGroupsChoice.get_queryset"""
        # These should match.
        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')

        # These should not match.
        self.create_review_group(name='group3',
                                 visible=False)

        self.assertQuerysetEqual(
            self.choice.get_queryset(),
            [group1.pk, group2.pk],
            transform=lambda group: group.pk)

    def test_get_queryset_with_local_site(self):
        """Testing ReviewGroupsChoice.get_queryset with LocalSite"""
        good_site = LocalSite.objects.create(name='good-site')
        bad_site = LocalSite.objects.create(name='bad-site')

        # These should match.
        group1 = self.create_review_group(name='group1',
                                          local_site=good_site)
        group2 = self.create_review_group(name='group2',
                                          local_site=good_site)

        # These should not match.
        self.create_review_group(name='group3')
        self.create_review_group(name='group4', local_site=bad_site)
        self.create_review_group(name='group5',
                                 local_site=good_site,
                                 visible=False)

        self.choice.extra_state['local_site'] = good_site

        self.assertQuerysetEqual(
            self.choice.get_queryset(),
            [group1.pk, group2.pk],
            transform=lambda group: group.pk)

    def test_get_queryset_with_matching(self):
        """Testing ReviewGroupsChoice.get_queryset with matching=True"""
        local_site = LocalSite.objects.create(name='site1')

        # These should match.
        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')
        group3 = self.create_review_group(name='group3',
                                          visible=False)
        group4 = self.create_review_group(name='group4',
                                          invite_only=True)

        # These should not match.
        self.create_review_group(name='group5',
                                 visible=False,
                                 local_site=local_site)

        self.choice.extra_state.update({
            'local_site': None,
            'matching': True,
        })

        self.assertQuerysetEqual(
            self.choice.get_queryset(),
            [group1.pk, group2.pk, group3.pk, group4.pk],
            transform=lambda group: group.pk)

    def test_get_queryset_with_matching_and_local_site(self):
        """Testing ReviewGroupsChoice.get_queryset with matching=True and
        LocalSite
        """
        good_site = LocalSite.objects.create(name='good-site')
        bad_site = LocalSite.objects.create(name='bad-site')

        # These should match.
        group1 = self.create_review_group(name='group1',
                                          local_site=good_site)
        group2 = self.create_review_group(name='group2',
                                          local_site=good_site)
        group3 = self.create_review_group(name='group3',
                                          local_site=good_site,
                                          visible=False)
        group4 = self.create_review_group(name='group4',
                                          local_site=good_site,
                                          invite_only=True)

        # These should not match.
        self.create_review_group(name='group5')
        self.create_review_group(name='group6', local_site=bad_site)

        self.choice.extra_state.update({
            'local_site': good_site,
            'matching': True,
        })

        self.assertQuerysetEqual(
            self.choice.get_queryset(),
            [group1.pk, group2.pk, group3.pk, group4.pk],
            transform=lambda group: group.pk)

    def test_matches_with_any_op(self):
        """Testing ReviewGroupsChoice.matches with "any" operator"""
        self.create_review_group(name='group1', invite_only=False)
        self.create_review_group(name='group2', invite_only=True)

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('any')),
        ])

        self.assertTrue(condition_set.matches(
            review_groups=Group.objects.all()))
        self.assertFalse(condition_set.matches(
            review_groups=Group.objects.none()))

    def test_matches_with_none_op(self):
        """Testing ReviewGroupsChoice.matches with "none" operator"""
        self.create_review_group(name='group1')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('none')),
        ])

        self.assertTrue(condition_set.matches(
            review_groups=Group.objects.none()))
        self.assertFalse(condition_set.matches(
            review_groups=Group.objects.all()))

    def test_matches_with_contains_any_op(self):
        """Testing ReviewGroupsChoice.matches with "contains-any" operator"""
        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')
        group3 = self.create_review_group(name='group3')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('contains-any'),
                      [group1, group2])
        ])

        self.assertTrue(condition_set.matches(
            review_groups=Group.objects.filter(pk=group1.pk)))
        self.assertFalse(condition_set.matches(
            review_groups=Group.objects.filter(pk=group3.pk)))
        self.assertFalse(condition_set.matches(
            review_groups=Group.objects.none()))

    def test_matches_with_does_not_contain_any_op(self):
        """Testing ReviewGroupsChoice.matches with "does-not-contain-any"
        operator
        """
        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')
        group3 = self.create_review_group(name='group3')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-contain-any'),
                      [group1, group2])
        ])

        self.assertFalse(condition_set.matches(
            review_groups=Group.objects.filter(pk=group1.pk)))
        self.assertTrue(condition_set.matches(
            review_groups=Group.objects.filter(pk=group3.pk)))
        self.assertTrue(condition_set.matches(
            review_groups=Group.objects.none()))

    def test_matches_with_any_public_op(self):
        """Testing ReviewGroupsChoice.matches with "any-public" operator"""
        group1 = self.create_review_group(name='group1', invite_only=False)
        group2 = self.create_review_group(name='group2', invite_only=True)

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('any-public')),
        ])

        self.assertTrue(condition_set.matches(
            review_groups=Group.objects.filter(pk=group1.pk)))
        self.assertFalse(condition_set.matches(
            review_groups=Group.objects.filter(pk=group2.pk)))
        self.assertFalse(condition_set.matches(
            review_groups=Group.objects.none()))

    def test_matches_with_all_invite_only_op(self):
        """Testing ReviewGroupsChoice.matches with "all-invite-only" operator
        """
        group1 = self.create_review_group(name='group1', invite_only=True)
        group2 = self.create_review_group(name='group2', invite_only=False)

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('all-invite-only')),
        ])

        self.assertTrue(condition_set.matches(
            review_groups=Group.objects.filter(pk=group1.pk)))
        self.assertFalse(condition_set.matches(
            review_groups=Group.objects.filter(pk=group2.pk)))
        self.assertFalse(condition_set.matches(
            review_groups=Group.objects.none()))


class ReviewRequestAllDiffFilesChoiceTests(TestCase):
    """Unit tests for ReviewRequestAllDiffFilesChoice."""

    fixtures = ['test_scmtools', 'test_users']

    def setUp(self):
        super(ReviewRequestAllDiffFilesChoiceTests, self).setUp()

        self.choice = ReviewRequestAllDiffFilesChoice()
        self.review_request = self.create_review_request(
            create_repository=True,
            publish=True)
        diffset = self.create_diffset(self.review_request)
        self.filediff1 = self.create_filediff(diffset, source_file='file1',
                                              dest_file='file1')
        self.filediff2 = self.create_filediff(diffset, source_file='file2',
                                              dest_file='file2')

    def test_get_match_value(self):
        """Testing ReviewRequestAllDiffFilesChoice.get_match_value"""
        self.assertEqual(self.choice.get_match_value(self.review_request, {}),
                         {'file1', 'file2'})

    def test_matches_with_is_op(self):
        """Testing ReviewRequestAllDiffFilesChoice.matches with "is" operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('is'), 'file1'),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

        self.filediff2.delete()
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_is_not_op(self):
        """Testing ReviewRequestAllDiffFilesChoice.matches with "is-not"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('is-not'),
                      'fileX'),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('is-not'),
                      'file1'),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_contains_op(self):
        """Testing ReviewRequestAllDiffFilesChoice.matches with "contains"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('contains'),
                      'file'),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('contains'),
                      '1'),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_does_not_contain_op(self):
        """Testing ReviewRequestAllDiffFilesChoice.matches with
        "does-not-contain" operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-contain'),
                      '3'),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-contain'),
                      'ile1'),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_starts_with_op(self):
        """Testing ReviewRequestAllDiffFilesChoice.matches with "starts-with"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('starts-with'),
                      'file'),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('starts-with'),
                      'file1'),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_ends_with_op(self):
        """Testing ReviewRequestAllDiffFilesChoice.matches with "ends-with"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('ends-with'),
                      'le1'),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

        self.filediff2.delete()
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_matches_regex_op(self):
        """Testing ReviewRequestAllDiffFilesChoice.matches with "matches-regex"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('matches-regex'),
                      re.compile(r'^[Ff]ile\d$')),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('matches-regex'),
                      re.compile('^[Ff]ile1$')),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_does_not_match_regex_op(self):
        """Testing ReviewRequestAllDiffFilesChoice.matches with
        "does-not-match-regex" operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-match-regex'),
                      re.compile(r'^[Ff]ile3$')),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-match-regex'),
                      re.compile('[Ff]ile1')),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))


class ReviewRequestAnyDiffFileChoiceTests(TestCase):
    """Unit tests for ReviewRequestAnyDiffFileChoice."""

    fixtures = ['test_scmtools', 'test_users']

    def setUp(self):
        super(ReviewRequestAnyDiffFileChoiceTests, self).setUp()

        self.choice = ReviewRequestAnyDiffFileChoice()
        self.review_request = self.create_review_request(
            create_repository=True,
            publish=True)
        diffset = self.create_diffset(self.review_request)
        self.filediff1 = self.create_filediff(diffset, source_file='file1',
                                              dest_file='file1')
        self.filediff2 = self.create_filediff(diffset, source_file='file2',
                                              dest_file='file2')

    def test_get_match_value(self):
        """Testing ReviewRequestAnyDiffFileChoice.get_match_value"""
        self.assertEqual(self.choice.get_match_value(self.review_request, {}),
                         {'file1', 'file2'})

    def test_matches_with_is_op(self):
        """Testing ReviewRequestAnyDiffFileChoice.matches with "is" operator"""
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('is'), 'file2'),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('is'), 'fileX'),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_is_not_op(self):
        """Testing ReviewRequestAnyDiffFileChoice.matches with "is-not"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('is-not'),
                      'fileX'),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('is-not'),
                      'file1'),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        self.filediff2.delete()
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_contains_op(self):
        """Testing ReviewRequestAnyDiffFileChoice.matches with "contains"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('contains'),
                      '1'),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('contains'),
                      '3'),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_does_not_contain_op(self):
        """Testing ReviewRequestAnyDiffFileChoice.matches with
        "does-not-contain" operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-contain'),
                      'xyz'),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-contain'),
                      'file'),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_starts_with_op(self):
        """Testing ReviewRequestAnyDiffFileChoice.matches with "starts-with"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('starts-with'),
                      'file'),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('starts-with'),
                      'ile'),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_ends_with_op(self):
        """Testing ReviewRequestAnyDiffFileChoice.matches with "ends-with"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('ends-with'),
                      'le1'),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('ends-with'),
                      'xyz'),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_matches_regex_op(self):
        """Testing ReviewRequestAnyDiffFileChoice.matches with "matches-regex"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('matches-regex'),
                      re.compile(r'^[Ff]ile1$')),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('matches-regex'),
                      re.compile('^\d')),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))

    def test_matches_with_does_not_match_regex_op(self):
        """Testing ReviewRequestAnyDiffFileChoice.matches with
        "does-not-match-regex" operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-match-regex'),
                      re.compile(r'^\d')),
        ])
        self.assertTrue(condition_set.matches(
            review_request=self.review_request))

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-match-regex'),
                      re.compile('[Ff]ile\d')),
        ])
        self.assertFalse(condition_set.matches(
            review_request=self.review_request))


class ReviewRequestRepositoriesChoiceTests(TestCase):
    """Unit tests for ReviewRequestRepositoriesChoice."""

    fixtures = ['test_scmtools', 'test_users']

    def setUp(self):
        super(ReviewRequestRepositoriesChoiceTests, self).setUp()

        self.choice = ReviewRequestRepositoriesChoice()

    def test_matches_with_any_op(self):
        """Testing ReviewRequestRepositoriesChoice.matches with "any" operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('any')),
        ])

        self.assertTrue(condition_set.matches(
            review_request=self.create_review_request(create_repository=True)))
        self.assertFalse(condition_set.matches(
            review_request=self.create_review_request()))

    def test_matches_with_none_op(self):
        """Testing ReviewRequestRepositoriesChoice.matches with "none" operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('none')),
        ])

        self.assertTrue(condition_set.matches(
            review_request=self.create_review_request()))
        self.assertFalse(condition_set.matches(
            review_request=self.create_review_request(create_repository=True)))

    def test_matches_with_one_of_op(self):
        """Testing ReviewRequestRepositoriesChoice.matches with "one-of"
        operator
        """
        repository1 = self.create_repository(name='repo1')
        repository2 = self.create_repository(name='repo2')
        repository3 = self.create_repository(name='repo3')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('one-of'),
                      [repository1, repository2])
        ])

        self.assertTrue(condition_set.matches(
            review_request=self.create_review_request(repository=repository1)))
        self.assertTrue(condition_set.matches(
            review_request=self.create_review_request(repository=repository2)))
        self.assertFalse(condition_set.matches(
            review_request=self.create_review_request(repository=repository3)))

    def test_matches_with_not_one_of_op(self):
        """Testing ReviewRequestRepositoriesChoice.matches with "not-one-of"
        operator
        """
        repository1 = self.create_repository(name='repo1')
        repository2 = self.create_repository(name='repo2')
        repository3 = self.create_repository(name='repo3')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('not-one-of'),
                      [repository1, repository2])
        ])

        self.assertFalse(condition_set.matches(
            review_request=self.create_review_request(repository=repository1)))
        self.assertFalse(condition_set.matches(
            review_request=self.create_review_request(repository=repository2)))
        self.assertTrue(condition_set.matches(
            review_request=self.create_review_request(repository=repository3)))

    def test_matches_with_is_public_op(self):
        """Testing ReviewRequestRepositoriesChoice.matches with "is-public"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('is-public')),
        ])

        public_repo = self.create_repository(name='repo1', public=True)
        private_repo = self.create_repository(name='repo2', public=False)

        self.assertTrue(condition_set.matches(
            review_request=self.create_review_request(repository=public_repo)))
        self.assertFalse(condition_set.matches(
            review_request=self.create_review_request(
                repository=private_repo)))

    def test_matches_with_is_private_op(self):
        """Testing ReviewRequestRepositoriesChoice.matches with "is-private"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('is-private')),
        ])

        public_repo = self.create_repository(name='repo1', public=True)
        private_repo = self.create_repository(name='repo2', public=False)

        self.assertTrue(condition_set.matches(
            review_request=self.create_review_request(
                repository=private_repo)))
        self.assertFalse(condition_set.matches(
            review_request=self.create_review_request(repository=public_repo)))


class ReviewRequestRepositoryTypeChoiceTests(TestCase):
    """Unit tests for ReviewRequestRepositoryTypeChoice."""

    fixtures = ['test_scmtools', 'test_users']

    def setUp(self):
        super(ReviewRequestRepositoryTypeChoiceTests, self).setUp()

        self.choice = ReviewRequestRepositoryTypeChoice()

    def test_matches_with_one_of_op(self):
        """Testing ReviewRequestRepositoryTypeChoice.matches with "one-of"
        operator
        """
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

        self.assertTrue(condition_set.matches(
            review_request=self.create_review_request(repository=repository1)))
        self.assertTrue(condition_set.matches(
            review_request=self.create_review_request(repository=repository2)))
        self.assertFalse(condition_set.matches(
            review_request=self.create_review_request(repository=repository3)))

    def test_matches_with_not_one_of_op(self):
        """Testing ReviewRequestRepositoryTypeChoice.matches with "not-one-of"
        operator
        """
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

        self.assertFalse(condition_set.matches(
            review_request=self.create_review_request(repository=repository1)))
        self.assertFalse(condition_set.matches(
            review_request=self.create_review_request(repository=repository2)))
        self.assertTrue(condition_set.matches(
            review_request=self.create_review_request(repository=repository3)))


class ReviewRequestReviewGroupsChoiceTests(TestCase):
    """Unit tests for ReviewRequestReviewGroupsChoice."""

    fixtures = ['test_users']

    def setUp(self):
        super(ReviewRequestReviewGroupsChoiceTests, self).setUp()

        self.request = RequestFactory().request()
        self.request.user = User.objects.create(username='test-user')

        self.choice = ReviewRequestReviewGroupsChoice(request=self.request)

    def test_get_queryset(self):
        """Testing ReviewGroupsChoice.get_queryset"""
        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')

        self.assertQuerysetEqual(
            self.choice.get_queryset(),
            [group1.pk, group2.pk],
            transform=lambda group: group.pk)

    def test_get_queryset_with_local_site(self):
        """Testing ReviewGroupsChoice.get_queryset with LocalSite"""
        good_site = LocalSite.objects.create(name='good-site')
        bad_site = LocalSite.objects.create(name='bad-site')

        # These should match.
        group1 = self.create_review_group(name='group1',
                                          local_site=good_site)
        group2 = self.create_review_group(name='group2',
                                          local_site=good_site)

        # These should not match.
        self.create_review_group(name='group3')
        self.create_review_group(name='group4', local_site=bad_site)

        self.choice.extra_state['local_site'] = good_site

        self.assertQuerysetEqual(
            self.choice.get_queryset(),
            [group1.pk, group2.pk],
            transform=lambda group: group.pk)

    def test_matches_with_any_op(self):
        """Testing ReviewRequestReviewGroupsChoice.matches with "any" operator
        """
        group = self.create_review_group(name='group1')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('any')),
        ])

        review_request = self.create_review_request()
        review_request.target_groups = [group]
        self.assertTrue(condition_set.matches(review_request=review_request))

        review_request.target_groups = []
        self.assertFalse(condition_set.matches(review_request=review_request))

    def test_matches_with_none_op(self):
        """Testing ReviewRequestReviewGroupsChoice.matches with "none" operator
        """
        group = self.create_review_group(name='group1')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('none')),
        ])

        review_request = self.create_review_request()
        self.assertTrue(condition_set.matches(review_request=review_request))

        review_request.target_groups = [group]
        self.assertFalse(condition_set.matches(review_request=review_request))

    def test_matches_with_contains_any_op(self):
        """Testing ReviewRequestReviewGroupsChoice.matches with "contains-any"
        operator
        """
        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')
        group3 = self.create_review_group(name='group2')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('contains-any'),
                      [group1, group2]),
        ])

        review_request = self.create_review_request()
        review_request.target_groups = [group2]
        self.assertTrue(condition_set.matches(review_request=review_request))

        review_request.target_groups = [group3]
        self.assertFalse(condition_set.matches(review_request=review_request))

        review_request.target_groups = []
        self.assertFalse(condition_set.matches(review_request=review_request))

    def test_matches_with_does_not_contain_any_op(self):
        """Testing ReviewRequestReviewGroupsChoice.matches with
        "does-not-contain-any" operator
        """
        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')
        group3 = self.create_review_group(name='group3')

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-contain-any'),
                      [group1, group2])
        ])

        review_request = self.create_review_request()
        self.assertTrue(condition_set.matches(review_request=review_request))

        review_request.target_groups = [group3]
        self.assertTrue(condition_set.matches(review_request=review_request))

        review_request.target_groups = [group1]
        self.assertFalse(condition_set.matches(review_request=review_request))

    def test_matches_with_any_public_op(self):
        """Testing ReviewRequestReviewGroupsChoice.matches with "any-public"
        operator"""
        group1 = self.create_review_group(name='group1', invite_only=False)
        group2 = self.create_review_group(name='group2', invite_only=True)

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice, self.choice.get_operator('any-public')),
        ])

        review_request = self.create_review_request()
        review_request.target_groups = [group1]
        self.assertTrue(condition_set.matches(review_request=review_request))

        review_request.target_groups = [group2]
        self.assertFalse(condition_set.matches(review_request=review_request))

        review_request.target_groups = []
        self.assertFalse(condition_set.matches(review_request=review_request))

    def test_matches_with_all_invite_only_op(self):
        """Testing ReviewRequestReviewGroupsChoice.matches with
        "all-invite-only" operator
        """
        group1 = self.create_review_group(name='group1', invite_only=True)
        group2 = self.create_review_group(name='group2', invite_only=False)

        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('all-invite-only')),
        ])

        review_request = self.create_review_request()
        review_request.target_groups = [group1]
        self.assertTrue(condition_set.matches(review_request=review_request))

        review_request.target_groups = [group2]
        self.assertFalse(condition_set.matches(review_request=review_request))

        review_request.target_groups = []
        self.assertFalse(condition_set.matches(review_request=review_request))


class ReviewRequestOwnerChoiceTests(TestCase):
    """Unit tests for ReviewRequestOwnerChoice."""

    fixtures = ['test_users']

    def setUp(self):
        super(ReviewRequestOwnerChoiceTests, self).setUp()

        self.choice = ReviewRequestOwnerChoice()
        self.user1 = User.objects.get(username='doc')
        self.user2 = User.objects.get(username='grumpy')
        self.user3 = User.objects.get(username='dopey')

    def test_get_queryset(self):
        """Testing ReviewRequestOwnerChoice.get_queryset"""
        self.assertQuerysetEqual(
            self.choice.get_queryset(),
            User.objects.values_list('pk', flat=True),
            transform=lambda user: user.pk)

    def test_get_queryset_with_local_site(self):
        """Testing ReviewRequestOwnerChoice.get_queryset with LocalSite"""
        good_site = LocalSite.objects.create(name='good-site')
        good_site.users.add(self.user2)

        bad_site = LocalSite.objects.create(name='bad-site')
        bad_site.users.add(self.user3)

        self.choice.extra_state['local_site'] = good_site

        self.assertQuerysetEqual(
            self.choice.get_queryset(),
            [self.user2.pk],
            transform=lambda user: user.pk)

    def test_matches_with_one_of_op(self):
        """Testing ReviewRequestOwnerChoice.matches with "one-of"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('one-of'),
                      [self.user1, self.user2]),
        ])

        self.assertTrue(condition_set.matches(
            review_request=self.create_review_request(submitter=self.user1)))
        self.assertTrue(condition_set.matches(
            review_request=self.create_review_request(submitter=self.user2)))
        self.assertFalse(condition_set.matches(
            review_request=self.create_review_request(submitter=self.user3)))

    def test_matches_with_not_one_of_op(self):
        """Testing ReviewRequestOwnerChoice.matches with "not-one-of"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('not-one-of'),
                      [self.user1, self.user2]),
        ])

        self.assertFalse(condition_set.matches(
            review_request=self.create_review_request(submitter=self.user1)))
        self.assertFalse(condition_set.matches(
            review_request=self.create_review_request(submitter=self.user2)))
        self.assertTrue(condition_set.matches(
            review_request=self.create_review_request(submitter=self.user3)))


class ReviewRequestReviewerChoiceTests(TestCase):
    """Unit tests for ReviewRequestReviewerChoice."""

    fixtures = ['test_users']

    def setUp(self):
        super(ReviewRequestReviewerChoiceTests, self).setUp()

        self.choice = ReviewRequestReviewerChoice()
        self.user1 = User.objects.get(username='doc')
        self.user2 = User.objects.get(username='grumpy')
        self.user3 = User.objects.get(username='dopey')

    def test_get_queryset(self):
        """Testing ReviewRequestReviewerChoice.get_queryset"""
        self.assertQuerysetEqual(
            self.choice.get_queryset(),
            User.objects.values_list('pk', flat=True),
            transform=lambda user: user.pk)

    def test_get_queryset_with_local_site(self):
        """Testing ReviewRequestReviewerChoice.get_queryset with LocalSite"""
        good_site = LocalSite.objects.create(name='good-site')
        good_site.users.add(self.user2)

        bad_site = LocalSite.objects.create(name='bad-site')
        bad_site.users.add(self.user3)

        self.choice.extra_state['local_site'] = good_site

        self.assertQuerysetEqual(
            self.choice.get_queryset(),
            [self.user2.pk],
            transform=lambda user: user.pk)

    def test_matches_with_contains_any_op(self):
        """Testing ReviewRequestReviewerChoice.matches with
        "contains-any" operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('contains-any'),
                      [self.user1, self.user2]),
        ])

        review_request = self.create_review_request(target_people=[self.user1])
        self.assertTrue(condition_set.matches(review_request=review_request))

        review_request = self.create_review_request(target_people=[self.user2])
        self.assertTrue(condition_set.matches(review_request=review_request))

        review_request = self.create_review_request(target_people=[self.user3])
        self.assertFalse(condition_set.matches(review_request=review_request))

    def test_matches_with_does_not_contain_any_op(self):
        """Testing ReviewRequestReviewerChoice.matches with
        "does-not-contain-any" operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-contain-any'),
                      [self.user1, self.user2]),
        ])

        review_request = self.create_review_request(target_people=[self.user1])
        self.assertFalse(condition_set.matches(review_request=review_request))

        review_request = self.create_review_request(target_people=[self.user2])
        self.assertFalse(condition_set.matches(review_request=review_request))

        review_request = self.create_review_request(target_people=[self.user3])
        self.assertTrue(condition_set.matches(review_request=review_request))


class ReviewRequestParticipantChoiceTests(TestCase):
    """Unit tests for ReviewRequestParticipantChoice."""

    fixtures = ['test_users']

    def setUp(self):
        super(ReviewRequestParticipantChoiceTests, self).setUp()

        self.choice = ReviewRequestParticipantChoice()
        self.user1 = User.objects.get(username='doc')
        self.user2 = User.objects.get(username='grumpy')
        self.user3 = User.objects.get(username='dopey')

    def test_get_queryset(self):
        """Testing ReviewRequestParticipantChoice.get_queryset"""
        self.assertQuerysetEqual(
            self.choice.get_queryset(),
            User.objects.values_list('pk', flat=True),
            transform=lambda user: user.pk)

    def test_get_queryset_with_local_site(self):
        """Testing ReviewRequestParticipantChoice.get_queryset with
        LocalSite
        """
        good_site = LocalSite.objects.create(name='good-site')
        good_site.users.add(self.user2)

        bad_site = LocalSite.objects.create(name='bad-site')
        bad_site.users.add(self.user3)

        self.choice.extra_state['local_site'] = good_site

        self.assertQuerysetEqual(
            self.choice.get_queryset(),
            [self.user2.pk],
            transform=lambda user: user.pk)

    def test_matches_with_contains_any_op(self):
        """Testing ReviewRequestParticipantChoice.matches with "contains-any"
        operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('contains-any'),
                      [self.user1, self.user2]),
        ])

        review_request = self.create_review_request()
        self.assertFalse(condition_set.matches(review_request=review_request))

        review_request = self.create_review_request()
        self.create_review(review_request,
                           user=self.user1,
                           public=True)
        self.assertTrue(condition_set.matches(review_request=review_request))

    def test_matches_with_does_not_contain_any_op(self):
        """Testing ReviewRequestParticipantChoice.matches with
        "does-not-contain-any" operator
        """
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(self.choice,
                      self.choice.get_operator('does-not-contain-any'),
                      [self.user1, self.user2]),
        ])

        review_request = self.create_review_request()
        self.assertTrue(condition_set.matches(review_request=review_request))

        review_request = self.create_review_request()
        self.create_review(review_request,
                           user=self.user1,
                           public=True)
        self.assertFalse(condition_set.matches(review_request=review_request))
