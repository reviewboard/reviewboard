from django.db.models import Q
from reviewboard.reviews.models import ReviewRequest, Review

def _get_review_request_list(user, status, extra_query=None):
    query = (Q(public=True) | Q(submitter=user))

    if status != None:
        query = query & Q(status=status)

    if extra_query != None:
        query = extra_query & query

    return ReviewRequest.objects.filter(query).distinct()


def get_all_review_requests(user=None, status='P'):
    return _get_review_request_list(user, status)

def get_review_requests_to_group(group_name, user=None, status='P'):
    return _get_review_request_list(user, status,
                                    Q(target_groups__name=group_name))

def get_review_requests_to_user_groups(username, user=None, status='P'):
    return _get_review_request_list(user, status,
                                    Q(target_groups__users__username=username))

def get_review_requests_to_user_directly(username, user=None, status='P'):
    return _get_review_request_list(user, status,
                                    Q(target_people__username=username))

def get_review_requests_to_user(username, user=None, status='P'):
    return _get_review_request_list(user, status,
                                    Q(target_people__username=username) |
                                    Q(target_groups__users__username=username))

def get_review_requests_from_user(username, user=None, status='P'):
    return _get_review_request_list(user, status,
                                    Q(submitter__username=username))
