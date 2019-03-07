"""Condition choices and operators for review requests and related objects."""

from __future__ import unicode_literals

from itertools import chain

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from djblets.conditions.choices import (BaseConditionStringChoice,
                                        BaseConditionModelMultipleChoice,
                                        ConditionChoiceMatchListItemsMixin,
                                        ConditionChoices)
from djblets.conditions.operators import (AnyOperator,
                                          BaseConditionOperator,
                                          ConditionOperators,
                                          ContainsAnyOperator,
                                          DoesNotContainAnyOperator,
                                          IsNotOneOfOperator,
                                          IsOneOfOperator,
                                          UnsetOperator)

from reviewboard.reviews.models import Group
from reviewboard.scmtools.conditions import (RepositoriesChoice,
                                             RepositoryTypeChoice)
from reviewboard.site.conditions import LocalSiteModelChoiceMixin


class ReviewRequestConditionChoiceMixin(object):
    """Mixin for condition choices that operate off review requests.

    This will set state needed to match against the choice.
    """

    value_kwarg = 'review_request'


class AnyReviewGroupsPublicOperator(BaseConditionOperator):
    """An operator for matching against any public review groups."""

    operator_id = 'any-public'
    name = _('Are any public')
    value_field = None

    def matches(self, match_value, **kwargs):
        """Return whether any review groups are public.

        Args:
            match_value (list of reviewboard.reviews.models.group.Group):
                The review groups to match.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            bool:
            ``True`` if any review groups are public. ``False`` if all are
            invite-only or the list is empty.
        """
        return match_value and any(
            not group.invite_only
            for group in match_value
        )


class AllReviewGroupsInviteOnlyOperator(BaseConditionOperator):
    """An operator for matching against all invite-only review groups."""

    operator_id = 'all-invite-only'
    name = _('Are all invite-only')
    value_field = None

    def matches(self, match_value, **kwargs):
        """Return whether all review groups in the list are invite-only.

        Args:
            match_value (list of reviewboard.reviews.models.group.Group):
                The review groups to match.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            bool:
            ``True`` if all review group in the list are invite-only.
            ``False`` if any are public, or the list is empty.
        """
        return match_value and all(
            group.invite_only
            for group in match_value
        )


class ReviewGroupsChoice(BaseConditionModelMultipleChoice):
    """A condition choice for matching review groups.

    This is used to match a :py:class:`~reviewboard.reviews.models.group.Group`
    against a list of groups, against no group (empty list), or against a
    group's public/invite-only state.
    """

    choice_id = 'review-groups'
    name = _('Review groups')
    value_kwarg = 'review_groups'

    operators = ConditionOperators([
        AnyOperator.with_overrides(name=_('Any review groups')),
        UnsetOperator.with_overrides(name=_('No review groups')),
        ContainsAnyOperator,
        DoesNotContainAnyOperator,
        AnyReviewGroupsPublicOperator,
        AllReviewGroupsInviteOnlyOperator,
    ])

    def get_queryset(self):
        """Return the queryset used to look up review group choices.

        Returns:
            django.db.models.query.QuerySet:
            The queryset for review groups.
        """
        if self.extra_state.get('matching'):
            return (
                Group.objects
                .filter(local_site=self.extra_state['local_site'])
            )
        else:
            request = self.extra_state.get('request')
            assert request is not None

            if 'local_site' in self.extra_state:
                local_site = self.extra_state['local_site']
                show_all_local_sites = False
            else:
                local_site = None
                show_all_local_sites = True

            return Group.objects.accessible(
                user=request.user,
                local_site=local_site,
                show_all_local_sites=show_all_local_sites)

    def get_match_value(self, review_groups, value_state_cache, **kwargs):
        """Return the review groups used for matching.

        Args:
            review_groups (django.db.models.query.QuerySet):
                The provided queryset for review groups.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            list of reviewboard.reviews.models.group.Group:
            The list of review groups.
        """
        try:
            result = value_state_cache['review_groups']
        except KeyError:
            result = list(review_groups.all())
            value_state_cache['review_groups'] = result

        return result


class ReviewRequestBranchChoice(ReviewRequestConditionChoiceMixin,
                                BaseConditionStringChoice):
    """A condition choice for matching a review request's branch."""

    choice_id = 'branch'
    name = _('Branch')

    def get_match_value(self, review_request, **kwargs):
        """Return the branch text used for matching.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The provided review request.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            unicode:
            The review request's branch text.
        """
        return review_request.branch


class ReviewRequestDescriptionChoice(ReviewRequestConditionChoiceMixin,
                                     BaseConditionStringChoice):
    """A condition choice for matching a review request's description."""

    choice_id = 'description'
    name = _('Description')

    def get_match_value(self, review_request, **kwargs):
        """Return the description text used for matching.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The provided review request.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            unicode:
            The review request's description text.
        """
        return review_request.description


class BaseReviewRequestDiffFileChoice(ReviewRequestConditionChoiceMixin,
                                      ConditionChoiceMatchListItemsMixin,
                                      BaseConditionStringChoice):
    """A condition choice for matching affected diff files on a review request.

    This matches against a list of file paths that were added/modified/deleted
    on the latest diffset of a review request.
    """

    def get_match_value(self, review_request, value_state_cache, **kwargs):
        """Return the list of filenames used for matching.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The provided review request.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            set of unicode:
            The set of filenames.
        """
        try:
            result = value_state_cache['diff_filenames']
        except KeyError:
            try:
                diffset = value_state_cache['latest_diffset']
            except KeyError:
                diffset = review_request.get_latest_diffset()
                value_state_cache['latest_diffset'] = diffset

            result = set(chain.from_iterable(
                diffset.files.values_list('source_file', 'dest_file')))
            value_state_cache['diff_filenames'] = result

        return result


