from datetime import datetime
import os.path
import re

from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import timesince
from django.views.decorators.http import require_POST
from djblets.util.misc import get_object_or_none
from djblets.webapi.core import WebAPIEncoder, WebAPIResponse, \
                                WebAPIResponseError, \
                                WebAPIResponseFormError
from djblets.webapi.decorators import webapi_login_required, \
                                      webapi_permission_required
from djblets.webapi.errors import WebAPIError, \
                                  PERMISSION_DENIED, DOES_NOT_EXIST, \
                                  INVALID_ATTRIBUTE, INVALID_FORM_DATA, \
                                  MISSING_ATTRIBUTE

from reviewboard.accounts.models import Profile
from reviewboard.diffviewer.forms import UploadDiffForm, EmptyDiffError
from reviewboard.diffviewer.models import FileDiff, DiffSet
from reviewboard.reviews.email import mail_review, mail_review_request, \
                                      mail_reply
from reviewboard.reviews.forms import UploadScreenshotForm
from reviewboard.reviews.models import ChangeNumberInUseError, \
                                       InvalidChangeNumberError, \
                                       ReviewRequest, Review, Group, Comment, \
                                       ReviewRequestDraft, Screenshot, \
                                       ScreenshotComment
from reviewboard.scmtools.models import Repository
import reviewboard.scmtools as scmtools


#
# Standard error messages
#
UNSPECIFIED_DIFF_REVISION = WebAPIError(200, "Diff revision not specified")
INVALID_DIFF_REVISION     = WebAPIError(201, "Invalid diff revision")
INVALID_ACTION            = WebAPIError(202, "Invalid action specified")
INVALID_CHANGE_NUMBER     = WebAPIError(203, "The change number specified " +
                                             "could not be found")
CHANGE_NUMBER_IN_USE      = WebAPIError(204, "The change number specified " +
                                             "has already been used")
MISSING_REPOSITORY        = WebAPIError(205, "A repository path must be " +
                                             "specified")
INVALID_REPOSITORY        = WebAPIError(206, "The repository path specified " +
                                             "is not in the list of known " +
                                             "repositories")
REPO_FILE_NOT_FOUND       = WebAPIError(207, "The file was not found in the " +
                                             "repository")
INVALID_USER              = WebAPIError(208, "User does not exist")
REPO_NOT_IMPLEMENTED      = WebAPIError(209, "The specified repository is " +
                                             "not able to perform this action")
REPO_INFO_ERROR           = WebAPIError(210, "There was an error fetching " +
                                             "extended information for this " +
                                             "repository.")


class ReviewBoardAPIEncoder(WebAPIEncoder):
    def encode(self, o):
        if isinstance(o, Group):
            return {
                'id': o.id,
                'name': o.name,
                'display_name': o.display_name,
                'mailing_list': o.mailing_list,
                'url': o.get_absolute_url(),
            }
        elif isinstance(o, ReviewRequest):
            if o.bugs_closed:
                bugs_closed = [b.strip() for b in o.bugs_closed.split(',')]
            else:
                bugs_closed = ''

            return {
                'id': o.id,
                'submitter': o.submitter,
                'time_added': o.time_added,
                'last_updated': o.last_updated,
                'status': status_to_string(o.status),
                'public': o.public,
                'changenum': o.changenum,
                'repository': o.repository,
                'summary': o.summary,
                'description': o.description,
                'testing_done': o.testing_done,
                'bugs_closed': bugs_closed,
                'branch': o.branch,
                'target_groups': o.target_groups.all(),
                'target_people': o.target_people.all(),
            }
        elif isinstance(o, ReviewRequestDraft):
            if o.bugs_closed != "":
                bugs_closed = [b.strip() for b in o.bugs_closed.split(',')]
            else:
                bugs_closed = []

            return {
                'id': o.id,
                'review_request': o.review_request,
                'last_updated': o.last_updated,
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
            }
        elif isinstance(o, Comment):
            review = o.review_set.get()
            return {
                'id': o.id,
                'filediff': o.filediff,
                'interfilediff': o.interfilediff,
                'text': o.text,
                'timestamp': o.timestamp,
                'timesince': timesince(o.timestamp),
                'first_line': o.first_line,
                'num_lines': o.num_lines,
                'public': review.public,
                'user': review.user,
            }
        elif isinstance(o, ScreenshotComment):
            review = o.review_set.get()
            return {
                'id': o.id,
                'screenshot': o.screenshot,
                'text': o.text,
                'timestamp': o.timestamp,
                'timesince': timesince(o.timestamp),
                'public': review.public,
                'user': review.user,
                'x': o.x,
                'y': o.y,
                'w': o.w,
                'h': o.h,
            }
        elif isinstance(o, Screenshot):
            return {
                'id': o.id,
                'caption': o.caption,
                'title': u'Screenshot: %s' % (o.caption or
                                              os.path.basename(o.image)),
                'image_url': o.get_absolute_url(),
            }
        elif isinstance(o, FileDiff):
            return {
                'id': o.id,
                'diffset': o.diffset,
                'source_file': o.source_file,
                'dest_file': o.dest_file,
                'source_revision': o.source_revision,
                'dest_detail': o.dest_detail,
            }
        elif isinstance(o, DiffSet):
            return {
                'id': o.id,
                'name': o.name,
                'revision': o.revision,
                'timestamp': o.timestamp,
                'repository': o.repository,
            }
        elif isinstance(o, Repository):
            return {
                'id': o.id,
                'name': o.name,
                'path': o.path,
                'tool': o.tool.name
            }
        else:
            return super(ReviewBoardAPIEncoder, self).encode(o)


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


