from django.contrib.auth.models import User
from django.core.serializers import serialize
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.db.models import Q
from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.template.defaultfilters import timesince
from django.utils import simplejson

from reviewboard.reviews.models import ReviewRequest, Review, Group


class ReviewBoardJSONEncoder(DateTimeAwareJSONEncoder):
    def default(self, o):
        if isinstance(o, QuerySet):
            return list(o)
        elif isinstance(o, User):
            return {
                'id': o.id,
                'username': o.username,
                'first_name': o.first_name,
                'last_name': o.last_name,
                'email': o.email,
            }
        elif isinstance(o, Group):
            return {
                'id': o.id,
                'name': o.name,
                'mailing_list': o.mailing_list,
            }
        elif isinstance(o, ReviewRequest):
            return {
                'id': o.id,
                'submitter': o.submitter,
                'time_added': o.time_added,
                'last_updated': o.last_updated,
                'status': status_to_string(o.status),
                'public': o.public,
                'changenum': o.changenum,
                'summary': o.summary,
                'description': o.description,
                'testing_done': o.testing_done,
                'bugs_closed': [int(bug) for bug in o.bugs_closed.split(",")],
                'branch': o.branch,
                'target_groups': o.target_groups.all(),
                'target_people': o.target_people.all(),
            }
        else:
            return super(ReviewBoardJSONEncoder, self).default(o)


class JsonResponse(HttpResponse):
    def __init__(self, request, obj):
        json = obj
        json['stat'] = 'ok'
        content = simplejson.dumps(json, cls=ReviewBoardJSONEncoder)

        callback = request.GET.get('callback', None)

        if callback != None:
            content = callback + "(" + content + ");"

        super(JsonResponse, self).__init__(content, mimetype='text/plain')
        #super(JsonResponse, self).__init__(content, mimetype='application/json')

def status_to_string(status):
    if status == "P":
        return "pending"
    elif status == "S":
        return "submitted"
    elif status == "D":
        return "discarded"
    elif status == None:
        return "all"
    else:
        raise "Invalid status '%s'" % status


def string_to_status(status):
    if status == "pending":
        return "P"
    elif status == "submitted":
        return "S"
    elif status == "discarded":
        return "D"
    elif status == "all":
        return None
    else:
        raise "Invalid status '%s'" % status


def review_request_list(request, func, **kwargs):
    status = string_to_status(request.GET.get('status', 'pending'))
    return JsonResponse(request, {
        'review_requests': func(user=request.user, status=status, **kwargs)
    })


def count_review_requests(request, func, **kwargs):
    status = string_to_status(request.GET.get('status', 'pending'))
    return JsonResponse(request, {
        'count': func(user=request.user, status=status, **kwargs).count()
    })

def serialized_object(request, object_id, varname, queryset):
    return JsonResponse(request, {
        varname: queryset.get(pk=object_id)
    })
