from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.db.models.query import QuerySet

from djblets.util.db import ConcurrencyManager

from reviewboard.diffviewer.models import DiffSetHistory
from reviewboard.scmtools.errors import ChangeNumberInUseError


class ReviewRequestQuerySet(QuerySet):
    def with_counts(self, user):
        queryset = self

        if user and user.is_authenticated():
            select_dict = {}

            select_dict['new_review_count'] = """
                SELECT COUNT(*)
                  FROM reviews_review, accounts_reviewrequestvisit
                  WHERE reviews_review.public
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.user_id = %(user_id)s
                    AND reviews_review.timestamp >
                        accounts_reviewrequestvisit.timestamp
                    AND reviews_review.user_id != %(user_id)s
            """ % {
                'user_id': str(user.id)
            }

            queryset = self.extra(select=select_dict)

        return queryset


class ReviewRequestManager(ConcurrencyManager):
    """
    A manager for review requests. Provides specialized queries to retrieve
    review requests with specific targets or origins, and to create review
    requests based on certain data.
    """

    def create(self, user, repository, changenum=None):
        """
        Creates a new review request, optionally filling in fields based off
        a change number.
        """
        if changenum:
            try:
                review_request = self.get(changenum=changenum,
                                          repository=repository)
                raise ChangeNumberInUseError(review_request)
            except ObjectDoesNotExist:
                pass

        diffset_history = DiffSetHistory()
        diffset_history.save()

        review_request = super(ReviewRequestManager, self).create(
            submitter=user,
            status='P',
            public=False,
            repository=repository,
            diffset_history=diffset_history)

        if changenum:
            review_request.update_from_changenum(changenum)
            review_request.save()

        return review_request

    def public(self, *args, **kwargs):
        return self._query(*args, **kwargs)

    def to_group(self, group_name, *args, **kwargs):
        return self._query(extra_query=Q(target_groups__name=group_name),
                           *args, **kwargs)

    def to_user_groups(self, username, *args, **kwargs):
        return self._query(
            extra_query=Q(target_groups__users__username=username),
            *args, **kwargs)

    def to_user_directly(self, username, *args, **kwargs):
        query_user = User.objects.get(username=username)
        query = Q(starred_by__user=query_user) | Q(target_people=query_user)
        return self._query(extra_query=query, *args, **kwargs)

    def to_user(self, username, *args, **kwargs):
        query_user = User.objects.get(username=username)
        query = Q(starred_by__user=query_user) | \
                Q(target_people=query_user) | \
                Q(target_groups__users=query_user)
        return self._query(extra_query=query, *args, **kwargs)

    def from_user(self, username, *args, **kwargs):
        return self._query(extra_query=Q(submitter__username=username),
                           *args, **kwargs)

    def _query(self, user=None, status='P', with_counts=False,
               extra_query=None):
        query = Q(public=True)

        if user and user.is_authenticated():
            query = query | Q(submitter=user)

        if status:
            query = query & Q(status=status)

        if extra_query:
            query = query & extra_query

        query = self.filter(query).distinct()

        if with_counts:
            query = query.with_counts(user)

        return query

    def get_query_set(self):
        return ReviewRequestQuerySet(self.model)
