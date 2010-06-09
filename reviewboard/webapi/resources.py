from datetime import datetime
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.template.defaultfilters import timesince
from django.utils.translation import ugettext as _
from djblets.siteconfig.models import SiteConfiguration
from djblets.webapi.core import WebAPIResponseFormError, \
                                WebAPIResponsePaginated
from djblets.webapi.decorators import webapi_login_required, \
                                      webapi_permission_required, \
                                      webapi_request_fields
from djblets.webapi.errors import DOES_NOT_EXIST, INVALID_ATTRIBUTE, \
                                  INVALID_FORM_DATA, PERMISSION_DENIED
from djblets.webapi.resources import WebAPIResource as DjbletsWebAPIResource, \
                                     UserResource as DjbletsUserResource, \
                                     RootResource, register_resource_for_model

from reviewboard import get_version_string, get_package_version, is_release
from reviewboard.accounts.models import Profile
from reviewboard.reviews.forms import UploadDiffForm, UploadScreenshotForm
from reviewboard.reviews.models import Comment, DiffSet, FileDiff, Group, \
                                       Repository, ReviewRequest, \
                                       ReviewRequestDraft, Review, \
                                       ScreenshotComment, Screenshot
from reviewboard.scmtools.errors import ChangeNumberInUseError, \
                                        EmptyChangeSetError, \
                                        FileNotFoundError, \
                                        InvalidChangeNumberError
from reviewboard.webapi.decorators import webapi_check_login_required
from reviewboard.webapi.errors import INVALID_REPOSITORY, MISSING_REPOSITORY, \
                                      REPO_FILE_NOT_FOUND


class WebAPIResource(DjbletsWebAPIResource):
    """A specialization of the Djblets WebAPIResource for Review Board."""

    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        """Returns the serialized object for the resource.

        This will require login if anonymous access isn't enabled on the
        site.
        """
        return super(WebAPIResource, self).get(request, *args, **kwargs)

    @webapi_check_login_required
    def get_list(self, request, *args, **kwargs):
        """Returns a list of objects.

        This will require login if anonymous access isn't enabled on the
        site.

        If ``?counts-only=1`` is passed on the URL, then this will return
        only a ``count`` field with the number of entries, instead of the
        serialized objects.
        """
        if self.model and request.GET.get('counts-only', False):
            return 200, {
                'count': self.get_queryset(request, is_list=True,
                                           *args, **kwargs).count()
            }
        else:
            return super(WebAPIResource, self).get_list(request,
                                                        *args, **kwargs)


class BaseCommentResource(WebAPIResource):
    """Base class for diff comment resources.

    Provides common fields and functionality for all diff comment resources.
    """
    model = Comment
    name = 'diff_comment'
    fields = (
        'id', 'first_line', 'num_lines', 'text', 'filediff',
        'interfilediff', 'timestamp', 'timesince', 'public', 'user',
    )

    uri_object_key = 'comment_id'

    allowed_methods = ('GET',)

    def get_queryset(self, request, review_request_id, *args, **kwargs):
        """Returns a queryset for Comment models.

        This filters the query for comments on the specified review request
        which are either public or owned by the requesting user.
        """
        return self.model.objects.filter(
            Q(review__public=True) | Q(review__user=request.user),
            filediff__diffset__history__review_request=review_request_id)

    def serialize_public_field(self, obj):
        return obj.review.get().public

    def serialize_timesince_field(self, obj):
        return timesince(obj.timestamp)

    def serialize_user_field(self, obj):
        return obj.review.get().user


