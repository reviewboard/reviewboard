"""Forms for searching Review Board."""

from __future__ import unicode_literals

from collections import OrderedDict

from django import forms
from django.contrib.auth.models import User
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from haystack.forms import ModelSearchForm
from haystack.inputs import Raw
from haystack.query import SQ

from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.scmtools.models import Repository
from reviewboard.search.indexes import BaseSearchIndex


class RBSearchForm(ModelSearchForm):
    """The Review Board search form.

    This form is capable of searching for :py:class:`ReviewRequests
    <reviewboard.reviews.models.review_request.ReviewRequest>` and
    :py:class:`Users <django.contrib.auth.models.User>`.
    """

    FILTER_ALL = ''
    FILTER_REVIEW_REQUESTS = 'reviewrequests'
    FILTER_USERS = 'users'

    #: Available model filters.
    FILTER_TYPES = OrderedDict([
        (FILTER_ALL, {
            'models': [ReviewRequest, User],
            'name': _('All results'),
        }),
        (FILTER_REVIEW_REQUESTS, {
            'models': [ReviewRequest],
            'name': _('Review Requests'),
        }),
        (FILTER_USERS, {
            'models': [User],
            'name': _('Users'),
        }),
    ])

    model_filter = forms.MultipleChoiceField(
        choices=(
            (filter_id, filter_type['name'])
            for filter_id, filter_type in six.iteritems(FILTER_TYPES)
        ),
        required=False,
    )

    id = forms.IntegerField(required=False)

    def __init__(self, user=None, local_site=None, **kwargs):
        """Initialize the search form.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the search.

                Results will be limited to those visible to the user.

            local_site (reviewboard.site.models.LocalSite):
                The Local Site the search is being performed on.

                Results will be limited to those on the LocalSite.

            **kwargs (dict):
                Additional keyword arguments to forward to the parent form.
        """
        super(RBSearchForm, self).__init__(**kwargs)

        self.user = user
        self.local_site = local_site

    def clean_q(self):
        """Clean the ``q`` field.

        The field will be stripped of leading and trailing whitespace.

        Returns:
            unicode:
            The stripped query.
        """
        return self.cleaned_data['q'].strip()

    def clean_model_filter(self):
        """Clean the ``model_filter`` field.

        If no filter is provided, the default (all models) will be used.

        Returns:
            list of unicode:
            The cleaned ``filter`` field.
        """
        return self.cleaned_data['model_filter'] or ['']

    def search(self):
        """Perform a search.

        Returns:
            haystack.query.SearchQuerySet:
            The search results.
        """
        if not self.is_valid():
            return self.no_query_found()

        user = self.user
        q = self.cleaned_data['q']
        id_q = self.cleaned_data.get('id')
        model_filters = set()

        for filter_type in self.cleaned_data.get('model_filter', ['']):
            model_filters.update(self.FILTER_TYPES[filter_type]['models'])

        model_filters = list(model_filters)

        sqs = (
            self.searchqueryset
            .filter(content=Raw(q))
            .models(*model_filters)
        )

        if id_q:
            sqs = sqs.filter_or(SQ(id=q))

        if self.local_site:
            local_site_id = self.local_site.pk
        else:
            local_site_id = BaseSearchIndex.NO_LOCAL_SITE_ID

        sqs = sqs.filter_and(local_sites__contains=local_site_id)

        # Filter out any private review requests the user doesn't have
        # access to.
        if not user.is_superuser:
            private_sq = (SQ(django_ct='reviews.reviewrequest') &
                          SQ(private=True))

            if user.is_authenticated():
                # We're going to build a series of queries that mimic the
                # accessibility checks we have internally, based on the access
                # permissions the user currently has, and the IDs listed in
                # the indexed review request.
                #
                # This must always be kept in sync with
                # ReviewRequestManager._query.
                #
                # Note that we are not performing Local Site checks here,
                # because we're already filtering by Local Sites.

                # Make sure they have access to the repository, if any.
                accessible_repo_ids = list(Repository.objects.accessible_ids(
                    user,
                    visible_only=False,
                    local_site=self.local_site,
                ))

                accessible_group_ids = Group.objects.accessible_ids(
                    user,
                    visible_only=False,
                )

                repository_sq = SQ(
                    private_repository_id__in=[0] + accessible_repo_ids
                )

                # Next, build a query to see if the review request targets any
                # invite-only groups the user is a member of.
                target_groups_sq = SQ(private_target_groups__contains=0)

                for pk in accessible_group_ids:
                    target_groups_sq |= SQ(private_target_groups__contains=pk)

                # Build a query to see if the user is explicitly listed
                # in the list of reviewers.
                target_users_sq = SQ(target_users__contains=user.pk)

                # And, of course, the owner of the review request can see it.
                #
                # With that, we'll put the whole query together, in the order
                # matching ReviewRequest.is_accessible_by.
                private_sq &= ~(SQ(username=user.username) |
                                (repository_sq &
                                 (target_users_sq | target_groups_sq)))

            sqs = sqs.exclude(private_sq)

        return sqs.order_by('-last_updated')
