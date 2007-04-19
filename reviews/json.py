import re

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers import serialize
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.db.models import Q
from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import timesince
from django.utils import simplejson
from django.views.decorators.http import require_GET, require_POST

from djblets.auth.util import login_required
from reviewboard.diffviewer.models import FileDiff, DiffSet
from reviewboard.reviews.models import ReviewRequest, Review, Group, Comment
from reviewboard.reviews.models import ReviewRequestDraft


class JsonError:
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg


DOES_NOT_EXIST            = JsonError(100, "Object does not exist")
PERMISSION_DENIED         = JsonError(101, "You don't have permission " +
                                           "to access this")
INVALID_ATTRIBUTE         = JsonError(102, "Invalid attribute")
UNSPECIFIED_DIFF_REVISION = JsonError(200, "Diff revision not specified")
INVALID_DIFF_REVISION     = JsonError(201, "Invalid diff revision")


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
        elif isinstance(o, Comment):
            return {
                'filediff': o.filediff,
                'text': o.text,
                'timestamp': o.timestamp,
                'first_line': o.first_line,
                'num_lines': o.num_lines,
            }
        elif isinstance(o, FileDiff):
            return {
                'diffset': o.diffset,
                'source_file': o.source_file,
                'dest_file': o.dest_file,
                'source_detail': o.source_detail,
                'dest_detail': o.dest_detail,
            }
        elif isinstance(o, DiffSet):
            return {
                'name': o.name,
                'revision': o.revision,
                'timestamp': o.timestamp
            }
        else:
            return super(ReviewBoardJSONEncoder, self).default(o)


class JsonResponse(HttpResponse):
    def __init__(self, request, obj={}, stat='ok'):
        json = {'stat': stat}
        json.update(obj)
        content = simplejson.dumps(json, cls=ReviewBoardJSONEncoder)

        callback = request.GET.get('callback', None)

        if callback != None:
            content = callback + "(" + content + ");"

        super(JsonResponse, self).__init__(content, mimetype='text/plain')
        #super(JsonResponse, self).__init__(content, mimetype='application/json')


class JsonResponseError(JsonResponse):
    def __init__(self, request, err, extra_params={}):
        errdata = {
            'err': {
                'code': err.code,
                'msg': err.msg
            }
        }
        errdata.update(extra_params)

        JsonResponse.__init__(self, request, errdata, "fail")


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


@login_required
def review_request_list(request, func, **kwargs):
    status = string_to_status(request.GET.get('status', 'pending'))
    return JsonResponse(request, {
        'review_requests': func(user=request.user, status=status, **kwargs)
    })


@login_required
def count_review_requests(request, func, **kwargs):
    status = string_to_status(request.GET.get('status', 'pending'))
    return JsonResponse(request, {
        'count': func(user=request.user, status=status, **kwargs).count()
    })


@login_required
def serialized_object(request, object_id, varname, queryset):
    try:
        return JsonResponse(request, {
            varname: queryset.get(pk=object_id)
        })
    except ObjectDoesNotExist:
        return JsonResponseError(request, DOES_NOT_EXIST,
                                 {'object_id': object_id})



@login_required
@require_POST
def review_request_draft_set(request, review_request_id, field_name):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if request.user != review_request.submitter:
        return JsonResponseError(request, PERMISSION_DENIED)

    form_data = request.POST.copy()

    if not hasattr(review_request, field_name):
        return JsonResponseError(request, INVALID_ATTRIBUTE,
                                 {'attribute': field_name})

    draft, draft_is_new = \
        ReviewRequestDraft.objects.get_or_create(
            review_request=review_request,
            defaults={
                'summary': review_request.summary,
                'description': review_request.description,
                'testing_done': review_request.testing_done,
                'bugs_closed': review_request.bugs_closed,
                'branch': review_request.branch,
            })

    if draft_is_new:
        map(draft.target_groups.add, review_request.target_groups.all())
        map(draft.target_people.add, review_request.target_people.all())

        if review_request.diffset_history.diffset_set.count() > 0:
            draft.diffset = \
                review_request.diffset_history.diffset_set.latest()

    result = {}

    if field_name == "target_groups" or field_name == "target_people":
        values = re.split(r"[, ]+", form_data['value'])
        target = getattr(draft, field_name)
        target.clear()

        invalid_entries = []

        for value in values:
            try:
                if field_name == "target_groups":
                    obj = Group.objects.get(name=value)
                elif field_name == "target_people":
                    obj = User.objects.get(username=value)

                target.add(obj)
            except:
                invalid_entries.append(value)

        result[field_name] = target.all()
        result['invalid_entries'] = invalid_entries
    else:
        setattr(draft, field_name, form_data['value'])

        if field_name == 'bugs_closed':
            result[field_name] = \
                [int(bug) for bug in form_data['value'].split(",")]
        else:
            result[field_name] = form_data['value']

    draft.save()

    return JsonResponse(request, result)


@login_required
@require_POST
def review_draft_save(request, review_request_id, publish=False):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if not request.POST.has_key('diff_revision'):
        return JsonResponseError(request, UNSPECIFIED_DIFF_REVISION)

    diff_revision = request.POST['diff_revision']

    try:
        diffset = review_request.diffset_history.diffset_set.get(
            revision=diff_revision)
    except DiffSet.DoesNotExist:
        return JsonResponseError(request, INVALID_DIFF_REVISION,
                                 {'diff_revision': diff_revision})

    review, review_is_new = Review.objects.get_or_create(
        user=request.user,
        review_request=review_request,
        public=False,
        reviewed_diffset=diffset)
    review.public      = publish
    review.ship_it     = request.POST.has_key('shipit')
    review.body_top    = request.POST['body_top']
    review.body_bottom = request.POST['body_bottom']
    review.save()

    if publish and settings.SEND_REVIEW_MAIL:
        mail_review(request.user, review)

    return JsonResponse(request)


@login_required
@require_POST
def review_draft_delete(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if not request.POST.has_key('diff_revision'):
        return JsonResponseError(request, UNSPECIFIED_DIFF_REVISION)

    diff_revision = request.POST['diff_revision']

    try:
        diffset = review_request.diffset_history.diffset_set.get(
            revision=diff_revision)
    except DiffSet.DoesNotExist:
        return JsonResponseError(request, INVALID_DIFF_REVISION,
                                 {'diff_revision': diff_revision})

    try:
        review = Review.objects.get(user=request.user,
                                    review_request=review_request,
                                    public=False,
                                    reviewed_diffset=diffset)

        for comment in review.comments.all():
            comment.delete()

        review.delete()
        return JsonResponse(request)
    except Review.DoesNotExist:
        return JsonResponseError(request, DOES_NOT_EXIST)


@login_required
def review_draft_comments(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    diff_revision = request.GET.get('diff_revision', None)

    if diff_revision == None:
        return JsonResponseError(request, UNSPECIFIED_DIFF_REVISION)

    try:
        diffset = review_request.diffset_history.diffset_set.get(
            revision=diff_revision)
    except DiffSet.DoesNotExist:
        return JsonResponseError(request, INVALID_DIFF_REVISION,
                                 {'diff_revision': diff_revision})

    try:
        review = Review.objects.get(user=request.user,
                                    review_request=review_request,
                                    public=False,
                                    reviewed_diffset=diffset)
        comments = review.comments.all()
    except Review.DoesNotExist:
        comments = []

    return JsonResponse(request, {
        'comments': comments,
    })