class FileDiffCommentResource(BaseCommentResource):
    """A resource representing diff comments inside a filediff resource.

    This resource is read-only, and only handles returning the list of
    comments. All comment creation is handled by ReviewCommentResource.
    """
    allowed_methods = ('GET',)
    model_parent_key = 'filediff'

    def get_queryset(self, request, review_request_id, diff_revision,
                     is_list=False, *args, **kwargs):
        """Returns a queryset for Comment models.

        This filters the query for comments on the specified review request
        and made on the specified diff revision, which are either public or
        owned by the requesting user.

        If the queryset is being used for a list of comment resources,
        then this can be further filtered by passing ``?interdiff_revision=``
        on the URL to match the given interdiff revision, and
        ``?line=`` to match comments on the given line number.
        """
        q = super(FileDiffCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        q = q.filter(filediff__diffset__revision=diff_revision)

        if is_list:
            if 'interdiff_revision' in request.GET:
                interdiff_revision = int(request.GET['interdiff_revision'])
                q = q.filter(
                    interfilediff__diffset__revision=interdiff_revision)

            if 'line' in request.GET:
                q = q.filter(first_line=int(request.GET['line']))

        return q

filediff_comment_resource = FileDiffCommentResource()


class ReviewCommentResource(BaseCommentResource):
    """A resource representing diff comments on a review."""
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model_parent_key = 'review'

    def get_queryset(self, request, review_request_id, review_id,
                     is_list=False, *args, **kwargs):
        """Returns a queryset for Comment models.

        This filters the query for comments on the particular review.

        If the queryset is being used for a list of comment resources,
        then this can be further filtered by passing ``?interdiff_revision=``
        on the URL to match the given interdiff revision, and
        ``?line=`` to match comments on the given line number.
        """
        q = super(ReviewCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        q = q.filter(review=review_id)

        if is_list:
            if 'interdiff_revision' in request.GET:
                interdiff_revision = int(request.GET['interdiff_revision'])
                q = q.filter(
                    interfilediff__diffset__revision=interdiff_revision)

            if 'line' in request.GET:
                q = q.filter(first_line=int(request.GET['line']))

        return q

    def has_delete_permissions(self, request, comment, *args, **kwargs):
        review = comment.review.get()
        return not review.public and review.user == request.user

    @webapi_login_required
    @webapi_request_fields(
        required = {
            'filediff_id': {
                'type': int,
                'description': 'The ID of the file diff the comment is on.',
            },
            'first_line': {
                'type': int,
                'description': 'The line number the comment starts at.',
            },
            'num_lines': {
                'type': int,
                'description': 'The number of lines the comment spans.',
            },
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
        },
        optional = {
            'interfilediff_id': {
                'type': int,
                'description': 'The ID of the second file diff in the '
                               'interdiff the comment is on.',
            },
        },
    )
    def create(self, request, first_line, num_lines, text,
               filediff_id, interfilediff_id=None, *args, **kwargs):
        """Creates a new diff comment.

        This will create a new diff comment on this review. The review
        must be a draft review.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_resource.has_modify_permissions(request, review):
            return PERMISSION_DENIED

        filediff = None
        interfilediff = None
        invalid_fields = {}

        try:
            filediff = FileDiff.objects.get(
                pk=filediff_id,
                diffset__history__review_request=review_request)
        except ObjectDoesNotExist:
            invalid_fields['filediff_id'] = \
                ['This is not a valid filediff ID']

        if filediff and interfilediff_id:
            if interfilediff_id == filediff.id:
                invalid_fields['interfilediff_id'] = \
                    ['This cannot be the same as filediff_id']
            else:
                try:
                    interfilediff = FileDiff.objects.get(
                        pk=interfilediff_id,
                        diffset__history=filediff.diffset.history)
                except ObjectDoesNotExist:
                    invalid_fields['interfilediff_id'] = \
                        ['This is not a valid interfilediff ID']

        if invalid_fields:
            return INVALID_FORM_DATA, {
                'fields': invalid_fields,
            }

        new_comment = self.model(filediff=filediff,
                                 interfilediff=interfilediff,
                                 text=text,
                                 first_line=first_line,
                                 num_lines=num_lines)
        new_comment.save()

        review.comments.add(new_comment)
        review.save()

        return 201, {
            self.item_result_key: new_comment,
        }

    @webapi_login_required
    @webapi_request_fields(
        optional = {
            'first_line': {
                'type': int,
                'description': 'The line number the comment starts at.',
            },
            'num_lines': {
                'type': int,
                'description': 'The number of lines the comment spans.',
            },
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates a diff comment.

        This can update the text or line range of an existing comment.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
            diff_comment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_resource.has_modify_permissions(request, review):
            return PERMISSION_DENIED

        for field in ('text', 'first_line', 'num_lines'):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(diff_comment, field, value)

        diff_comment.save()

        return 200, {
            self.item_result_key: diff_comment,
        }

review_comment_resource = ReviewCommentResource()


class ReviewReplyCommentResource(BaseCommentResource):
    """A resource representing diff comments on a reply to a review."""
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model_parent_key = 'review'

    def get_queryset(self, request, review_request_id, review_id, reply_id,
                     *args, **kwargs):
        q = super(ReviewReplyCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        q = q.filter(review=reply_id, review__base_reply_to=review_id)
        return q

    @webapi_login_required
    @webapi_request_fields(
        required = {
            'reply_to_id': {
                'type': int,
                'description': 'The ID of the comment being replied to.',
            },
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
        },
    )
    def create(self, request, reply_to_id, text, *args, **kwargs):
        """Creates a new diff comment on a reply.

        This will create a new diff comment on this reply. The reply
        must be a draft reply.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            reply = review_reply_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_reply_resource.has_modify_permissions(request, reply):
            return PERMISSION_DENIED

        try:
            comment = \
                review_comment_resource.get_object(request,
                                                   comment_id=reply_to_id,
                                                   *args, **kwargs)
        except ObjectDoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'reply_to_id': ['This is not a valid comment ID'],
                }
            }

        new_comment = self.model(filediff=comment.filediff,
                                 interfilediff=comment.interfilediff,
                                 reply_to=comment,
                                 text=text,
                                 first_line=comment.first_line,
                                 num_lines=comment.num_lines)
        new_comment.save()

        reply.comments.add(new_comment)
        reply.save()

        return 201, {
            self.item_result_key: new_comment,
        }

review_reply_comment_resource = ReviewReplyCommentResource()


class FileDiffResource(WebAPIResource):
    """A resource representing a file diff."""
    model = FileDiff
    name = 'file'
    fields = (
        'id', 'source_file', 'dest_file', 'source_revision', 'dest_detail',
    )
    item_child_resources = [filediff_comment_resource]

    uri_object_key = 'filediff_id'
    model_parent_key = 'diffset'

    def get_queryset(self, request, review_request_id, diff_revision,
                     *args, **kwargs):
        return self.model.objects.filter(
            diffset__history__review_request=review_request_id,
            diffset__revision=diff_revision)

filediff_resource = FileDiffResource()