class ReviewRequestAnyDiffFileChoice(BaseReviewRequestDiffFileChoice):
    choice_id = 'any_diffed_file'
    name = _('Any diffed file')
    require_match_all_items = False


class ReviewRequestAllDiffFilesChoice(BaseReviewRequestDiffFileChoice):
    choice_id = 'all_diffed_files'
    name = _('All diffed file')
    require_match_all_items = True


class ReviewRequestOwnerChoice(LocalSiteModelChoiceMixin,
                               ReviewRequestConditionChoiceMixin,
                               BaseConditionModelMultipleChoice):
    """A condition choice for matching a review request's owner."""

    queryset = User.objects.all()
    choice_id = 'owner'
    name = _('Owner')

    operators = ConditionOperators([
        IsOneOfOperator,
        IsNotOneOfOperator,
    ])

    def get_match_value(self, review_request, **kwargs):
        """Return the owner used for matching.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The provided review request.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            django.contrib.auth.models.User:
            The review request's owner.
        """
        return review_request.owner


class ReviewRequestReviewerChoice(LocalSiteModelChoiceMixin,
                                  ReviewRequestConditionChoiceMixin,
                                  BaseConditionModelMultipleChoice):
    """A condition choice for matching a review request's reviewer."""

    queryset = User.objects.all()
    choice_id = 'reviewer'
    name = _('Reviewer')

    operators = ConditionOperators([
        ContainsAnyOperator,
        DoesNotContainAnyOperator,
    ])

    def get_match_value(self, review_request, **kwargs):
        """Return the reviewers used for matching.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The provided review request.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            list of django.contrib.auth.models.User:
            List of the review request's reviewers.
        """
        return list(review_request.target_people.all())


class ReviewRequestParticipantChoice(LocalSiteModelChoiceMixin,
                                     ReviewRequestConditionChoiceMixin,
                                     BaseConditionModelMultipleChoice):
    """A condition choice for matching a review request's participant."""

    queryset = User.objects.all()
    choice_id = 'participant'
    name = _('Participant')

    operators = ConditionOperators([
        ContainsAnyOperator,
        DoesNotContainAnyOperator,
    ])

    def get_match_value(self, review_request, **kwargs):
        """Return the participants used for matching.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The provided review request.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            set of django.contrib.auth.models.User:
            The review request's participants.
        """
        return review_request.review_participants


class ReviewRequestSummaryChoice(ReviewRequestConditionChoiceMixin,
                                 BaseConditionStringChoice):
    """A condition choice for matching a review request's summary."""

    choice_id = 'summary'
    name = _('Summary')

    def get_match_value(self, review_request, **kwargs):
        """Return the summary text used for matching.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The provided review request.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            unicode:
            The review request's summary text.
        """
        return review_request.summary


class ReviewRequestTestingDoneChoice(BaseConditionStringChoice):
    """A condition choice for matching a review request's Testing Done field.
    """

    choice_id = 'testing-done'
    name = _('Testing Done')

    def get_match_value(self, review_request, **kwargs):
        """Return the testing done text used for matching.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The provided review request.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            unicode:
            The review request's testing done text.
        """
        return review_request.testing_done


class ReviewRequestRepositoriesChoice(ReviewRequestConditionChoiceMixin,
                                      RepositoriesChoice):
    """A condition choice for matching a review request's repositories."""

    def get_match_value(self, review_request, **kwargs):
        """Return the repository used for matching.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The provided review request.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            reviewboard.scmtools.models.Repository:
            The review request's repository.
        """
        return review_request.repository


class ReviewRequestRepositoryTypeChoice(ReviewRequestConditionChoiceMixin,
                                        RepositoryTypeChoice):
    """A condition choice for matching a review request's repository types."""

    def get_match_value(self, review_request, **kwargs):
        """Return the repository used for matching.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The provided review request.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            reviewboard.scmtools.models.Repository:
            The review request's repository.
        """
        return super(ReviewRequestRepositoryTypeChoice, self).get_match_value(
            repository=review_request.repository)


class ReviewRequestReviewGroupsChoice(ReviewRequestConditionChoiceMixin,
                                      ReviewGroupsChoice):
    """A condition choice for matching a review request's review groups."""

    def get_match_value(self, review_request, **kwargs):
        """Return the review groups used for matching.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The provided review request.

            **kwargs (dict):
                Extra keyword arguments.

        Returns:
            django.db.models.query.QuerySet:
            The queryset for a review request's target review groups.
        """
        return super(ReviewRequestReviewGroupsChoice, self).get_match_value(
            review_groups=review_request.target_groups,
            **kwargs)


class ReviewRequestConditionChoices(ConditionChoices):
    """A standard set of review request condition choices.

    This provides a handful of condition choices that are useful for
    review requests. They can be used in integrations or any other place
    where conditions are used.
    """

    choice_classes = [
        ReviewRequestBranchChoice,
        ReviewRequestDescriptionChoice,
        ReviewRequestRepositoriesChoice,
        ReviewRequestRepositoryTypeChoice,
        ReviewRequestReviewGroupsChoice,
        ReviewRequestOwnerChoice,
        ReviewRequestReviewerChoice,
        ReviewRequestParticipantChoice,
        ReviewRequestSummaryChoice,
        ReviewRequestTestingDoneChoice,
    ]
