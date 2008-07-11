from django.contrib.auth.models import User
from django.db.models import Q

from djblets.util.db import ConcurrencyManager

from reviewboard.diffviewer.models import DiffSetHistory
from reviewboard.reviews.errors import ChangeNumberInUseError


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

    def public(self, user=None, status='P'):
        return self._query(user, status)

    def to_group(self, group_name, user=None, status='P'):
        return self._query(user, status, Q(target_groups__name=group_name))

    def to_user_groups(self, username, user=None, status='P'):
        return self._query(user, status,
                           Q(target_groups__users__username=username))

    def to_user_directly(self, username, user=None, status='P'):
        query_user = User.objects.get(username=username)
        query = Q(target_people=query_user) | Q(starred_by__user=query_user)
        return self._query(user, status, query)

    def to_user(self, username, user=None, status='P'):
        query_user = User.objects.get(username=username)
        query = Q(target_groups__users=query_user) | \
                Q(target_people=query_user) | \
                Q(starred_by__user=query_user)
        return self._query(user, status, query)

    def from_user(self, username, user=None, status='P'):
        return self._query(user, status, Q(submitter__username=username))

    def _query(self, user, status, extra_query=None):
        query = Q(public=True)

        if user and user.is_authenticated():
            query = query | Q(submitter=user)

        if status:
            query = query & Q(status=status)

        if extra_query:
            query = query & extra_query

        return self.filter(query).distinct()