class DiffSetResource(WebAPIResource):
    """A resource representing a set of file diffs."""
    model = DiffSet
    name = 'diff'
    fields = ('id', 'name', 'revision', 'timestamp', 'repository')
    item_child_resources = [filediff_resource]

    allowed_methods = ('GET', 'POST')

    uri_object_key = 'diff_revision'
    model_object_key = 'revision'
    model_parent_key = 'history'

    def get_queryset(self, request, review_request_id, *args, **kwargs):
        return self.model.objects.filter(
            history__review_request=review_request_id)

    def get_parent_object(self, diffset):
        history = diffset.history

        if history:
            return history.review_request.get()
        else:
            # This isn't in a history yet. It's part of a draft.
            return diffset.review_request_draft.get().review_request

    def has_access_permissions(self, request, diffset, *args, **kwargs):
        review_request = diffset.history.review_request.get()
        return review_request.is_accessible_by(request.user)

    @webapi_login_required
    def create(self, request, *args, **kwargs):
        """Creates a new diffset by parsing an uploaded diff file.

        This accepts a unified diff file, validates it, and stores it along
        with a draft of a review request.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return PERMISSION_DENIED

        form_data = request.POST.copy()
        form = UploadDiffForm(review_request, form_data, request.FILES)

        if not form.is_valid():
            return WebAPIResponseFormError(request, form)

        try:
            diffset = form.create(request.FILES['path'],
                                  request.FILES.get('parent_diff_path'))
        except FileNotFoundError, e:
            return REPO_FILE_NOT_FOUND, {
                'file': e.path,
                'revision': e.revision
            }
        except EmptyDiffError, e:
            return INVALID_FORM_DATA, {
                'fields': {
                    'path': [str(e)]
                }
            }
        except Exception, e:
            # This could be very wrong, but at least they'll see the error.
            # We probably want a new error type for this.
            logging.error("Error uploading new diff: %s", e, exc_info=1)

            return INVALID_FORM_DATA, {
                'fields': {
                    'path': [str(e)]
                }
            }

        discarded_diffset = None

        try:
            draft = review_request.draft.get()

            if draft.diffset and draft.diffset != diffset:
                discarded_diffset = draft.diffset
        except ReviewRequestDraft.DoesNotExist:
            try:
                draft = ReviewRequestDraftResource.prepare_draft(
                    request, review_request)
            except PermissionDenied:
                return PERMISSION_DENIED

        draft.diffset = diffset

        # We only want to add default reviewers the first time.  Was bug 318.
        if review_request.diffset_history.diffsets.count() == 0:
            draft.add_default_reviewers();

        draft.save()

        if discarded_diffset:
            discarded_diffset.delete()

        # E-mail gets sent when the draft is saved.

        return 201, {
            self.item_result_key: diffset,
        }

diffset_resource = DiffSetResource()


class BaseWatchedObjectResource(WebAPIResource):
    """A base resource for objects watched by a user."""
    watched_resource = None
    uri_object_key = 'watched_obj_id'
    profile_field = None

    allowed_methods = ('GET', 'POST', 'DELETE')

    @property
    def uri_object_key_regex(self):
        return self.watched_resource.uri_object_key_regex

    def get_queryset(self, request, username, *args, **kwargs):
        try:
            profile = Profile.objects.get(user__username=username)
            q = self.watched_resource.get_queryset(request, *args, **kwargs)
            q = q.filter(starred_by=profile)
            return q
        except Profile.DoesNotExist:
            return self.watched_resource.model.objects.none()

    @webapi_check_login_required
    def get(self, request, watched_obj_id, *args, **kwargs):
        try:
            q = self.get_queryset(request, *args, **kwargs)
            obj = q.get(pk=watched_obj_id)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        return HttpResponseRedirect(
            self.watched_resource.get_href(obj, request, *args, **kwargs))

    @webapi_check_login_required
    def get_list(self, request, *args, **kwargs):
        # TODO: Handle pagination and ?counts-only=1
        objects = [
            self.serialize_object(obj)
            for obj in self.get_queryset(request, is_list=True,
                                         *args, **kwargs)
        ]

        return 200, {
            self.list_result_key: objects,
        }

    @webapi_login_required
    @webapi_request_fields(required={
        'object_id': {
            'type': str,
            'description': 'The ID of the object to watch.',
        },
    })
    def create(self, request, object_id, *args, **kwargs):
        try:
            obj = self.watched_resource.get_object(request, **dict({
                self.watched_resource.uri_object_key: object_id,
            }))
            user = user_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not user_resource.has_modify_permissions(request, user,
                                                   *args, **kwargs):
            return PERMISSION_DENIED

        profile, profile_is_new = \
            Profile.objects.get_or_create(user=request.user)
        getattr(profile, self.profile_field).add(obj)
        profile.save()

        return 201, {
            self.item_result_key: obj,
        }

    @webapi_login_required
    def delete(self, request, watched_obj_id, *args, **kwargs):
        try:
            obj = self.watched_resource.get_object(request, **dict({
                self.watched_resource.uri_object_key: watched_obj_id,
            }))
            user = user_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not user_resource.has_modify_permissions(request, user,
                                                   *args, **kwargs):
            return PERMISSION_DENIED

        profile, profile_is_new = \
            Profile.objects.get_or_create(user=request.user)

        if not profile_is_new:
            getattr(profile, self.profile_field).remove(obj)
            profile.save()

        return 204, {}

    def serialize_object(self, obj, *args, **kwargs):
        return {
            'id': obj.pk,
            self.item_result_key: obj,
        }


class WatchedReviewGroupResource(BaseWatchedObjectResource):
    """A resource for review groups watched by a user."""
    name = 'watched_review_group'
    uri_name = 'review-groups'
    profile_field = 'starred_groups'

    @property
    def watched_resource(self):
        """Return the watched resource.

        This is implemented as a property in order to work around
        a circular reference issue.
        """
        return review_group_resource

watched_review_group_resource = WatchedReviewGroupResource()


class WatchedReviewRequestResource(BaseWatchedObjectResource):
    """A resource for review requests watched by a user."""
    name = 'watched_review_request'
    uri_name = 'review-requests'
    profile_field = 'starred_review_requests'

    @property
    def watched_resource(self):
        """Return the watched resource.

        This is implemented as a property in order to work around
        a circular reference issue.
        """
        return review_request_resource

watched_review_request_resource = WatchedReviewRequestResource()


class WatchedResource(WebAPIResource):
    """A resource for types of things watched by a user."""
    name = 'watched'
    name_plural = 'watched'

    list_child_resources = [
        watched_review_group_resource,
        watched_review_request_resource,
    ]

watched_resource = WatchedResource()


class UserResource(DjbletsUserResource):
    """A resource representing user accounts."""
    item_child_resources = [
        watched_resource,
    ]

    def get_queryset(self, request, *args, **kwargs):
        search_q = request.GET.get('q', None)

        query = self.model.objects.filter(is_active=True)

        if search_q:
            q = Q(username__istartswith=search_q)

            if request.GET.get('fullname', None):
                q = q | (Q(first_name__istartswith=query) |
                         Q(last_name__istartswith=query))

            query = query.filter(q)

        return query

user_resource = UserResource()


class ReviewGroupUserResource(UserResource):
    """A resource representing users in a review group."""
    def get_queryset(self, request, group_name, *args, **kwargs):
        return self.model.objects.filter(review_groups__name=group_name)

review_group_user_resource = ReviewGroupUserResource()


class ReviewGroupResource(WebAPIResource):
    """A resource representing review groups."""
    model = Group
    fields = ('id', 'name', 'display_name', 'mailing_list', 'url')
    item_child_resources = [
        review_group_user_resource
    ]

    uri_object_key = 'group_name'
    uri_object_key_regex = '[A-Za-z0-9_-]+'
    model_object_key = 'name'

    allowed_methods = ('GET', 'PUT')

    def get_queryset(self, request, *args, **kwargs):
        search_q = request.GET.get('q', None)

        query = self.model.objects.all()

        if search_q:
            q = Q(name__istartswith=search_q)

            if request.GET.get('displayname', None):
                q = q | Q(display_name__istartswith=search_q)

            query = query.filter(q)

        return query

    def serialize_url_field(self, group):
        return group.get_absolute_url()

review_group_resource = ReviewGroupResource()


class RepositoryInfoResource(WebAPIResource):
    """A resource representing server-side information on a repository."""
    name = 'info'
    name_plural = 'info'
    allowed_methods = ('GET',)

    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        """Returns repository-specific information from a server."""
        try:
            repository = repository_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        try:
            return 200, {
                self.item_result_key: repository.get_scmtool().get_repository_info()
            }
        except NotImplementedError:
            return REPO_NOT_IMPLEMENTED
        except:
            return REPO_INFO_ERROR

repository_info_resource = RepositoryInfoResource()


class RepositoryResource(WebAPIResource):
    """A resource representing a repository."""
    model = Repository
    name_plural = 'repositories'
    fields = ('id', 'name', 'path', 'tool')
    uri_object_key = 'repository_id'
    item_child_resources = [repository_info_resource]

    allowed_methods = ('GET',)

    @webapi_check_login_required
    def get_queryset(self, request, *args, **kwargs):
        return self.model.objects.filter(visible=True)

    def serialize_tool_field(self, obj):
        return obj.tool.name

repository_resource = RepositoryResource()


class BaseScreenshotResource(WebAPIResource):
    """A base resource representing screenshots."""
    model = Screenshot
    name = 'screenshot'
    fields = ('id', 'caption', 'path', 'thumbnail_url')

    uri_object_key = 'screenshot_id'

    def get_queryset(self, request, review_request_id, *args, **kwargs):
        return self.model.objects.filter(review_request=review_request_id)

    def serialize_path_field(self, obj):
        return obj.image.name

    def serialize_thumbnail_url_field(self, obj):
        return obj.get_thumbnail_url()

    @webapi_login_required
    def create(self, request, *args, **kwargs):
        """Creates a new screenshot from an uploaded file.

        This accepts any standard image format (PNG, GIF, JPEG) and associates
        it with a draft of a review request.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return PERMISSION_DENIED

        form_data = request.POST.copy()
        form = UploadScreenshotForm(form_data, request.FILES)

        if not form.is_valid():
            return WebAPIResponseFormError(request, form)

        try:
            screenshot = form.create(request.FILES['path'], review_request)
        except ValueError, e:
            return INVALID_FORM_DATA, {
                'fields': {
                    'path': [str(e)],
                },
            }

        return 201, {
            self.item_result_key: screenshot,
        }

    @webapi_login_required
    @webapi_request_fields(
        optional={
            'caption': {
                'type': str,
                'description': 'The new caption for the screenshot.',
            },
        }
    )
    def update(self, request, caption=None, *args, **kwargs):
        """Updates the screenshot's data.

        This allows updating the screenshot in a draft. The caption, currently,
        is the only thing that can be updated.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            screenshot = screenshot_resource.get_object(request, *args,
                                                        **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return PERMISSION_DENIED

        try:
            draft = review_request_draft_resource.prepare_draft(request,
                                                                review_request)
        except PermissionDenied:
            return PERMISSION_DENIED

        screenshot.draft_caption = caption
        screenshot.save()

        return 200, {
            self.item_result_key: screenshot,
        }


class ScreenshotDraftResource(BaseScreenshotResource):
    """A resource representing drafts of screenshots."""
    name = 'draft-screenshot'
    uri_name = 'screenshots'
    model_parent_key = 'drafts'
    allowed_methods = ('GET', 'POST', 'PUT',)

    def get_queryset(self, request, review_request_id, *args, **kwargs):
        try:
            draft = review_request_draft_resource.get_object(
                request, review_request_id, *args, **kwargs)

            inactive_ids = \
                draft.inactive_screenshots.values_list('pk', flat=True)

            q = Q(review_request=review_request_id) | Q(drafts=draft)
            query = self.model.objects.filter(q)
            query = query.exclude(pk__in=inactive_ids)
            return query
        except ObjectDoesNotExist:
            return self.model.objects.none()

    def serialize_caption_field(self, obj):
        return obj.draft_caption

    def get_list(self, request, *args, **kwargs):
        """Returns a list of draft screenshots.

        This is a specialized version of the standard ``get_list`` function
        that uses this resource to serialize the children, in order to
        guarantee that we'll be able to identify them as screenshots part
        of the draft.
        """
        # TODO: Handle ?counts-only=1
        return WebAPIResponsePaginated(
            request,
            queryset=self.get_queryset(request, is_list=True,
                                       *args, **kwargs),
            results_key=self.list_result_key,
            serialize_object_func=
                lambda obj: self.serialize_object(obj, request=request,
                                                  *args, **kwargs),
            extra_data={
                'links': self.get_links(self.list_child_resources,
                                        request=request, *args, **kwargs),
            })

screenshot_draft_resource = ScreenshotDraftResource()


class ReviewRequestDraftResource(WebAPIResource):
    """A resource representing drafts of review requests."""
    model = ReviewRequestDraft
    name = 'draft'
    name_plural = 'draft'
    model_parent_key = 'review_request'
    mutable_fields = (
        'branch', 'bugs_closed', 'changedescription', 'description',
        'public', 'summary', 'target_groups', 'target_people', 'testing_done'
    )
    fields = ('id', 'review_request', 'last_updated') + mutable_fields
    singleton = True

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    item_child_resources = [
        screenshot_draft_resource,
    ]

    @classmethod
    def prepare_draft(self, request, review_request):
        """Creates a draft, if the user has permission to."""
        if not review_request.is_mutable_by(request.user):
            raise PermissionDenied

        return ReviewRequestDraft.create(review_request)

    def get_queryset(self, request, review_request_id, *args, **kwargs):
        return self.model.objects.filter(review_request=review_request_id)

    def serialize_bugs_closed_field(self, obj):
        return obj.get_bug_list()

    def serialize_changedescription_field(self, obj):
        if obj.changedesc:
            return obj.changedesc.text
        else:
            return ''

    def serialize_status_field(self, obj):
        return status_to_string(obj.status)

    def serialize_public_field(self, obj):
        return False

    def has_delete_permissions(self, request, draft, *args, **kwargs):
        return draft.review_request.is_mutable_by(request.user)

    @webapi_login_required
    @webapi_request_fields(
        optional={
            'branch': {
                'type': str,
                'description': 'The new branch name.',
            },
            'bugs_closed': {
                'type': str,
                'description': 'A comma-separated list of bug IDs.',
            },
            'changedescription': {
                'type': str,
                'description': 'The change description for this update.',
            },
            'description': {
                'type': str,
                'description': 'The new review request description.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the review public. '
                               'If a review is public, it cannot be made '
                               'private again.',
            },
            'summary': {
                'type': str,
                'description': 'The new review request summary.',
            },
            'target_groups': {
                'type': str,
                'description': 'A comma-separated list of review groups '
                               'that will be on the reviewer list.',
            },
            'target_people': {
                'type': str,
                'description': 'A comma-separated list of users that will '
                               'be on a reviewer list.',
            },
            'testing_done': {
                'type': str,
                'description': 'The new testing done text.',
            },
        },
    )
    def create(self, *args, **kwargs):
        """Creates a draft of a review request.

        If a draft already exists, this will just reuse the existing draft.
        """
        # A draft is a singleton. Creating and updating it are the same
        # operations in practice.
        result = self.update(*args, **kwargs)

        if isinstance(result, tuple):
            if result[0] == 200:
                return (201,) + result[1:]

        return result

    @webapi_login_required
    @webapi_request_fields(
        optional={
            'branch': {
                'type': str,
                'description': 'The new branch name.',
            },
            'bugs_closed': {
                'type': str,
                'description': 'A comma-separated list of bug IDs.',
            },
            'changedescription': {
                'type': str,
                'description': 'The change description for this update.',
            },
            'description': {
                'type': str,
                'description': 'The new review request description.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the review public. '
                               'If a review is public, it cannot be made '
                               'private again.',
            },
            'summary': {
                'type': str,
                'description': 'The new review request summary.',
            },
            'target_groups': {
                'type': str,
                'description': 'A comma-separated list of review groups '
                               'that will be on the reviewer list.',
            },
            'target_people': {
                'type': str,
                'description': 'A comma-separated list of users that will '
                               'be on a reviewer list.',
            },
            'testing_done': {
                'type': str,
                'description': 'The new testing done text.',
            },
        },
    )
    def update(self, request, always_save=False, *args, **kwargs):
        """Updates a draft of a review request.

        This will update the draft with the newly provided data.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        try:
            draft = self.prepare_draft(request, review_request)
        except PermissionDenied:
            return PERMISSION_DENIED

        modified_objects = []
        invalid_fields = {}

        for field_name in self.mutable_fields:
            if kwargs.get(field_name, None) is not None:
                field_result, field_modified_objects, invalid = \
                    self._set_draft_field_data(draft, field_name,
                                               kwargs[field_name])

                if invalid:
                    invalid_fields[field_name] = invalid
                elif field_modified_objects:
                    modified_objects += field_modified_objects

        if always_save or not invalid_fields:
            for obj in modified_objects:
                obj.save()

            draft.save()

        if invalid_fields:
            return INVALID_FORM_DATA, {
                'fields': invalid_fields,
            }

        if request.POST.get('public', False):
            review_request.publish(user=request.user)

            return 303, {}, {
                'Location': review_request_resource.get_href(
                    review_request, request, *args, **kwargs)
            }
        else:
            return 200, {
                self.item_result_key: draft,
            }

    @webapi_login_required
    def delete(self, request, review_request_id, *args, **kwargs):
        """Deletes a draft of a review request."""
        # Make sure this exists. We don't want to use prepare_draft, or
        # we'll end up creating a new one.
        try:
            draft = ReviewRequestDraft.objects.get(
                review_request=review_request_id)
        except ReviewRequestDraft.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, draft, *args, **kwargs):
            return PERMISSION_DENIED

        draft.delete()

        return 204, {}

    def _set_draft_field_data(self, draft, field_name, data):
        """Sets a field on a draft.

        This will update a draft's field based on the provided data.
        It handles transforming the data as necessary to put it into
        the field.

        if there is a problem with the data, then a validation error
        is returned.

        This returns a tuple of (data, modified_objects, invalid_entries).

        ``data`` is the transformed data.

        ``modified_objects`` is a list of objects (screenshots or change
        description) that were affected.

        ``invalid_entries`` is a list of validation errors.
        """
        result = None
        modified_objects = []
        invalid_entries = []

        if field_name in ('target_groups', 'target_people'):
            values = re.split(r",\s*", data)
            target = getattr(draft, field_name)
            target.clear()

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
                        obj = self._find_user(username=value)

                    target.add(obj)
                except:
                    invalid_entries.append(value)

            result = target.all()
        elif field_name == 'bugs_closed':
            data = list(self._sanitize_bug_ids(data))
            setattr(draft, field_name, ','.join(data))
            result = data
        elif field_name == 'changedescription':
            if not draft.changedesc:
                invalid_entries.append('Change descriptions cannot be used '
                                       'for drafts of new review requests')
            else:
                draft.changedesc.text = data

                modified_objects.append(draft.changedesc)
                result = data
        else:
            if field_name == 'summary' and '\n' in data:
                invalid_entries.append('Summary cannot contain newlines')
            else:
                setattr(draft, field_name, data)
                result = data

        return data, modified_objects, invalid_entries

    def _sanitize_bug_ids(self, entries):
        """Sanitizes bug IDs.

        This will remove any excess whitespace before or after the bug
        IDs, and remove any leading ``#`` characters.
        """
        for bug in entries.split(','):
            bug = bug.strip()

            if bug:
                # RB stores bug numbers as numbers, but many people have the
                # habit of prepending #, so filter it out:
                if bug[0] == '#':
                    bug = bug[1:]

                yield bug

    def _find_user(self, username):
        """Finds a User object matching ``username``.

        This will search all authentication backends, and may create the
        User object if the authentication backend knows that the user exists.
        """
        username = username.strip()

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

