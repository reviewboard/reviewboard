from datetime import datetime
import re

from django.conf import settings
from django.contrib import auth
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

from djblets.util.decorators import simple_decorator
from reviewboard.diffviewer.forms import UploadDiffForm
from reviewboard.diffviewer.models import FileDiff, DiffSet, DiffSetHistory
import reviewboard.reviews.db as reviews_db
from reviewboard.reviews.email import mail_review, mail_review_request, \
                                      mail_reply
from reviewboard.reviews.models import ReviewRequest, Review, Group, Comment
from reviewboard.reviews.models import ReviewRequestDraft


class JsonError:
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg


NO_ERROR                  = JsonError(0,   "If you see this, yell at " +
                                           "the developers")

DOES_NOT_EXIST            = JsonError(100, "Object does not exist")
PERMISSION_DENIED         = JsonError(101, "You don't have permission " +
                                           "to access this")
INVALID_ATTRIBUTE         = JsonError(102, "Invalid attribute")
NOT_LOGGED_IN             = JsonError(103, "You are not logged in")

UNSPECIFIED_DIFF_REVISION = JsonError(200, "Diff revision not specified")
INVALID_DIFF_REVISION     = JsonError(201, "Invalid diff revision")
INVALID_ACTION            = JsonError(202, "Invalid action specified")
INVALID_CHANGE_NUMBER     = JsonError(203, "The change number specified " +
                                           "could not be found")
CHANGE_NUMBER_IN_USE      = JsonError(204, "The change number specified " +
                                           "has already been used")


@simple_decorator
def json_login_required(view_func):
    def _checklogin(request, *args, **kwargs):
        if request.user.is_authenticated():
            return view_func(request, *args, **kwargs)
        else:
            return JsonResponseError(request, NOT_LOGGED_IN)
    return _checklogin