@webapi_login_required
def repository_list(request):
    """
    Returns a list of all known repositories.
    """
    return WebAPIResponse(request, {
        'repositories': Repository.objects.all(),
    })


@webapi_login_required
def repository_info(request, repository_id):
    try:
        repository = Repository.objects.get(id=repository_id)
    except Repository.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)

    try:
        return WebAPIResponse(request, {
            'info': repository.get_scmtool().get_repository_info()
        })
    except NotImplementedError:
        return WebAPIResponseError(request, REPO_NOT_IMPLEMENTED)
    except:
        return WebAPIResponseError(request, REPO_INFO_ERROR)

@webapi_login_required
def user_list(request):
    """
    Returns a list of all users.

    If the query parameter is passed, users with a username beginning with
    the query value will be returned.
    """
    query = request.GET.get('query', None)
    if not query:
        u = User.objects.filter(is_active=True)
    else:
        u = User.objects.filter(is_active=True, username__startswith=query)

    return WebAPIResponse(request, {
        'users': u,
    })

@webapi_login_required
def group_list(request):
    """
    Returns a list of all review groups.

    If the query parameter is passed, groups with a name beginning with
    the query value will be returned.
    """
    query = request.GET.get('query', None)
    if not query:
        u = Group.objects.all()
    else:
        u = Group.objects.filter(name__startswith=query)

    return WebAPIResponse(request, {
        'groups': u,
    })

@webapi_login_required
def users_in_group(request, group_name):
    """
    Returns a list of users in a group.
    """
    try:
        g = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)

    return WebAPIResponse(request, {
        'users': g.users.all(),
    })

@webapi_login_required
def group_star(request, group_name):
    """
    Adds a group to the user's watched groups list.
    """
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)

    profile, profile_is_new = Profile.objects.get_or_create(user=request.user)
    profile.starred_groups.add(group)
    profile.save()

    return WebAPIResponse(request)


@webapi_login_required
def group_unstar(request, group_name):
    """
    Removes a group from the user's watched groups list.
    """
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)

    profile, profile_is_new = Profile.objects.get_or_create(user=request.user)

    if not profile_is_new:
        profile.starred_groups.remove(group)
        profile.save()

    return WebAPIResponse(request)


