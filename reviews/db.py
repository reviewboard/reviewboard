from django.db.models import Q

from reviewboard.diffviewer.models import DiffSetHistory
from reviewboard.reviews.models import ReviewRequest, Review
from reviewboard import scmtools

def _get_review_request_list(user, status, extra_query=None):
    if user:
        query = Q(public=True) | Q(submitter=user)
    else:
        query = Q(public=True)

    if status != None:
        query = query & Q(status=status)

    if extra_query:
        query = query & extra_query

    review_requests = ReviewRequest.objects.filter(query).distinct()

    return review_requests


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


class InvalidChangeNumberException(Exception):
    def __init__(self):
        Exception.__init__(self, None)
        self.review_request = review_request


class ChangeNumberInUseException(Exception):
    def __init__(self, review_request=None):
        Exception.__init__(self, None)
        self.review_request = review_request


def update_review_request_from_changenum(review_request, changenum):
    changeset = scmtools.get_tool().get_changeset(changenum)

    if not changeset:
        raise InvalidChangeNumberException()

    review_request.changenum = changenum
    review_request.summary = changeset.summary
    review_request.description = changeset.description
    review_request.testing_done = changeset.testing_done
    review_request.branch = changeset.branch
    review_request.bugs_closed = ','.join(changeset.bugs_closed)


def create_review_request(user, changenum=None):
    try:
        review_request = ReviewRequest.objects.get(changenum=changenum)
        raise ChangeNumberInUseException(review_request)
    except ReviewRequest.DoesNotExist:
        pass

    review_request = ReviewRequest()

    if changenum:
        update_review_request_from_changenum(review_request, changenum)

    diffset_history = DiffSetHistory()
    diffset_history.save()

    review_request.diffset_history = diffset_history
    review_request.submitter = user
    review_request.status = 'P'
    review_request.public = False
    review_request.save()

    return review_request
