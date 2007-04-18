from django.db.models import Q
from reviewboard.reviews.models import ReviewRequest, Review

def _review_request_list(user, status, extra_query=None):
    query = Q(public=True) | Q(submitter=user)

    if status != None:
        query = query & Q(status=status)

    if extra_query != None:
        query = query & extra_query

    return ReviewRequest.objects.filter(query)


def all_review_requests(user, status=None):
    return _review_request_list(user, status)

def review_requests_to_group(user, group_name, status=None):
    return _review_request_list(user, status,
                                Q(target_groups__name=group_name))

def review_requests_to_user(user, username, status=None):
    return _review_request_list(user, status,
                                Q(target_people__username=username))

def review_requests_from_user(user, username, status=None):
    return _review_request_list(user, status, Q(submitter__username=username))