@webapi_login_required
@require_POST
def new_review_request(request):
    """
    Creates a new review request.

    Required parameters:

      * repository_path: The repository to create the review request against.
                         If not specified, the DEFAULT_REPOSITORY_PATH
                         setting will be used.
                         If both this and repository_id are set,
                         repository_path's value takes precedence.
      * repository_id:   The ID of the repository to create the review
                         request against.


    Optional parameters:

      * submit_as:       The optional user to submit the review request as.
                         This requires that the actual logged in user is
                         either a superuser or has the
                         "reviews.can_submit_as_another_user" property.
      * changenum:       The optional changenumber to look up for the review
                         request details. This only works with repositories
                         that support changesets.

    Returned keys:

      * 'review_request': The resulting review request

    Errors:

      * INVALID_REPOSITORY
      * CHANGE_NUMBER_IN_USE
      * INVALID_CHANGE_NUMBER
    """
    try:
        repository_path = request.POST.get('repository_path',
                                           settings.DEFAULT_REPOSITORY_PATH)
        repository_id = request.POST.get('repository_id', None)
        submit_as = request.POST.get('submit_as')

        if submit_as:
            if not request.user.has_perm('reviews.can_submit_as_another_user'):
                return WebAPIResponseError(request, PERMISSION_DENIED)
            try:
                user = User.objects.get(username=submit_as)
            except User.DoesNotExist:
                return WebAPIResponseError(request, INVALID_USER)
        else:
            user = request.user

        if repository_path == None and repository_id == None:
            return WebAPIResponseError(request, MISSING_REPOSITORY)

        if repository_path:
            repository = Repository.objects.get(
                Q(path=repository_path) |
                Q(mirror_path=repository_path))
        else:
            repository = Repository.objects.get(id=repository_id)

        review_request = ReviewRequest.objects.create(
            user, repository, request.POST.get('changenum', None))

        return WebAPIResponse(request, {'review_request': review_request})
    except Repository.DoesNotExist, e:
        return WebAPIResponseError(request, INVALID_REPOSITORY,
                                 {'repository_path': repository_path})
    except ChangeNumberInUseError, e:
        return WebAPIResponseError(request, CHANGE_NUMBER_IN_USE,
                                 {'review_request': e.review_request})
    except InvalidChangeNumberError:
        return WebAPIResponseError(request, INVALID_CHANGE_NUMBER)


@webapi_login_required
def review_request(request, review_request_id):
    """
    Returns the review request with the specified ID.
    """
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if not review_request.is_accessible_by(request.user):
        return WebAPIResponseError(request, PERMISSION_DENIED)

    return WebAPIResponse(request, {'review_request': review_request})


@webapi_login_required
def review_request_by_changenum(request, repository_id, changenum):
    """
    Returns a review request with the specified changenum.
    """
    try:
        review_request = ReviewRequest.objects.get(changenum=changenum,
                                                   repository=repository_id)

        if not review_request.is_accessible_by(request.user):
            return WebAPIResponseError(request, PERMISSION_DENIED)

        return WebAPIResponse(request, {'review_request': review_request})
    except ReviewRequest.DoesNotExist:
        return WebAPIResponseError(request, INVALID_CHANGE_NUMBER)


@webapi_login_required
def review_request_star(request, review_request_id):
    try:
        review_request = ReviewRequest.objects.get(pk=review_request_id)
    except ReviewRequest.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)

    profile, profile_is_new = Profile.objects.get_or_create(user=request.user)
    profile.starred_review_requests.add(review_request)
    profile.save()

    return WebAPIResponse(request)


@webapi_login_required
def review_request_unstar(request, review_request_id):
    try:
        review_request = ReviewRequest.objects.get(pk=review_request_id)
    except ReviewRequest.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)

    profile, profile_is_new = Profile.objects.get_or_create(user=request.user)

    if not profile_is_new:
        profile.starred_review_requests.remove(review_request)
        profile.save()

    return WebAPIResponse(request)


@webapi_permission_required('reviews.delete_reviewrequest')
def review_request_delete(request, review_request_id):
    try:
        review_request = ReviewRequest.objects.get(pk=review_request_id)
        review_request.delete()
    except ReviewRequest.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)

    return WebAPIResponse(request)


@webapi_login_required
def review_request_list(request, func, **kwargs):
    """
    Returns a list of review requests.

    Optional parameters:

      * status: The status of the returned review requests. This defaults
                to "pending".
    """
    status = string_to_status(request.GET.get('status', 'pending'))
    return WebAPIResponse(request, {
        'review_requests': func(user=request.user, status=status, **kwargs)
    })


@webapi_login_required
def count_review_requests(request, func, **kwargs):
    """
    Returns the number of review requests.

    Optional parameters:

      * status: The status of the returned review requests. This defaults
                to "pending".
    """
    status = string_to_status(request.GET.get('status', 'pending'))
    return WebAPIResponse(request, {
        'count': func(user=request.user, status=status, **kwargs).count()
    })


