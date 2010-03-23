from datetime import datetime
import logging
import os
import re

from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST

from djblets.siteconfig.models import SiteConfiguration
from djblets.util.misc import get_object_or_none
from djblets.webapi.core import WebAPIEncoder, WebAPIResponse, \
                                WebAPIResponseError, \
                                WebAPIResponseFormError
from djblets.webapi.decorators import webapi, \
                                      webapi_login_required, \
                                      webapi_permission_required
from djblets.webapi.errors import WebAPIError, \
                                  PERMISSION_DENIED, DOES_NOT_EXIST, \
                                  INVALID_ATTRIBUTE, INVALID_FORM_DATA, \
                                  NOT_LOGGED_IN, SERVICE_NOT_CONFIGURED

from reviewboard.accounts.models import Profile
from reviewboard.diffviewer.forms import EmptyDiffError
from reviewboard.diffviewer.models import FileDiff, DiffSet
from reviewboard.reviews.forms import UploadDiffForm, UploadScreenshotForm
from reviewboard.reviews.errors import PermissionError
from reviewboard.reviews.models import ReviewRequest, Review, Group, Comment, \
                                       ReviewRequestDraft, Screenshot, \
                                       ScreenshotComment
from reviewboard.scmtools.core import FileNotFoundError
from reviewboard.scmtools.errors import ChangeNumberInUseError, \
                                        EmptyChangeSetError, \
                                        InvalidChangeNumberError
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.decorators import webapi_check_login_required
from reviewboard.webapi.resources import commentResource, \
                                         diffSetResource, \
                                         fileDiffResource, \
                                         repositoryResource, \
                                         reviewDraftResource, \
                                         reviewGroupResource, \
                                         reviewRequestResource, \
                                         reviewRequestDraftResource, \
                                         reviewResource, \
                                         screenshotResource, \
                                         screenshotCommentResource


class ReviewBoardAPIEncoder(WebAPIEncoder):
    def encode(self, o, api_format, *args, **kwargs):
        resource = None

        if isinstance(o, Group):
            resource = reviewGroupResource
        elif isinstance(o, ReviewRequest):
            resource = reviewRequestResource
        elif isinstance(o, ReviewRequestDraft):
            resource = reviewRequestDraftResource
        elif isinstance(o, Review):
            resource = reviewResource
        elif isinstance(o, Comment):
            resource = commentResource
        elif isinstance(o, ScreenshotComment):
            resource = screenshotCommentResource
        elif isinstance(o, Screenshot):
            resource = screenshotResource
        elif isinstance(o, FileDiff):
            resource = fileDiffResource
        elif isinstance(o, DiffSet):
            resource = diffSetResource
        elif isinstance(o, Repository):
            resource = repositoryResource
        else:
            return super(ReviewBoardAPIEncoder, self).encode(o, *args, **kwargs)

        return resource.serialize_object(o, api_format=api_format)


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


@webapi
def service_not_configured(request):
    """
    Returns an error specifying that the service has not yet been configured.
    """
    return WebAPIResponseError(request, SERVICE_NOT_CONFIGURED)


@webapi_check_login_required
def review_request_last_update(request, review_request_id):
    """
    Returns the last update made to the specified review request.

    This does not take into account changes to a draft review request, as
    that's generally not update information that the owner of the draft is
    interested in.
    """
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if not review_request.is_accessible_by(request.user):
        return WebAPIResponseError(request, PERMISSION_DENIED)

    timestamp, updated_object = review_request.get_last_activity()
    user = None
    summary = None
    update_type = None

    if isinstance(updated_object, ReviewRequest):
        user = updated_object.submitter
        summary = _("Review request updated")
        update_type = "review-request"
    elif isinstance(updated_object, DiffSet):
        summary = _("Diff updated")
        update_type = "diff"
    elif isinstance(updated_object, Review):
        user = updated_object.user

        if updated_object.is_reply():
            summary = _("New reply")
            update_type = "reply"
        else:
            summary = _("New review")
            update_type = "review"
    else:
        # Should never be able to happen. The object will always at least
        # be a ReviewRequest.
        assert False

    return WebAPIResponse(request, {
        'timestamp': timestamp,
        'user': user,
        'summary': summary,
        'type': update_type,
    })


@webapi_check_login_required
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
def review_request_update_changenum(request, review_request_id, changenum):
    try:
        review_request = ReviewRequest.objects.get(pk=review_request_id)
        review_request.update_changenum(changenum, request.user)
    except ReviewRequest.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)
    except PermissionError:
        return HttpResponseForbidden()

    return WebAPIResponse(request)


@webapi_login_required
def review_request_updated(request, review_request_id):
    """
    Determines if a review has been updated since the user last viewed
    it.
    """
    try:
        review_request = ReviewRequest.objects.get(pk=review_request_id)
    except ReviewRequest.DoesNotExist:
        return WebAPIResponseError(request, DOES_NOT_EXIST)

    return WebAPIResponse(request, {
        'updated' : review_request.get_new_reviews(request.user).count() > 0
        })

@webapi_check_login_required
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