class ReviewBoardJSONEncoder(DateTimeAwareJSONEncoder):
    def default(self, o):
        if isinstance(o, QuerySet):
            return list(o)
        elif isinstance(o, User):
            return {
                'id': o.id,
                'username': o.username,
                'fullname': o.get_full_name(),
                'email': o.email,
                'url': o.get_absolute_url(),
            }
        elif isinstance(o, Group):
            return {
                'id': o.id,
                'name': o.name,
                'mailing_list': o.mailing_list,
                'url': o.get_absolute_url(),
            }
        elif isinstance(o, ReviewRequest):
            if o.bugs_closed == '':
                bugs_closed = []
            else:
                bugs_closed = map(int, o.bugs_closed.split(","))

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
                'bugs_closed': bugs_closed,
                'branch': o.branch,
                'target_groups': o.target_groups.all(),
                'target_people': o.target_people.all(),
            }
        elif isinstance(o, Review):
            return {
                'id': o.id,
                'user': o.user,
                'timestamp': o.timestamp,
                'public': o.public,
                'ship_it': o.ship_it,
                'body_top': o.body_top,
                'body_bottom': o.body_bottom,
                'comments': o.comments.all(),
                'reviewed_diffset': o.reviewed_diffset,
            }
        elif isinstance(o, Comment):
            review = o.review_set.get()
            return {
                'id': o.id,
                'filediff': o.filediff,
                'text': o.text,
                'timestamp': o.timestamp,
                'timesince': timesince(o.timestamp),
                'first_line': o.first_line,
                'num_lines': o.num_lines,
                'public': review.public,
                'user': review.user,
            }
        elif isinstance(o, FileDiff):
            return {
                'id': o.id,
                'diffset': o.diffset,
                'source_file': o.source_file,
                'dest_file': o.dest_file,
                'source_detail': o.source_detail,
                'dest_detail': o.dest_detail,
            }
        elif isinstance(o, DiffSet):
            return {
                'id': o.id,
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


@json_login_required
@require_POST
def new_review_request(request):
    try:
        review_request = reviews_db.create_review_request(
            request.user, request.POST.get('changenum', None))
        return JsonResponse(request, {'review_request': review_request})
    except reviews_db.ChangeNumberInUseException, e:
        return JsonResponseError(request, CHANGE_NUMBER_IN_USE,
                                 {'review_request': e.review_request})
    except reviews_db.InvalidChangeNumberException:
        return JsonResponseError(request, INVALID_CHANGE_NUMBER)


@json_login_required
def review_request(request, review_request_id):
    """
    Returns the review request with the specified ID.
    """
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if not review_request.public and review_request.submitter != request.user:
        return JsonResponseError(request, PERMISSION_DENIED)

    return JsonResponse(request, {'review_request': review_request})


@json_login_required
def review_request_by_changenum(request, changenum):
    try:
        review_request = ReviewRequest.objects.get(changenum=changenum)

        if not review_request.public and \
           review_request.submitter != request.user:
            return JsonResponseError(request, PERMISSION_DENIED)

        return JsonResponse(request, {'review_request': review_request})
    except ReviewRequest.DoesNotExist:
        return JsonResponseError(request, INVALID_CHANGE_NUMBER)


@json_login_required
def review_request_list(request, func, **kwargs):
    status = string_to_status(request.GET.get('status', 'pending'))
    return JsonResponse(request, {
        'review_requests': func(user=request.user, status=status, **kwargs)
    })


@json_login_required
def count_review_requests(request, func, **kwargs):
    status = string_to_status(request.GET.get('status', 'pending'))
    return JsonResponse(request, {
        'count': func(user=request.user, status=status, **kwargs).count()
    })


def _get_and_validate_review(review_request_id, review_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    review = get_object_or_404(Review, pk=review_id)

    if review.review_request != review_request or review.base_reply_to != None:
        raise Http404()

    if not review.public and review.user != request.user:
        return JsonResponseError(request, PERMISSION_DENIED)

    return review


@json_login_required
def review(request, review_request_id, review_id):
    review = _get_and_validate_review(review_request_id, review_id)

    if isinstance(review, JsonResponseError):
        return review

    return JsonResponse(request, {'review': review})


def _get_reviews(review_request):
    return review_request.review_set.filter(public=True,
                                            base_reply_to__isnull=True)


@json_login_required
def review_list(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    return JsonResponse(request, {
        'reviews': _get_reviews(review_request)
    })


@json_login_required
def count_review_list(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    return JsonResponse(request, {
        'reviews': _get_reviews(review_request).count()
    })


@json_login_required
def review_comments_list(request, review_request_id, review_id):
    review = _get_and_validate_review(review_request_id, review_id)

    if isinstance(review, JsonResponseError):
        return review

    return JsonResponse(request, {'comments': review.comments.all()})


@json_login_required
def count_review_comments(request, review_request_id, review_id):
    review = _get_and_validate_review(review_request_id, review_id)

    if isinstance(review, JsonResponseError):
        return review

    return JsonResponse(request, {'count': review.comments.count()})


@json_login_required
@require_POST
def review_request_draft_discard(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    try:
        draft = ReviewRequestDraft.objects.get(review_request=review_request)
    except ReviewRequestDraft.DoesNotExist:
        return JsonResponseError(request, DOES_NOT_EXIST)

    if review_request.submitter != request.user:
        return JsonResponseError(request, PERMISSION_DENIED)

    draft.delete()

    return JsonResponse(request)


@json_login_required
@require_POST
def review_request_draft_save(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    try:
        draft = ReviewRequestDraft.objects.get(review_request=review_request)
    except ReviewRequestDraft.DoesNotExist:
        return JsonResponseError(request, DOES_NOT_EXIST)

    if review_request.submitter != request.user:
        return JsonResponseError(request, PERMISSION_DENIED)

    review_request.summary = draft.summary
    review_request.description = draft.description
    review_request.testing_done = draft.testing_done
    review_request.bugs_closed = draft.bugs_closed
    review_request.branch = draft.branch

    review_request.target_groups.clear()
    map(review_request.target_groups.add, draft.target_groups.all())

    review_request.target_people.clear()
    map(review_request.target_people.add, draft.target_people.all())

    if draft.diffset:
        draft.diffset.history = review_request.diffset_history
        draft.diffset.save()

    review_request.save()
    draft.delete()

    return JsonResponse(request)


def find_user(username):
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        for backend in auth.get_backends():
            try:
                user = backend.get_or_create_user(username)
            except:
                pass
            if user:
                return user
    return None


def _prepare_draft(request, review_request):
    if request.user != review_request.submitter:
        return JsonResponseError(request, PERMISSION_DENIED)

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
            draft.diffset = review_request.diffset_history.diffset_set.latest()

    return draft


def _set_draft_field_data(draft, field_name, data):
    if field_name == "target_groups" or field_name == "target_people":
        values = re.split(r"[, ]+", data)
        target = getattr(draft, field_name)
        target.clear()

        invalid_entries = []

        for value in values:
            try:
                if field_name == "target_groups":
                    obj = Group.objects.get(name=value)
                elif field_name == "target_people":
                    obj = find_user(username=value)

                target.add(obj)
            except:
                invalid_entries.append(value)

        return target.all(), invalid_entries
    else:
        setattr(draft, field_name, data)

        if field_name == 'bugs_closed':
            if data == '':
                data = []
            else:
                data = map(int, data.split(","))

        return data, None


@json_login_required
@require_POST
def review_request_draft_set_field(request, review_request_id, field_name):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if not hasattr(review_request, field_name):
        return JsonResponseError(request, INVALID_ATTRIBUTE,
                                 {'attribute': field_name})

    draft = _prepare_draft(request, review_request)
    result = {}

    result[field_name], result['invalid_' + field_name] = \
        _set_draft_field_data(draft, field_name, request.POST['value'])

    draft.save()

    return JsonResponse(request, result)


mutable_review_request_fields = [
    'status', 'public', 'summary', 'description', 'testing_done',
    'bugs_closed', 'branch', 'target_groups', 'target_people'
]

@json_login_required
@require_POST
def review_request_draft_set(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    draft = _prepare_draft(request, review_request)

    result = {}

    for field_name in mutable_review_request_fields:
        if request.POST.has_key(field_name):
            value, result['invalid_' + field_entries] = \
                _set_draft_field_data(draft, field_name,
                                      request.POST[field_name])

    draft.save()

    result['draft'] = draft

    return JsonResponse(request, result)


@json_login_required
@require_POST
def review_request_draft_update_from_changenum(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    draft = _prepare_draft(request, review_request)

    changeset = scmtools.get_tool().get_changeset(review_request.changenum)

    try:
        reviews_db.update_review_request_from_changenum(review_request,
                                                        changenum)
    except reviews_db.InvalidChangeNumberException:
        return JsonResponseError(request, INVALID_CHANGE_NUMBER,
                                 {'changenum': review_request.changenum})

    review_request.save()

    return JsonResponse(request, {'review_request': review_request})


@json_login_required
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


@json_login_required
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


@json_login_required
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


@json_login_required
@require_POST
def review_reply_draft(request, review_request_id, review_id):
    source_review = _get_and_validate_review(review_request_id, review_id)
    if isinstance(source_review, JsonResponseError):
        return source_review

    context_type = request.POST['type']
    context_id = request.POST['id']
    value = request.POST['value']

    reply, reply_is_new = Review.objects.get_or_create(
        review_request=source_review.review_request,
        user=request.user,
        public=False,
        base_reply_to=source_review,
        reviewed_diffset=source_review.reviewed_diffset)

    if reply_is_new:
        reply.save()

    if context_type == "comment":
        context_comment = Comment.objects.get(pk=context_id)

        try:
            comment = Comment.objects.get(review=reply,
                                          reply_to=context_comment)
            comment_is_new = False
        except Comment.DoesNotExist:
            comment = Comment(reply_to=context_comment,
                              filediff=context_comment.filediff,
                              first_line=context_comment.first_line,
                              num_lines=context_comment.num_lines)
            comment_is_new = True

        comment.text = value
        comment.timestamp = datetime.now()

        if value == "" and not comment_is_new:
            comment.delete()
        else:
            comment.save()

            if comment_is_new:
                reply.comments.add(comment)

    elif context_type == "body_top":
        reply.body_top = value

        if value == "":
            reply.body_top_reply_to = None
        else:
            reply.body_top_reply_to = source_review

    elif context_type == "body_bottom":
        reply.body_bottom = value

        if value == "":
            reply.body_bottom_reply_to = None
        else:
            reply.body_bottom_reply_to = source_review
    else:
        raise Http403()

    if reply.body_top == "" and reply.body_bottom == "" and \
       reply.comments.count() == 0:
        reply.delete()
    else:
        reply.save()

    return JsonResponse(request)


@json_login_required
@require_POST
def review_reply_draft_save(request, review_request_id, review_id):
    review = _get_and_validate_review(review_request_id, review_id)
    if isinstance(review, JsonResponseError):
        return review

    try:
        reply = Review.objects.get(base_reply_to=review, public=False,
                                   user=request.user)
        reply.public = True
        reply.save()

        if settings.SEND_REVIEW_MAIL:
            mail_reply(request.user, reply)

        return JsonResponse(request)
    except Review.DoesNotExist:
        return JsonResponseError(request, DOES_NOT_EXIST)


@json_login_required
@require_POST
def review_reply_draft_discard(request, review_request_id, review_id):
    review = _get_and_validate_review(review_request_id, review_id)
    if isinstance(review, JsonResponseError):
        return review

    try:
        reply = Review.objects.get(base_reply_to=review, public=False,
                                   user=request.user)
        for comment in reply.comments.all():
            comment.delete()
        reply.delete()
        return JsonResponse(request)
    except Review.DoesNotExist:
        return JsonResponseError(request, DOES_NOT_EXIST)


@json_login_required
def review_replies_list(request, review_request_id, review_id):
    review = _get_and_validate_review(review_request_id, review_id)
    if isinstance(review, JsonResponseError):
        return review

    return JsonResponse(request,
        {'replies': review.replies.filter(public=True)})


@json_login_required
def count_review_replies(request, review_request_id, review_id):
    review = _get_and_validate_review(review_request_id, review_id)
    if isinstance(review, JsonResponseError):
        return review

    return JsonResponse(request,
        {'count': review.replies.filter(public=True).count()})


@json_login_required
@require_POST
def new_diff(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if review_request.submitter != request.user:
        return JsonResponseError(request, PERMISSION_DENIED)

    form_data = request.POST.copy()
    form_data.update(request.FILES)
    form = UploadDiffForm(form_data)

    if not form.is_valid():
        return JsonResponseError(request, INVALID_ATTRIBUTE)

    diffset = form.create(request.FILES['path'], review_request.diffset_history)

    try:
        draft = review_request.reviewrequestdraft_set.get()

        if draft.diffset and draft.diffset != diffset:
            draft.diffset.delete()

        draft.diffset = diffset
        draft.save()
    except ReviewRequestDraft.DoesNotExist:
        diffset.history = review_request.diffset_history
        diffset.save()

    return JsonResponse(request, {'diffset_id': diffset.id})


@json_login_required
def diff_line_comments(request, review_request_id, diff_revision,
                       filediff_id, line):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    filediff = get_object_or_404(FileDiff,
        pk=filediff_id, diffset__history=review_request.diffset_history,
        diffset__revision=diff_revision)

    if request.POST:
        text = request.POST['text']
        num_lines = request.POST['num_lines']
        action = request.POST['action']

        # TODO: Sanity check the fields

        if action == "set":
            review, review_is_new = Review.objects.get_or_create(
                review_request=review_request,
                user=request.user,
                public=False,
                reviewed_diffset=filediff.diffset)

            if review_is_new:
                review.save()

            comment, comment_is_new = review.comments.get_or_create(
                filediff=filediff,
                first_line=line)

            comment.text = text
            comment.num_lines = num_lines
            comment.timestamp = datetime.now()
            comment.save()

            if comment_is_new:
                review.comments.add(comment)
                review.save()
        elif action == "delete":
            review = get_object_or_404(Review,
                review_request=review_request,
                user=request.user,
                public=False,
                reviewed_diffset=filediff.diffset)

            try:
                comment = review.comments.get(filediff=filediff,
                                              first_line=line)
                comment.delete()
            except Comment.DoesNotExist:
                pass

            if review.body_top.strip() == "" and \
               review.body_bottom.strip() == "" and \
               review.comments.count() == 0:
                review.delete()
        else:
            return JsonResponseError(request, INVALID_ACTION,
                                     {'action': action})

    return JsonResponse(request, {
        'comments': filediff.comment_set.filter(
            Q(review__public=True) | Q(review__user=request.user),
            first_line=line)
    })