def _get_and_validate_review(request, review_request_id, review_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    review = get_object_or_404(Review, pk=review_id)

    if review.review_request != review_request or review.base_reply_to != None:
        raise Http404()

    if not review.public and review.user != request.user:
        return WebAPIResponseError(request, PERMISSION_DENIED)

    return review


@webapi_login_required
def review(request, review_request_id, review_id):
    review = _get_and_validate_review(request, review_request_id, review_id)

    if isinstance(review, WebAPIResponseError):
        return review

    return WebAPIResponse(request, {'review': review})


def _get_reviews(review_request):
    return review_request.review_set.filter(public=True,
                                            base_reply_to__isnull=True)


@webapi_login_required
def review_list(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    return WebAPIResponse(request, {
        'reviews': _get_reviews(review_request)
    })


@webapi_login_required
def count_review_list(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    return WebAPIResponse(request, {
        'reviews': _get_reviews(review_request).count()
    })


@webapi_login_required
def review_comments_list(request, review_request_id, review_id):
    review = _get_and_validate_review(request, review_request_id, review_id)

    if isinstance(review, WebAPIResponseError):
        return review

    return WebAPIResponse(request, {
        'comments': review.comments.all(),
        'screenshot_comments': review.screenshot_comments.all(),
    })


@webapi_login_required
def count_review_comments(request, review_request_id, review_id):
    review = _get_and_validate_review(request, review_request_id, review_id)

    if isinstance(review, WebAPIResponseError):
        return review

    return WebAPIResponse(request, {'count': review.comments.count()})


@webapi_login_required
@require_POST
def review_request_draft_discard(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    try:
        draft = ReviewRequestDraft.objects.get(review_request=review_request)
    except ReviewRequestDraft.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)

    if not review_request.is_mutable_by(request.user):
        return WebAPIResponseError(request, PERMISSION_DENIED)

    draft.delete()

    return WebAPIResponse(request)


@webapi_login_required
@require_POST
def review_request_draft_save(request, review_request_id):
    try:
        draft = ReviewRequestDraft.objects.get(review_request=review_request_id)
        review_request = draft.review_request
    except ReviewRequestDraft.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)

    if not review_request.is_mutable_by(request.user):
        return WebAPIResponseError(request, PERMISSION_DENIED)

    changes = draft.save_draft()
    draft.delete()

    if settings.SEND_REVIEW_MAIL and changes:
        mail_review_request(request.user, review_request, changes)

    return WebAPIResponse(request)


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
    if not review_request.is_mutable_by(request.user):
        return WebAPIResponseError(request, PERMISSION_DENIED)
    return ReviewRequestDraft.create(review_request)


def _set_draft_field_data(draft, field_name, data):
    if field_name == "target_groups" or field_name == "target_people":
        values = re.split(r",\s*", data)
        target = getattr(draft, field_name)
        target.clear()

        invalid_entries = []

        for value in values:
            # Prevent problems if the user leaves a trailing comma,
            # generating an empty value.
            if not value:
                continue

            try:
                if field_name == "target_groups":
                    obj = Group.objects.get(Q(name__iexact=value) |
                                            Q(display_name__iexact=value))
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
                data = [b.strip() for b in data.split(',')]

        return data, None


@webapi_login_required
@require_POST
def review_request_draft_set_field(request, review_request_id, field_name):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    #if not request.POST['value']:
    #    return WebAPIResponseError(request, MISSING_ATTRIBUTE,
    #                               {'attribute': field_name})

    m = re.match(r'screenshot_(?P<id>[0-9]+)_caption', field_name)
    if m:
        try:
            screenshot = Screenshot.objects.get(id=int(m.group('id')))
        except:
            return WebAPIResponseError(request, INVALID_ATTRIBUTE,
                                       {'attribute': field_name})

        draft = _prepare_draft(request, review_request)
        screenshot.draft_caption = data = request.POST['value']
        screenshot.save()
        draft.save()

        return WebAPIResponse(request, {field_name: data})

    if not hasattr(review_request, field_name):
        return WebAPIResponseError(request, INVALID_ATTRIBUTE,
                                   {'attribute': field_name})

    draft = _prepare_draft(request, review_request)
    result = {}

    result[field_name], result['invalid_' + field_name] = \
        _set_draft_field_data(draft, field_name, request.POST['value'])

    draft.save()

    return WebAPIResponse(request, result)


mutable_review_request_fields = [
    'status', 'public', 'summary', 'description', 'testing_done',
    'bugs_closed', 'branch', 'target_groups', 'target_people'
]

@webapi_login_required
@require_POST
def review_request_draft_set(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    draft = _prepare_draft(request, review_request)

    result = {}

    for field_name in mutable_review_request_fields:
        if request.POST.has_key(field_name):
            value, result['invalid_' + field_name] = \
                _set_draft_field_data(draft, field_name,
                                      request.POST[field_name])

    draft.save()

    result['draft'] = draft

    return WebAPIResponse(request, result)


@webapi_login_required
@require_POST
def review_request_draft_update_from_changenum(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    draft = _prepare_draft(request, review_request)

    tool = review_request.repository.get_scmtool()
    changeset = tool.get_changeset(review_request.changenum)

    try:
        draft.update_from_changenum(review_request.changenum)
    except InvalidChangeNumberError:
        return WebAPIResponseError(request, INVALID_CHANGE_NUMBER,
                                 {'changenum': review_request.changenum})

    draft.save()

    if review_request.status == 'D':
        review_request.status = 'P'
        review_request.public = False
        review_request.save()

    return WebAPIResponse(request, {
        'draft': draft,
        'review_request': review_request,
    })


@webapi_login_required
@require_POST
def review_draft_save(request, review_request_id, publish=False):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    review, review_is_new = Review.objects.get_or_create(
        user=request.user,
        review_request=review_request,
        public=False,
        base_reply_to__isnull=True)
    review.ship_it     = request.POST.has_key('shipit')
    review.body_top    = request.POST['body_top']
    review.body_bottom = request.POST['body_bottom']

    if publish:
        review.publish()
    else:
        review.save()

    if publish and settings.SEND_REVIEW_MAIL:
        mail_review(request.user, review)

    return WebAPIResponse(request)


@webapi_login_required
@require_POST
def review_draft_delete(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    try:
        review = Review.objects.get(user=request.user,
                                    review_request=review_request,
                                    public=False,
                                    base_reply_to__isnull=True)
        review.delete()
        return WebAPIResponse(request)
    except Review.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)


@webapi_login_required
def review_draft_comments(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    try:
        review = Review.objects.get(user=request.user,
                                    review_request=review_request,
                                    public=False,
                                    base_reply_to__isnull=True)
        comments = review.comments.all()
        screenshot_comments = review.screenshot_comments.all()
    except Review.DoesNotExist:
        comments = []
        screenshot_comments = []

    return WebAPIResponse(request, {
        'comments': comments,
        'screenshot_comments': screenshot_comments,
    })


@webapi_login_required
@require_POST
def review_reply_draft(request, review_request_id, review_id):
    source_review = _get_and_validate_review(request, review_request_id,
                                             review_id)
    if isinstance(source_review, WebAPIResponseError):
        return source_review

    context_type = request.POST['type']
    value = request.POST['value']

    reply, reply_is_new = Review.objects.get_or_create(
        review_request=source_review.review_request,
        user=request.user,
        public=False,
        base_reply_to=source_review)

    result = {
        'reply': reply,
    }

    if reply_is_new:
        reply.save()

    if context_type == "comment":
        context_id = request.POST['id']
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
            result['comment'] = comment

            if comment_is_new:
                reply.comments.add(comment)

    elif context_type == "screenshot_comment":
        context_id = request.POST['id']
        context_comment = ScreenshotComment.objects.get(pk=context_id)

        try:
            comment = ScreenshotComment.objects.get(review=reply,
                                                    reply_to=context_comment)
            comment_is_new = False
        except ScreenshotComment.DoesNotExist:
            comment = ScreenshotComment(reply_to=context_comment,
                                        screenshot=context_comment.screenshot,
                                        x=context_comment.x,
                                        y=context_comment.y,
                                        w=context_comment.w,
                                        h=context_comment.h)
            comment_is_new = True

        comment.text = value
        comment.timestamp = datetime.now()

        if value == "" and not comment_is_new:
            comment.delete()
        else:
            comment.save()
            result['screenshot_comment'] = comment

            if comment_is_new:
                reply.screenshot_comments.add(comment)

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
        raise HttpResponseForbidden()

    if reply.body_top == "" and reply.body_bottom == "" and \
       reply.comments.count() == 0 and reply.screenshot_comments.count() == 0:
        reply.delete()
    else:
        reply.save()

    return WebAPIResponse(request, result)


@webapi_login_required
@require_POST
def review_reply_draft_save(request, review_request_id, review_id):
    review = _get_and_validate_review(request, review_request_id, review_id)
    if isinstance(review, WebAPIResponseError):
        return review

    try:
        reply = Review.objects.get(base_reply_to=review, public=False,
                                   user=request.user)
        reply.publish()

        if settings.SEND_REVIEW_MAIL:
            mail_reply(request.user, reply)

        return WebAPIResponse(request)
    except Review.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)


@webapi_login_required
@require_POST
def review_reply_draft_discard(request, review_request_id, review_id):
    review = _get_and_validate_review(request, review_request_id, review_id)
    if isinstance(review, WebAPIResponseError):
        return review

    try:
        reply = Review.objects.get(base_reply_to=review, public=False,
                                   user=request.user)
        reply.delete()
        return WebAPIResponse(request)
    except Review.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)


@webapi_login_required
def review_replies_list(request, review_request_id, review_id):
    review = _get_and_validate_review(request, review_request_id, review_id)
    if isinstance(review, WebAPIResponseError):
        return review

    return WebAPIResponse(request, {
        'replies': review.replies.filter(public=True)
    })


@webapi_login_required
def count_review_replies(request, review_request_id, review_id):
    review = _get_and_validate_review(request, review_request_id, review_id)
    if isinstance(review, WebAPIResponseError):
        return review

    return WebAPIResponse(request, {
        'count': review.replies.filter(public=True).count()
    })


@webapi_login_required
@require_POST
def new_diff(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if not review_request.is_mutable_by(request.user):
        return WebAPIResponseError(request, PERMISSION_DENIED)

    form_data = request.POST.copy()
    form = UploadDiffForm(review_request.repository, form_data, request.FILES)

    if not form.is_valid():
        return WebAPIResponseFormError(request, form)

    try:
        diffset = form.create(request.FILES['path'])

        # Set the initial revision to be one newer than the most recent
        # public revision, so we can reference it in the diff viewer.
        #
        # TODO: It would be nice to later consolidate this with the logic in
        #       DiffSet.save.
        public_diffsets = review_request.diffset_history.diffset_set

        if public_diffsets.count() > 0:
            diffset.revision = public_diffsets.latest().revision + 1
            diffset.save()
        else:
            diffset.revision = 1
    except scmtools.FileNotFoundError, e:
        return WebAPIResponseError(request, REPO_FILE_NOT_FOUND, {
            'file': e.path,
            'revision': e.revision
        })
    except EmptyDiffError, e:
        return WebAPIResponseError(request, INVALID_FORM_DATA, {
            'fields': {
                'path': [str(e)]
            }
        })
    except Exception, e:
        # This could be very wrong, but at least they'll see the error.
        # We probably want a new error type for this.
        return WebAPIResponseError(request, INVALID_FORM_DATA, {
            'fields': {
                'path': [str(e)]
            }
        })

    discarded_diffset = None

    try:
        draft = review_request.reviewrequestdraft_set.get()

        if draft.diffset and draft.diffset != diffset:
            discarded_diffset = draft.diffset
    except ReviewRequestDraft.DoesNotExist:
        draft = _prepare_draft(request, review_request)

    draft.diffset = diffset

    # We only want to add default reviewers the first time.  Was bug 318.
    if review_request.diffset_history.diffset_set.count() == 0:
        draft.add_default_reviewers();

    draft.save()

    if discarded_diffset:
        discarded_diffset.delete()

    # E-mail gets sent when the draft is saved.

    return WebAPIResponse(request, {'diffset_id': diffset.id})


@webapi_login_required
@require_POST
def new_screenshot(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if not review_request.is_mutable_by(request.user):
        return WebAPIResponseError(request, PERMISSION_DENIED)

    form_data = request.POST.copy()
    form = UploadScreenshotForm(form_data, request.FILES)

    if not form.is_valid():
        return WebAPIResponseFormError(request, form)

    try:
        screenshot = form.create(request.FILES['path'], review_request)
    except ValueError, e:
        return WebAPIResponseError(request, INVALID_FORM_DATA, {
            'fields': {
                'path': [str(e)],
            },
        })

    return WebAPIResponse(request, {'screenshot_id': screenshot.id})


@webapi_login_required
def diff_line_comments(request, review_request_id, line, diff_revision,
                       filediff_id, interdiff_revision=None,
                       interfilediff_id=None):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    filediff = get_object_or_404(FileDiff,
        pk=filediff_id, diffset__history=review_request.diffset_history,
        diffset__revision=diff_revision)

    if interdiff_revision is not None and interfilediff_id is not None:
        interfilediff = get_object_or_none(FileDiff,
            pk=interfilediff_id,
            diffset__history=review_request.diffset_history,
            diffset__revision=interdiff_revision)
    else:
        interfilediff = None

    if request.POST:
        num_lines = request.POST['num_lines']
        action = request.POST['action']

        # TODO: Sanity check the fields

        if action == "set":
            text = request.POST['text']

            review, review_is_new = Review.objects.get_or_create(
                review_request=review_request,
                user=request.user,
                public=False,
                base_reply_to__isnull=True)

            if review_is_new:
                review.save()

            if interfilediff:
                comment, comment_is_new = review.comments.get_or_create(
                    filediff=filediff,
                    interfilediff=interfilediff,
                    first_line=line)
            else:
                comment, comment_is_new = review.comments.get_or_create(
                    filediff=filediff,
                    interfilediff__isnull=True,
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
                public=False)

            try:
                q = Q(filediff=filediff, first_line=line)

                if interfilediff:
                    q = q & Q(interfilediff=interfilediff)
                else:
                    q = q & Q(interfilediff__isnull=True)

                comment = review.comments.get(q)
                comment.delete()
            except Comment.DoesNotExist:
                pass

            if review.body_top.strip() == "" and \
               review.body_bottom.strip() == "" and \
               review.comments.count() == 0 and \
               review.screenshot_comments.count() == 0:
                review.delete()
        else:
            return WebAPIResponseError(request, INVALID_ACTION,
                                     {'action': action})

    comments_query = filediff.comment_set.filter(
        Q(review__public=True) | Q(review__user=request.user),
        first_line=line)

    if interfilediff:
        comments_query = comments_query.filter(interfilediff=interfilediff)
    else:
        comments_query = comments_query.filter(interfilediff__isnull=True)

    return WebAPIResponse(request, {
        'comments': comments_query
    })


@webapi_login_required
def screenshot_comments(request, review_request_id, screenshot_id, x, y, w, h):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    screenshot = get_object_or_404(Screenshot, pk=screenshot_id)

    if request.POST:
        action = request.POST['action']

        # TODO: Sanity check the fields

        if action == "set":
            text = request.POST['text']
            review, review_is_new = Review.objects.get_or_create(
                review_request=review_request,
                user=request.user,
                public=False,
                base_reply_to__isnull=True)

            if review_is_new:
                review.save()

            comment, comment_is_new = review.screenshot_comments.get_or_create(
               screenshot=screenshot,
               x=x, y=y, w=w, h=h)

            comment.text = text
            comment.timestamp = datetime.now()
            comment.save()

            if comment_is_new:
                review.screenshot_comments.add(comment)
                review.save()
        elif action == "delete":
            review = get_object_or_404(Review,
                review_request=review_request,
                user=request.user,
                public=False)

            try:
                comment = review.screenshot_comments.get(screenshot=screenshot,
                                                         x=x, y=y, w=w, h=h)
                comment.delete()
            except ScreenshotComment.DoesNotExist:
                pass

            if review.body_top.strip() == "" and \
               review.body_bottom.strip() == "" and \
               review.comments.count() == 0 and \
               review.screenshot_comments.count() == 0:
                review.delete()
        else:
            return WebAPIResponseError(request, INVALID_ACTION,
                                       {'action': action})

    return WebAPIResponse(request, {
        'comments': screenshot.screenshotcomment_set.filter(
            Q(review__public=True) | Q(review__user=request.user),
            x=x, y=y, w=w, h=h)
    })