@webapi_check_login_required
def count_review_list(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    return WebAPIResponse(request, {
        'reviews': _get_reviews(review_request).count()
    })


@webapi_check_login_required
def review_comments_list(request, review_request_id, review_id):
    review = _get_and_validate_review(request, review_request_id, review_id)

    if isinstance(review, WebAPIResponseError):
        return review

    return WebAPIResponse(request, {
        'comments': review.comments.all(),
        'screenshot_comments': review.screenshot_comments.all(),
    })


@webapi_check_login_required
def count_review_comments(request, review_request_id, review_id):
    review = _get_and_validate_review(request, review_request_id, review_id)

    if isinstance(review, WebAPIResponseError):
        return review

    return WebAPIResponse(request, {'count': review.comments.count()})


def _prepare_draft(request, review_request):
    if not review_request.is_mutable_by(request.user):
        raise PermissionDenied
    return ReviewRequestDraft.create(review_request)


@webapi_login_required
@require_POST
def review_request_draft_update_from_changenum(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    try:
        draft = _prepare_draft(request, review_request)
    except PermissionDenied:
        return WebAPIResponseError(request, PERMISSION_DENIED)

    tool = review_request.repository.get_scmtool()
    changeset = tool.get_changeset(review_request.changenum)

    try:
        draft.update_from_changenum(review_request.changenum)
    except InvalidChangeNumberError:
        return WebAPIResponseError(request, INVALID_CHANGE_NUMBER,
                                 {'changenum': review_request.changenum})

    draft.save()
    review_request.reopen()

    return WebAPIResponse(request, {
        'draft': draft,
        'review_request': review_request,
    })


@webapi_login_required
def review_draft_comments(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    review = review_request.get_pending_review(request.user)

    if review:
        comments = review.comments.all()
        screenshot_comments = review.screenshot_comments.all()
    else:
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

    result = {}

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
                              interfilediff=context_comment.interfilediff,
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
        result['reply'] = None
        result['discarded'] = True
    else:
        reply.save()
        result['reply'] = reply

    return WebAPIResponse(request, result)

@webapi_login_required
@require_POST
def review_reply_draft_save(request, review_request_id, review_id):
    review = _get_and_validate_review(request, review_request_id, review_id)
    if isinstance(review, WebAPIResponseError):
        return review

    reply = review.get_pending_reply(request.user)

    if not reply:
        return WebAPIResponseError(request, DOES_NOT_EXIST)

    reply.publish(user=request.user)

    return WebAPIResponse(request)


@webapi_login_required
@require_POST
def review_reply_draft_discard(request, review_request_id, review_id):
    review = _get_and_validate_review(request, review_request_id, review_id)
    if isinstance(review, WebAPIResponseError):
        return review

    reply = review.get_pending_reply(request.user)

    if reply:
        reply.delete()
        return WebAPIResponse(request)
    else:
        return WebAPIResponseError(request, DOES_NOT_EXIST)


@webapi_check_login_required
def review_replies_list(request, review_request_id, review_id):
    review = _get_and_validate_review(request, review_request_id, review_id)
    if isinstance(review, WebAPIResponseError):
        return review

    return WebAPIResponse(request, {
        'replies': review.public_replies()
    })


@webapi_check_login_required
def count_review_replies(request, review_request_id, review_id):
    review = _get_and_validate_review(request, review_request_id, review_id)
    if isinstance(review, WebAPIResponseError):
        return review

    return WebAPIResponse(request, {
        'count': review.public_replies().count()
    })


@webapi_check_login_required
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
        if request.user.is_anonymous():
            return WebAPIResponseError(request, NOT_LOGGED_IN)

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
            review = review_request.get_pending_review(request.user)

            if not review:
                raise Http404()

            q = Q(filediff=filediff, first_line=line)

            if interfilediff:
                q = q & Q(interfilediff=interfilediff)
            else:
                q = q & Q(interfilediff__isnull=True)

            try:
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

    comments_query = filediff.comments.filter(
        Q(review__public=True) | Q(review__user=request.user),
        first_line=line)

    if interfilediff:
        comments_query = comments_query.filter(interfilediff=interfilediff)
    else:
        comments_query = comments_query.filter(interfilediff__isnull=True)

    return WebAPIResponse(request, {
        'comments': comments_query
    })


@webapi_check_login_required
def screenshot_comments(request, review_request_id, screenshot_id, x, y, w, h):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    screenshot = get_object_or_404(Screenshot, pk=screenshot_id)

    if request.POST:
        if request.user.is_anonymous():
            return WebAPIResponseError(request, NOT_LOGGED_IN)

        action = request.POST['action']

        # TODO: Sanity check the fields

        if action == "set":
            text = request.POST['text']
            review, review_is_new = Review.objects.get_or_create(
                review_request=review_request,
                user=request.user,
                public=False,
                base_reply_to__isnull=True)

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
            review = review_request.get_pending_review(request.user)

            if not review:
                raise Http404()

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
        'comments': screenshot.comments.filter(
            Q(review__public=True) | Q(review__user=request.user),
            x=x, y=y, w=w, h=h)
    })
