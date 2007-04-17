from django.db.models import Q
from django.http import HttpResponse
from django.template.defaultfilters import timesince
from django.utils import simplejson

from reviewboard.reviews.models import ReviewRequest, Review
from reviewboard.utils import JsonResponse


def serialize_status(status):
    if status == "P":
        return "pending"
    elif status == "S":
        return "submitted"
    elif status == "D":
        return "discarded"
    else:
        raise "Invalid status '%s'" % status


def deserialize_status(status):
    if status == "pending":
        return "P"
    elif status == "submitted":
        return "S"
    elif status == "discarded":
        return "D"
    else:
        raise "Invalid status '%s'" % status


def serialize_user(user):
    return {
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
    }


def serialize_group(group):
    return {
        'id': group.id,
        'name': group.name,
        'mailing_list': group.mailing_list,
    }


def serialize_review_request(review_request):
    return {
        'id': review_request.id,
        'submitter': serialize_user(review_request.submitter),
        'time_added': review_request.time_added,
        'time_added_relative': timesince(review_request.time_added),
        'last_updated': review_request.last_updated,
        'last_updated_relative': timesince(review_request.last_updated),
        'status': serialize_status(review_request.status),
        'public': review_request.public,
        'changenum': review_request.changenum,
        'summary': review_request.summary,
        'description': review_request.description,
        'testing_done': review_request.testing_done,
        'bugs_closed': [int(bug)
                        for bug in review_request.bugs_closed.split(",")],
        'branch': review_request.branch,
        'target_groups': [serialize_group(g)
                          for g in review_request.target_groups.all()],
        'target_people': [serialize_user(u)
                          for u in review_request.target_people.all()],
    }


def json_review_request_list(request, extra_query=None):
    status = request.GET.get('status', 'pending')

    query = Q(public=True) | Q(submitter=request.user)

    if status != "all":
        query = query & Q(status=deserialize_status(status))

    if extra_query != None:
        query = query & extra_query

    review_requests = ReviewRequest.objects.filter(query)
    return JsonResponse({
        'review_requests': [serialize_review_request(r)
                            for r in review_requests]
    })


def all_review_requests(request):
    return json_review_request_list(request)


def review_requests_to_group(request, name):
    return json_review_request_list(request,
                                    Q(target_groups__name=name))


def review_requests_to_user(request, username):
    return json_review_request_list(request,
                                    Q(target_people__username=username))


def review_requests_from_user(request, username):
    return json_review_request_list(request,
                                    Q(submitter__username=username))