review_request_draft_resource = ReviewRequestDraftResource()


class BaseScreenshotCommentResource(WebAPIResource):
    """A base resource for screenshot comments."""
    model = ScreenshotComment
    name = 'screenshot_comment'
    fields = (
        'id', 'screenshot', 'timestamp', 'timesince',
        'public', 'user', 'text', 'x', 'y', 'w', 'h',
    )

    uri_object_key = 'comment_id'

    allowed_methods = ('GET',)

    def get_queryset(self, request, review_request_id, *args, **kwargs):
        return self.model.objects.filter(
            screenshot__review_request=review_request_id,
            review__isnull=False)

    def serialize_public_field(self, obj):
        return obj.review.get().public

    def serialize_timesince_field(self, obj):
        return timesince(obj.timestamp)

    def serialize_user_field(self, obj):
        return obj.review.get().user


class ScreenshotCommentResource(BaseScreenshotCommentResource):
    """A resource representing a comment on a screenshot."""
    model_parent_key = 'screenshot'

    def get_queryset(self, request, review_request_id, screenshot_id,
                     *args, **kwargs):
        q = super(ScreenshotCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        q = q.filter(screenshot=screenshot_id)
        return q

screenshot_comment_resource = ScreenshotCommentResource()


class ReviewScreenshotCommentResource(BaseScreenshotCommentResource):
    """A resource representing a screenshot comment on a review."""
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model_parent_key = 'review'

    def get_queryset(self, request, review_request_id, review_id,
                     *args, **kwargs):
        q = super(ReviewScreenshotCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        return q.filter(review=review_id)

    def has_delete_permissions(self, request, comment, *args, **kwargs):
        review = comment.review.get()
        return not review.public and review.user == request.user

    @webapi_login_required
    @webapi_request_fields(
        required = {
            'screenshot_id': {
                'type': int,
                'description': 'The ID of the screenshot being commented on.',
            },
            'x': {
                'type': int,
                'description': 'The X location for the comment.',
            },
            'y': {
                'type': int,
                'description': 'The Y location for the comment.',
            },
            'w': {
                'type': int,
                'description': 'The width of the comment region.',
            },
            'h': {
                'type': int,
                'description': 'The height of the comment region.',
            },
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
        },
    )
    def create(self, request, screenshot_id, x, y, w, h, text,
               *args, **kwargs):
        """Creates a screenshot comment on a review.

        This will create a new comment on a screenshot as part of a review.
        The comment contains text and dimensions for the area being commented
        on.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_resource.has_modify_permissions(request, review):
            return PERMISSION_DENIED

        try:
            screenshot = Screenshot.objects.get(pk=screenshot_id,
                                                review_request=review_request)
        except ObjectDoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'screenshot_id': ['This is not a valid screenshot ID'],
                }
            }

        new_comment = self.model(screenshot=screenshot, x=x, y=y, w=w, h=h,
                                 text=text)
        new_comment.save()

        review.screenshot_comments.add(new_comment)
        review.save()

        return 201, {
            self.item_result_key: new_comment,
        }

review_screenshot_comment_resource = ReviewScreenshotCommentResource()


class ReviewReplyScreenshotCommentResource(BaseScreenshotCommentResource):
    """A resource representing screenshot comments on a reply to a review."""
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model_parent_key = 'review'

    def get_queryset(self, request, review_request_id, review_id, reply_id,
                     *args, **kwargs):
        q = super(ReviewReplyScreenshotCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        q = q.filter(review=reply_id, review__base_reply_to=review_id)
        return q

    @webapi_login_required
    @webapi_request_fields(
        required = {
            'reply_to_id': {
                'type': int,
                'description': 'The ID of the comment being replied to.',
            },
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
        },
    )
    def create(self, request, reply_to_id, text, *args, **kwargs):
        """Creates a reply to a screenshot comment on a review.

        This will create a reply to a screenshot comment on a review.
        The new comment will contain the same dimensions of the comment
        being replied to, but may contain new text.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            reply = review_reply_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_reply_resource.has_modify_permissions(request, reply):
            return PERMISSION_DENIED

        try:
            comment = review_screenshot_comment_resource.get_object(
                request,
                comment_id=reply_to_id,
                *args, **kwargs)
        except ObjectDoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'reply_to_id': ['This is not a valid screenshot '
                                    'comment ID'],
                }
            }

        new_comment = self.model(screenshot=comment.screenshot,
                                 x=comment.x,
                                 y=comment.y,
                                 w=comment.w,
                                 h=comment.h,
                                 text=text)
        new_comment.save()

        reply.screenshot_comments.add(new_comment)
        reply.save()

        return 201, {
            self.item_result_key: new_comment,
        }

review_reply_screenshot_comment_resource = \
    ReviewReplyScreenshotCommentResource()


class BaseReviewResource(WebAPIResource):
    """Base class for review resources.

    Provides common fields and functionality for all review resources.
    """
    model = Review
    fields = (
        'id', 'user', 'timestamp', 'public', 'comments',
        'ship_it', 'body_top', 'body_bottom'
    )

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def get_queryset(self, request, review_request_id, is_list=False,
                     *args, **kwargs):
        q = Q(review_request=review_request_id) & \
            Q(**self.get_base_reply_to_field(*args, **kwargs))

        if is_list:
            # We don't want to show drafts in the list.
            q = q & Q(public=True)

        return self.model.objects.filter(q)

    def get_base_reply_to_field(self):
        raise NotImplemented

    def has_access_permissions(self, request, review, *args, **kwargs):
        return review.public or review.user == request.user

    def has_modify_permissions(self, request, review, *args, **kwargs):
        return not review.public and review.user == request.user

    def has_delete_permissions(self, request, review, *args, **kwargs):
        return not review.public and review.user == request.user

    @webapi_login_required
    @webapi_request_fields(
        optional = {
            'ship_it': {
                'type': bool,
                'description': 'Whether or not to mark the review "Ship It!"',
            },
            'body_top': {
                'type': str,
                'description': 'The review content above the comments.',
            },
            'body_bottom': {
                'type': str,
                'description': 'The review content below the comments.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the review public. '
                               'If a review is public, it cannot be made '
                               'private again.',
            },
        },
    )
    def create(self, request, *args, **kwargs):
        """Creates a review.

        This creates a new review on a review request. The review is a
        draft and only the author will be able to see it until it is
        published.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        review, is_new = Review.objects.get_or_create(
            review_request=review_request,
            user=request.user,
            public=False,
            **self.get_base_reply_to_field(*args, **kwargs))

        if is_new:
            status_code = 201 # Created
        else:
            # This already exists. Go ahead and update, but we're going to
            # redirect the user to the right place.
            status_code = 303 # See Other

        result = self._update_review(request, review, *args, **kwargs)

        if not isinstance(result, tuple) or result[0] != 200:
            return result
        else:
            return status_code, result[1], {
                'Location': self.get_href(review, request, *args, **kwargs),
            }

    @webapi_login_required
    @webapi_request_fields(
        optional = {
            'ship_it': {
                'type': bool,
                'description': 'Whether or not to mark the review "Ship It!"',
            },
            'body_top': {
                'type': str,
                'description': 'The review content above the comments.',
            },
            'body_bottom': {
                'type': str,
                'description': 'The review content below the comments.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the review public. '
                               'If a review is public, it cannot be made '
                               'private again.',
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates a review.

        This updates the fields of a draft review. Published reviews cannot
        be updated.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        return self._update_review(request, review, *args, **kwargs)

    def _update_review(self, request, review, public=None, *args, **kwargs):
        """Common function to update fields on a draft review."""
        if not self.has_modify_permissions(request, review):
            # Can't modify published reviews or those not belonging
            # to the user.
            return PERMISSION_DENIED

        for field in ('ship_it', 'body_top', 'body_bottom'):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(review, field, value)

        review.save()

        if public:
            review.publish(user=request.user)

        return 200, {
            self.item_result_key: review,
        }


class ReviewReplyDraftResource(WebAPIResource):
    """A redirecting resource that points to the current draft reply."""
    name = 'reply_draft'
    name_plural = 'reply_draft'
    uri_name = 'draft'

    @webapi_login_required
    def get(self, request, *args, **kwargs):
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
            reply = review.get_pending_reply(request.user)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not reply:
            return DOES_NOT_EXIST

        return 301, {}, {
            'Location': review_reply_resource.get_href(reply, request,
                                                       *args, **kwargs),
        }

review_reply_draft_resource = ReviewReplyDraftResource()


class ReviewReplyResource(BaseReviewResource):
    """A resource representing a reply to a review."""
    model = Review
    name = 'reply'
    name_plural = 'replies'
    fields = (
        'id', 'user', 'timestamp', 'public', 'comments', 'body_top',
        'body_bottom'
    )

    item_child_resources = [
        review_reply_comment_resource,
        review_reply_screenshot_comment_resource,
    ]

    list_child_resources = [
        review_reply_draft_resource,
    ]

    uri_object_key = 'reply_id'
    model_parent_key = 'base_reply_to'

    def get_base_reply_to_field(self, review_id, *args, **kwargs):
        return {
            'base_reply_to': Review.objects.get(pk=review_id),
        }

    @webapi_login_required
    @webapi_request_fields(
        optional = {
            'body_top': {
                'type': str,
                'description': 'The response to the review content above '
                               'the comments.',
            },
            'body_bottom': {
                'type': str,
                'description': 'The response to the review content below '
                               'the comments.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the reply public. '
                               'If a reply is public, it cannot be made '
                               'private again.',
            },
        },
    )
    def create(self, request, *args, **kwargs):
        """Creates a reply to a review.

        This creates a new reply to a review. The reply is a draft and
        only the author will be able to see it until it is published.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        reply, is_new = Review.objects.get_or_create(
            review_request=review_request,
            user=request.user,
            public=False,
            base_reply_to=review)

        if is_new:
            status_code = 201 # Created
        else:
            # This already exists. Go ahead and update, but we're going to
            # redirect the user to the right place.
            status_code = 303 # See Other

        result = self._update_reply(request, reply, *args, **kwargs)

        if not isinstance(result, tuple) or result[0] != 200:
            return result
        else:
            return status_code, result[1], {
                'Location': self.get_href(reply, request, *args, **kwargs),
            }

    @webapi_login_required
    @webapi_request_fields(
        optional = {
            'body_top': {
                'type': str,
                'description': 'The response to the review content above '
                               'the comments.',
            },
            'body_bottom': {
                'type': str,
                'description': 'The response to the review content below '
                               'the comments.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the reply public. '
                               'If a reply is public, it cannot be made '
                               'private again.',
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates a reply.

        This updates the fields of a draft reply. Published replies cannot
        be updated.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
            reply = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        return self._update_reply(request, reply, *args, **kwargs)

    def _update_reply(self, request, reply, public=None, *args, **kwargs):
        """Common function to update fields on a draft reply."""
        if not self.has_modify_permissions(request, reply):
            # Can't modify published replies or those not belonging
            # to the user.
            return PERMISSION_DENIED

        invalid_fields = {}

        for field in ('body_top', 'body_bottom'):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(reply, field, value)

                if value == '':
                    reply_to = None
                else:
                    reply_to = reply.base_reply_to

                setattr(reply, '%s_reply_to' % field, reply_to)

        if public:
            reply.publish(user=request.user)
        else:
            reply.save()

        return 200, {
            self.item_result_key: reply,
        }

review_reply_resource = ReviewReplyResource()


class ReviewDraftResource(WebAPIResource):
    """A redirecting resource that points to the current draft review."""
    name = 'review_draft'
    name_plural = 'review_draft'
    uri_name = 'draft'

    @webapi_login_required
    def get(self, request, *args, **kwargs):
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            review = review_request.get_pending_review(request.user)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review:
            return DOES_NOT_EXIST

        return 301, {}, {
            'Location': review_resource.get_href(review, request,
                                                 *args, **kwargs),
        }

review_draft_resource = ReviewDraftResource()


class ReviewResource(BaseReviewResource):
    """A resource representing a review on a review request."""
    uri_object_key = 'review_id'
    model_parent_key = 'review_request'

    item_child_resources = [
        review_comment_resource,
        review_reply_resource,
        review_screenshot_comment_resource,
    ]

    list_child_resources = [
        review_draft_resource,
    ]

    def get_base_reply_to_field(self, *args, **kwargs):
        return {
            'base_reply_to__isnull': True,
        }

review_resource = ReviewResource()


class ScreenshotResource(BaseScreenshotResource):
    """A resource representing a screenshot on a review request."""
    model_parent_key = 'review_request'

    item_child_resources = [
        screenshot_comment_resource,
    ]

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

screenshot_resource = ScreenshotResource()


class ReviewRequestLastUpdateResource(WebAPIResource):
    """A resource representing the last update to a review request."""
    name = 'last_update'
    name_plural = 'last_update'

    allowed_methods = ('GET',)

    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        """Returns the last update made to the review request.

        This does not take into account changes to a draft review request, as
        that's generally not update information that the owner of the draft is
        interested in.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request_resource.has_access_permissions(request,
                                                              review_request):
            return PERMISSION_DENIED

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

        return 200, {
            self.item_result_key: {
                'timestamp': timestamp,
                'user': user,
                'summary': summary,
                'type': update_type,
            }
        }

review_request_last_update_resource = ReviewRequestLastUpdateResource()


class ReviewRequestResource(WebAPIResource):
    """A resource representing a review request."""
    model = ReviewRequest
    name = 'review_request'
    fields = (
        'id', 'submitter', 'time_added', 'last_updated', 'status',
        'public', 'changenum', 'repository', 'summary', 'description',
        'testing_done', 'bugs_closed', 'branch', 'target_groups',
        'target_people',
    )
    uri_object_key = 'review_request_id'
    item_child_resources = [
        diffset_resource,
        review_request_draft_resource,
        review_request_last_update_resource,
        review_resource,
        screenshot_resource,
    ]

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    _close_type_map = {
        'submitted': ReviewRequest.SUBMITTED,
        'discarded': ReviewRequest.DISCARDED,
    }

    def get_queryset(self, request, is_list=False, *args, **kwargs):
        """Returns a queryset for ReviewRequest models.

        By default, this returns all published or formerly published
        review requests.

        If the queryset is being used for a list of review request
        resources, then it can be further filtered by one or more of the
        following arguments in the URL:

          * ``changenum`` - The change number the review requests must be
                            against. This will only return one review request
                            per repository, and only works for repository
                            types that support server-side changesets.
          * ``from-user`` - The username that the review requests must be
                            owned by.
          * ``repository`` - The ID of the repository that the review requests
                             must be on.
          * ``status`` - The status of the review requests. This can be
                         ``pending``, ``submitted`` or ``discarded``.
          * ``to-groups`` - A comma-separated list of review group names that
                            the review requests must have in the reviewer
                            list.
          * ``to-user-groups`` - A comma-separated list of usernames who
                                 are in groups that the review requests
                                 must have in the reviewer list.
          * ``to-users`` - A comma-separated list of usernames that the
                           review requests must either have in the reviewer
                           list specifically or by way of a group.
          * ``to-users-directly`` - A comma-separated list of usernames that
                                    the review requests must have in the
                                    reviewer list specifically.
        """
        q = Q()

        if is_list:
            if 'to-groups' in request.GET:
                for group_name in request.GET.get('to-groups').split(','):
                    q = q & self.model.objects.get_to_group_query(group_name)

            if 'to-users' in request.GET:
                for username in request.GET.get('to-users').split(','):
                    q = q & self.model.objects.get_to_user_query(username)

            if 'to-users-directly' in request.GET:
                for username in request.GET.get('to-users-directly').split(','):
                    q = q & self.model.objects.get_to_user_directly_query(
                        username)

            if 'to-users-groups' in request.GET:
                for username in request.GET.get('to-users-groups').split(','):
                    q = q & self.model.objects.get_to_user_groups_query(
                        username)

            if 'from-user' in request.GET:
                q = q & self.model.objects.get_from_user_query(
                    request.GET.get('from-user'))

            if 'repository' in request.GET:
                q = q & Q(repository=int(request.GET.get('repository')))

            if 'changenum' in request.GET:
                q = q & Q(changenum=int(request.GET.get('changenum')))

            status = string_to_status(request.GET.get('status', 'pending'))

            return self.model.objects.public(user=request.user, status=status,
                                             extra_query=q)
        else:
            return self.model.objects.all()

    def has_access_permissions(self, request, review_request, *args, **kwargs):
        return review_request.is_accessible_by(request.user)

    def has_delete_permissions(self, request, review_request, *args, **kwargs):
        return request.user.has_perm('reviews.delete_reviewrequest')

    def serialize_bugs_closed_field(self, obj):
        return obj.get_bug_list()

    def serialize_status_field(self, obj):
        return status_to_string(obj.status)

    @webapi_login_required
    @webapi_request_fields(
        required={
            'repository': {
                'type': str,
                'description': 'The path or ID of the repository that the '
                               'review request is for.',
            },
        },
        optional={
            'changenum': {
                'type': int,
                'description': 'The optional changenumber to look up for the '
                               'review request details. This only works with '
                               'repositories that support server-side '
                               'changesets.',
            },
            'submit_as': {
                'type': str,
                'description': 'The optional user to submit the review '
                               'request as. This requires that the actual '
                               'logged in user is either a superuser or has '
                               'the "reviews.can_submit_as_another_user" '
                               'permission.',
            },
        })
    def create(self, request, repository, submit_as=None, changenum=None,
               *args, **kwargs):
        """Creates a new review request."""
        user = request.user

        if submit_as and user.username != submit_as:
            if not user.has_perm('reviews.can_submit_as_another_user'):
                return PERMISSION_DENIED

            try:
                user = User.objects.get(username=submit_as)
            except User.DoesNotExist:
                return INVALID_USER

        try:
            try:
                repository = Repository.objects.get(pk=int(repository))
            except ValueError:
                # The repository is not an ID.
                repository = Repository.objects.get(
                    Q(path=repository) |
                    Q(mirror_path=repository))
        except Repository.DoesNotExist, e:
            return INVALID_REPOSITORY, {
                'repository': repository
            }

        try:
            review_request = ReviewRequest.objects.create(user, repository,
                                                          changenum)

            return 201, {
                self.item_result_key: review_request
            }
        except ChangeNumberInUseError, e:
            return CHANGE_NUMBER_IN_USE, {
                'review_request': e.review_request
            }
        except InvalidChangeNumberError:
            return INVALID_CHANGE_NUMBER
        except EmptyChangeSetError:
            return EMPTY_CHANGESET

    @webapi_login_required
    @webapi_request_fields(
        optional={
            'status': {
                'type': ('discarded', 'pending', 'submitted'),
                'description': 'The status of the review request. This can '
                               'be changed to close or reopen the review '
                               'request',
            },
        },
    )
    def update(self, request, status=None, *args, **kwargs):
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if (status is not None and
            review_request.status != string_to_status(status)):
            try:
                if status in self._close_type_map:
                    review_request.close(self._close_type_map[status],
                                         request.user)
                elif status == 'pending':
                    review_request.reopen(request.user)
                else:
                    raise AssertionError("Code path for invalid status '%s' "
                                         "should never be reached." % status)
            except PermissionError:
                return PERMISSION_DENIED

        return 200, {
            self.item_result_key: review_request,
        }

review_request_resource = ReviewRequestResource()


class ServerInfoResource(WebAPIResource):
    name = 'info'
    name_plural = 'info'

    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        """Returns information on the Review Board server.

        This contains product information, such as the version, and
        site-specific information, such as the main URL and list of
        administrators.
        """
        site = Site.objects.get_current()
        siteconfig = SiteConfiguration.objects.get_current()

        url = '%s://%s%s' % (siteconfig.get('site_domain_method'), site.domain,
                             settings.SITE_ROOT)

        return 200, {
            self.item_result_key: {
                'product': {
                    'name': 'Review Board',
                    'version': get_version_string(),
                    'package_version': get_package_version(),
                    'is_release': is_release(),
                },
                'site': {
                    'url': url,
                    'administrators': [{'name': name, 'email': email}
                                       for name, email in settings.ADMINS],
                },
            },
        }

server_info_resource = ServerInfoResource()


root_resource = RootResource([
    repository_resource,
    review_group_resource,
    review_request_resource,
    server_info_resource,
    user_resource,
])


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
        raise Exception("Invalid status '%s'" % status)


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
        raise Exception("Invalid status '%s'" % status)


register_resource_for_model(Comment, review_comment_resource)
register_resource_for_model(DiffSet, diffset_resource)
register_resource_for_model(FileDiff, filediff_resource)
register_resource_for_model(Group, review_group_resource)
register_resource_for_model(Repository, repository_resource)
register_resource_for_model(
    Review,
    lambda obj: obj.is_reply() and review_reply_resource or review_resource)
register_resource_for_model(ReviewRequest, review_request_resource)
register_resource_for_model(ReviewRequestDraft, review_request_draft_resource)
register_resource_for_model(Screenshot, screenshot_resource)
register_resource_for_model(ScreenshotComment,
                            review_screenshot_comment_resource)
register_resource_for_model(User, user_resource)
