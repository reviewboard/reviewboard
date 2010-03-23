from datetime import datetime
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.template.defaultfilters import timesince
from djblets.siteconfig.models import SiteConfiguration
from djblets.webapi.decorators import webapi_login_required, \
                                      webapi_permission_required
from djblets.webapi.errors import DOES_NOT_EXIST, INVALID_ATTRIBUTE, \
                                  INVALID_FORM_DATA, PERMISSION_DENIED
from djblets.webapi.resources import WebAPIResource as DjbletsWebAPIResource, \
                                     UserResource as DjbletsUserResource

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
    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        return super(WebAPIResource, self).get(request, *args, **kwargs)

    @webapi_check_login_required
    def get_list(self, request, *args, **kwargs):
        if not self.model:
            return HttpResponseNotAllowed(self.allowed_methods)

        if request.GET.get('counts-only', False):
            result = {
                'count': self.get_queryset(request, is_list=True,
                                           *args, **kwargs).count()
            }

            # Several old API functions had a field name other than 'count'.
            # This is deprecated, but must be kept for backwards-compatibility.
            field_alias = \
                request.GET.get('_count-field-alias',
                                kwargs.get('_count-field-alias', None))

            if field_alias:
                result[field_alias] = result['count']

            return 200, result
        else:
            result = super(WebAPIResource, self).get_list(request,
                                                          *args, **kwargs)

            if request.GET.get('_first-result-only', False):
                # This is intended ONLY for deprecated functions. It is not
                # supported as a valid parameter for APIs and should be ignored.
                # It may return broken results if used outside of its built-in
                # intended uses.
                result = (result[0], {
                    self.name: result[1][self.name_plural][0],
                })

            return result


class CommentResource(WebAPIResource):
    model = Comment
    fields = (
        'id', 'filediff', 'interfilediff', 'text', 'timestamp',
        'timesince', 'first_line', 'num_lines', 'public', 'user',
    )

    uri_object_key = 'comment_id'

    allowed_methods = ('GET', 'POST')

    def get_queryset(self, request, review_request_id, diff_revision,
                     *args, **kwargs):
        query = self.model.objects.filter(
            Q(review__public=True) | Q(review__user=request.user),
            filediff__diffset__history__review_request=review_request_id,
            filediff__diffset__revision=diff_revision,
            interfilediff__isnull=True)

        return query

    def serialize_public_field(self, obj):
        return obj.review.get().public

    def serialize_timesince_field(self, obj):
        return timesince(obj.timestamp)

    def serialize_user_field(self, obj):
        return obj.review.get().user

    def get_href_parent_ids(self, comment, *args, **kwargs):
        filediff = comment.filediff
        diffset = filediff.diffset
        review_request = diffset.history.review_request.get()

        return {
            'review_request_id': review_request.id,
            'diff_revision': diffset.revision,
            'filediff_id': filediff.id,
        }

    @webapi_login_required
    def create(self, request, review_request_id, diff_revision, filediff_id,
               *args, **kwargs):
        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)
            filediff = FileDiff.objects.get(
                pk=filediff_id,
                diffset__revision=diff_revision,
                diffset__history__review_request=review_request)
        except (ReviewRequest.DoesNotExist, FileDiff.DoesNotExist):
            return DOES_NOT_EXIST

        line = request.POST.get('line')
        num_lines = request.POST.get('num_lines')
        text = request.POST.get('text')

        interfilediff = None # XXX

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

        return 200, {
            self.name: comment,
        }

commentResource = CommentResource()


class FileDiffResource(WebAPIResource):
    model = FileDiff
    name = 'file'
    fields = (
        'id', 'diffset', 'source_file', 'dest_file',
        'source_revision', 'dest_detail',
    )
    item_child_resources = [commentResource]

    uri_object_key = 'filediff_id'

    def get_queryset(self, request, review_request_id, diff_revision,
                     *args, **kwargs):
        return self.model.objects.filter(
            diffset__history__review_request=review_request_id,
            diffset__revision=diff_revision)

    def get_href_parent_ids(self, filediff, *args, **kwargs):
        diffset = filediff.diffset
        review_request = diffset.history.review_request.get()

        return {
            'diff_revision': diffset.revision,
            'review_request_id': review_request.id,
        }

fileDiffResource = FileDiffResource()


class DiffSetResource(WebAPIResource):
    model = DiffSet
    name = 'diff'
    fields = ('id', 'name', 'revision', 'timestamp', 'repository')
    item_child_resources = [fileDiffResource]

    allowed_methods = ('GET', 'POST')

    uri_object_key = 'diff_revision'
    model_object_key = 'revision'

    def get_queryset(self, request, review_request_id, *args, **kwargs):
        return self.model.objects.filter(
            history__review_request=review_request_id)

    def get_href_parent_ids(self, diffset, *args, **kwargs):
        history = diffset.history

        if history:
            review_request = history.review_request.get()
        else:
            # This isn't in a history yet. It's part of a draft.
            review_request = diffset.review_request_draft.get().review_request

        return {
            'review_request_id': review_request.id,
        }

    def has_access_permissions(self, request, diffset, *args, **kwargs):
        review_request = diffset.history.review_request.get()
        return review_request.is_accessible_by(request.user)

    @webapi_login_required
    def create(self, request, review_request_id, *args, **kwargs):
        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)
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
                draft = _prepare_draft(request, review_request)
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

        return 200, {
            'diffset': diffset,
            'diffset_id': diffset.id, # Deprecated
        }

diffSetResource = DiffSetResource()


class UserResource(DjbletsUserResource):
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


class ReviewGroupUserResource(UserResource):
    def get_queryset(self, request, group_name, *args, **kwargs):
        return self.model.objects.filter(review_groups__name=group_name)


class ReviewGroupResource(WebAPIResource):
    model = Group
    fields = ('id', 'name', 'display_name', 'mailing_list', 'url')
    item_child_resources = [ReviewGroupUserResource()]

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

    @webapi_login_required
    def action_star(self, request, group_name, *args, **kwargs):
        """
        Adds a group to the user's watched groups list.
        """
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            return DOES_NOT_EXIST

        profile, profile_is_new = \
            Profile.objects.get_or_create(user=request.user)
        profile.starred_groups.add(group)
        profile.save()

        return 200, {}

    @webapi_login_required
    def action_unstar(self, request, group_name, *args, **kwargs):
        """
    Removes a group from the user's watched groups list.
        """
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            return DOES_NOT_EXIST

        profile, profile_is_new = \
            Profile.objects.get_or_create(user=request.user)

        if not profile_is_new:
            profile.starred_groups.remove(group)
            profile.save()

        return 200, {}


class RepositoryInfoResource(WebAPIResource):
    name = 'info'
    name_plural = 'info'
    allowed_methods = ('GET',)

    @webapi_check_login_required
    def get(self, request, repository_id, *args, **kwargs):
        try:
            repository = Repository.objects.get(pk=repository_id)
        except Repository.DoesNotExist:
            return DOES_NOT_EXIST

        try:
            return 200, {
                self.name: repository.get_scmtool().get_repository_info()
            }
        except NotImplementedError:
            return REPO_NOT_IMPLEMENTED
        except:
            return REPO_INFO_ERROR


class RepositoryResource(WebAPIResource):
    model = Repository
    name_plural = 'repositories'
    fields = ('id', 'name', 'path', 'tool')
    uri_object_key = 'repository_id'
    item_child_resources = [RepositoryInfoResource()]

    allowed_methods = ('GET',)

    @webapi_check_login_required
    def get_queryset(self, request, *args, **kwargs):
        return self.model.objects.filter(visible=True)

    def serialize_tool_field(self, obj):
        return obj.tool.name


class ReviewRequestDraftResource(WebAPIResource):
    model = ReviewRequestDraft
    name = 'draft'
    name_plural = 'draft'
    mutable_fields = (
        'summary', 'description', 'testing_done', 'bugs_closed',
        'branch', 'target_groups', 'target_people'
    )
    fields = ('id', 'review_request', 'last_updated') + mutable_fields

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    SCREENSHOT_CAPTION_FIELD_RE = \
        re.compile(r'screenshot_(?P<id>[0-9]+)_caption')

    def get_queryset(self, request, review_request_id, *args, **kwargs):
        return self.model.objects.filter(review_request=review_request_id)

    def serialize_bugs_closed_field(self, obj):
        return obj.get_bug_list()

    def serialize_status_field(self, obj):
        return status_to_string(obj.status)

    def has_delete_permissions(self, request, draft, *args, **kwargs):
        return draft.review_request.is_mutable_by(request.user)

    @webapi_login_required
    def create(self, *args, **kwargs):
        # A draft is a singleton. Creating and updating it are the same
        # operations in practice.
        return self.update(*args, **kwargs)

    @webapi_login_required
    def update(self, request, review_request_id, always_save=False,
               *args, **kwargs):
        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        try:
            draft = self._prepare_draft(request, review_request)
        except PermissionDenied:
            return PERMISSION_DENIED

        modified_objects = []
        invalid_fields = {}

        for field_name in request.POST:
            if field_name in ('action', 'method', 'callback'):
                # These are special names and can be ignored.
                continue

            if (field_name in self.mutable_fields or
                self.SCREENSHOT_CAPTION_FIELD_RE.match(field_name)):
                field_result, field_modified_objects, invalid = \
                    self._set_draft_field_data(draft, field_name,
                                               request.POST[field_name])

                if invalid:
                    invalid_fields[field_name] = invalid
                elif field_modified_objects:
                    modified_objects += field_modified_objects
            else:
                invalid_fields[field_name] = ['Field is not supported']

        if always_save or not invalid_fields:
            for obj in modified_objects:
                obj.save()

            draft.save()

        if invalid_fields:
            return INVALID_FORM_DATA, {
                'fields': invalid_fields,
            }

        return 200, {
            self.name: draft,
        }

    @webapi_login_required
    def delete(self, request, review_request_id, *args, **kwargs):
        # Make sure this exists. We don't want to use _prepare_draft, or
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

    @webapi_login_required
    def action_publish(self, request, review_request_id, *args, **kwargs):
        # Make sure this exists. We don't want to use _prepare_draft, or
        # we'll end up creating a new one.
        try:
            draft = ReviewRequestDraft.objects.get(
                review_request=review_request_id)
            review_request = draft.review_request
        except ReviewRequestDraft.DoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return PERMISSION_DENIED

        draft.publish(user=request.user)
        draft.delete()

        return 200, {}

    @webapi_login_required
    def action_deprecated_set(self, request, review_request_id, *args, **kwargs):
        code, result = self.update(request, review_request_id,
                                   always_save=True, *args, **kwargs)

        if code == INVALID_FORM_DATA:
            code = 200

            for field in result['fields']:
                result['invalid_' + field] = result['fields'][field][0]

            del result['fields']

            # These really should succeed, given that they did in update().
            # Better safe than sorry, though.
            try:
                review_request = ReviewRequest.objects.get(pk=review_request_id)
            except ReviewRequest.DoesNotExist:
                return DOES_NOT_EXIST

            try:
                draft = self._prepare_draft(request, review_request)
            except PermissionDenied:
                return PERMISSION_DENIED

            result[self.name] = draft

        return code, result

    @webapi_login_required
    def action_deprecated_set_field(self, request, review_request_id,
                                    field_name, *args, **kwargs):
        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        try:
            draft = self._prepare_draft(request, review_request)
        except PermissionDenied:
            return PERMISSION_DENIED

        if field_name not in self.mutable_fields:
            return INVALID_ATTRIBUTE, {
                'attribute': field_name,
            }

        field_result, modified_objects, invalid = \
            self._set_draft_field_data(draft, field_name,
                                       request.POST['value'])

        result = {}

        if invalid:
            if field_name == 'summary':
                # The summary field returned an INVALID_FORM_DATA, rather
                # than setting the invalid_summary field.
                return INVALID_FORM_DATA, {
                    'attribute': field_name,
                    'detail': invalid[0]
                }

            result['invalid_' + field_name] = invalid[0]
        else:
            result[field_name] = field_result

            for obj in modified_objects:
                obj.save()

            draft.save()

        return 200, result

    @webapi_login_required
    def action_deprecated_discard(self, *args, **kwargs):
        code, result = self.delete(*args, **kwargs)

        if code == 204:
            # Discard returned a 200 on success.
            code = 200

        return code, result

    def _set_draft_field_data(self, draft, field_name, data):
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
        elif field_name.startswith('screenshot_'):
            m = self.SCREENSHOT_CAPTION_FIELD_RE.match(field_name)

            if not m:
                # We've already checked this. It should never happen.
                raise AssertionError('Should not be reached')

            screenshot_id = int(m.group('id'))

            try:
                screenshot = Screenshot.objects.get(pk=screenshot_id)
            except Screenshot.DoesNotExist:
                return ['Screenshot with ID %s does not exist' %
                        screenshot_id], []

            screenshot.draft_caption = data

            result = data
            modified_objects.append(screenshot)
        elif field_name == 'changedescription':
            draft.changedesc.text = data

            modified_objects.append(draft.changedesc)
            result = data
        else:
            if field_name == 'summary' and '\n' in data:
                return ['Summary cannot contain newlines'], []

            setattr(draft, field_name, data)
            result = data

        return data, modified_objects, invalid_entries

    def _sanitize_bug_ids(self, entries):
        for bug in entries.split(','):
            bug = bug.strip()

            if bug:
                # RB stores bug numbers as numbers, but many people have the
                # habit of prepending #, so filter it out:
                if bug[0] == '#':
                    bug = bug[1:]

                yield bug

    def _prepare_draft(self, request, review_request):
        if not review_request.is_mutable_by(request.user):
            raise PermissionDenied

        return ReviewRequestDraft.create(review_request)

    def _find_user(self, username):
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

reviewRequestDraftResource = ReviewRequestDraftResource()


class ReviewDraftCommentsResource(CommentResource):
    mutable_fields = ('text', 'first_line', 'num_lines')

    allowed_methods = ('GET', 'PUT', 'POST', 'DELETE')


class ReviewDraftResource(WebAPIResource):
    model = Review
    name = 'draft'
    name_plural = 'draft'
    deprecated_fields = ('shipit',)
    mutable_fields = ('ship_it', 'body_top', 'body_bottom')
    fields = ('id', 'user', 'timestamp', 'public', 'comments') + mutable_fields

    allowed_methods = ('GET', 'PUT', 'POST', 'DELETE')

    @webapi_login_required
    def get(self, request, api_format, review_request_id, *args, **kwargs):
        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        review = review_request.get_pending_review(request.user)

        if not review:
            return DOES_NOT_EXIST

        return 200, {
            'review': review,
        }

    @webapi_login_required
    def create(self, *args, **kwargs):
        # A draft is a singleton. Creating and updating it are the same
        # operations in practice.
        return self.update(*args, **kwargs)

    @webapi_login_required
    def update(self, request, review_request_id, publish=False,
               *args, **kwargs):
        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        review, review_is_new = Review.objects.get_or_create(
            user=request.user,
            review_request=review_request,
            public=False,
            base_reply_to__isnull=True)

        invalid_fields = {}

        for field_name in request.POST:
            if field_name in ('action', 'method', 'callback'):
                # These are special names and can be ignored.
                continue

            if (field_name not in self.mutable_fields and
                field_name not in self.deprecated_fields):
                invalid_fields[field_name] = ['Field is not supported']
            elif field_name in ('shipit', 'ship_it'):
                # NOTE: "shipit" is deprecated.
                review.ship_it = request.POST[field_name] in \
                                 (1, "1", True, "True")
            elif field_name in ('body_top', 'body_bottom'):
                setattr(review, field_name, request.POST.get(field_name))

        if invalid_fields:
            return INVALID_FORM_DATA, {
                'fields': invalid_fields,
            }

        review.save()

        if publish:
            review.publish(user=request.user)
        else:
            review.save()

        return 200, {}

    @webapi_login_required
    def delete(self, request, api_format, review_request_id, *args, **kwargs):
        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        review = review_request.get_pending_review(request.user)

        if not review:
            return DOES_NOT_EXIST

        review.delete()

        return 204, {}

    @webapi_login_required
    def action_publish(self, *args, **kwargs):
        return self.update(publish=True, *args, **kwargs)

    @webapi_login_required
    def action_deprecated_delete(self, *args, **kwargs):
        result = self.delete(*args, **kwargs)

        if isinstance(result, tuple) and result[0] == 204:
            # Delete returned a 200 on success.
            return 200, result[1]

        return result

reviewDraftResource = ReviewDraftResource()


class ReviewResource(WebAPIResource):
    model = Review
    fields = (
        'id', 'user', 'timestamp', 'public', 'ship_it', 'body_top',
        'body_bottom', 'comments',
    )
    uri_object_key = 'review_id'
    list_child_resources = [
        reviewDraftResource,
    ]

    allowed_methods = ('GET',)

    def get_queryset(self, request, review_request_id, is_list=False,
                     *args, **kwargs):
        q = Q(base_reply_to__isnull=True) & \
            Q(review_request=review_request_id)

        if is_list:
            # We don't want to show drafts in the list.
            q = q & Q(public=True)

        return self.model.objects.filter(q)

    def has_access_permissions(self, request, review, *args, **kwargs):
        return review.public or review.user == request.user

    def get_href_parent_ids(self, review, *args, **kwargs):
        return {
            'review_request_id': review.review_request.id,
        }

reviewResource = ReviewResource()


class ScreenshotCommentResource(WebAPIResource):
    model = ScreenshotComment
    name = 'comment'
    fields = (
        'id', 'screenshot', 'text', 'timestamp', 'timesince',
        'public', 'user', 'x', 'y', 'w', 'h',
    )

    uri_object_key = 'comment_id'

    allowed_methods = ('GET', 'POST')

    def get_queryset(self, request, review_request_id, screenshot_id,
                     *args, **kwargs):
        return self.model.objects.filter(
            screenshot=screenshot_id,
            screenshot__review_request=review_request_id,
            review__isnull=False)

    def serialize_public_field(self, obj):
        return obj.review.get().public

    def serialize_timesince_field(self, obj):
        return timesince(obj.timestamp)

    def serialize_user_field(self, obj):
        return obj.review.get().user

    def get_href_parent_ids(self, comment, *args, **kwargs):
        screenshot = comment.screenshot
        review_request = screenshot.review_request.get()

        return {
            'review_request_id': review_request.id,
            'screenshot_id': screenshot.id,
        }

    @webapi_login_required
    def create(self, request, review_request_id, screenshot_id,
               *args, **kwargs):
        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)
            screenshot = Screenshot.objects.get(
                pk=screenshot_id,
                review_request=review_request)
        except (ReviewRequest.DoesNotExist, Screenshot.DoesNotExist):
            return DOES_NOT_EXIST

        text = request.POST.get('text', None)
        x = request.POST.get('x', None)
        y = request.POST.get('y', None)
        width = request.POST.get('width', None)
        height = request.POST.get('height', None)

        review, review_is_new = Review.objects.get_or_create(
            review_request=review_request,
            user=request.user,
            public=False,
            base_reply_to__isnull=True)

        comment, comment_is_new = review.screenshot_comments.get_or_create(
           screenshot=screenshot,
           x=x, y=y, w=width, h=height)

        comment.text = text
        comment.timestamp = datetime.now()
        comment.save()

        if comment_is_new:
            review.screenshot_comments.add(comment)
            review.save()

        return 200, {
            self.name: comment,
        }

screenshotCommentResource = ScreenshotCommentResource()


class ScreenshotResource(WebAPIResource):
    model = Screenshot
    name = 'screenshot'
    fields = ('id', 'caption', 'title', 'image_url', 'thumbnail_url')

    uri_object_key = 'screenshot_id'

    item_child_resources = [
        screenshotCommentResource,
    ]

    def get_queryset(self, request, review_request_id, *args, **kwargs):
        return self.model.objects.filter(review_request=review_request_id)

    def serialize_title_field(self, obj):
        return u'Screenshot: %s' % (obj.caption or obj.image.name),

    def serialize_image_url_field(self, obj):
        return obj.get_absolute_url()

    def serialize_thumbnail_url_field(self, obj):
        return obj.get_thumbnail_url()

    def get_href_parent_ids(self, screenshot, *args, **kwargs):
        return {
            'review_request_id': screenshot.review_request.get().id,
        }

    @webapi_login_required
    def create(self, request, review_request_id, *args, **kwargs):
        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)
        except ReviewRequest.DoesNotExist:
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

        return 200, {
            'screenshot_id': screenshot.id, # For backwards-compatibility
            'screenshot': screenshot,
        }

screenshotResource = ScreenshotResource()


class ReviewRequestResource(WebAPIResource):
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
        diffSetResource,
        reviewRequestDraftResource,
        reviewResource,
        screenshotResource,
    ]

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def get_queryset(self, request, is_list=False, *args, **kwargs):
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

    def serialize_bugs_closed_field(self, obj):
        if obj.bugs_closed:
            return [b.strip() for b in obj.bugs_closed.split(',')]
        else:
            return ''

    def serialize_status_field(self, obj):
        return status_to_string(obj.status)

    @webapi_login_required
    def create(self, request, *args, **kwargs):
        """
        Creates a new review request.

        Required parameters:

          * repository_path: The repository to create the review request
                             against. If both this and repository_id are set,
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
            repository_path = request.POST.get('repository_path', None)
            repository_id = request.POST.get('repository_id', None)
            submit_as = request.POST.get('submit_as')
            user = request.user

            if submit_as and user.username != submit_as:
                if not user.has_perm('reviews.can_submit_as_another_user'):
                    return PERMISSION_DENIED

                try:
                    user = User.objects.get(username=submit_as)
                except User.DoesNotExist:
                    return INVALID_USER

            if repository_path is None and repository_id is None:
                return MISSING_REPOSITORY

            if repository_path:
                repository = Repository.objects.get(
                    Q(path=repository_path) |
                    Q(mirror_path=repository_path))
            else:
                repository = Repository.objects.get(id=repository_id)

            review_request = ReviewRequest.objects.create(
                user, repository, request.POST.get('changenum', None))

            return 200, {
                'review_request': review_request
            }
        except Repository.DoesNotExist, e:
            return INVALID_REPOSITORY, {
                'repository_path': repository_path
            }
        except ChangeNumberInUseError, e:
            return CHANGE_NUMBER_IN_USE, {
                'review_request': e.review_request
            }
        except InvalidChangeNumberError:
            return INVALID_CHANGE_NUMBER
        except EmptyChangeSetError:
            return EMPTY_CHANGESET

    @webapi_permission_required('reviews.delete_reviewrequest')
    def delete(self, *args, **kwargs):
        return super(ReviewRequestResource, self).delete(*args, **kwargs)

    @webapi_login_required
    def action_star(self, request, review_request_id, *args, **kwargs):
        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        profile, profile_is_new = \
            Profile.objects.get_or_create(user=request.user)
        profile.starred_review_requests.add(review_request)
        profile.save()

        return 200, {}

    @webapi_login_required
    def action_unstar(self, request, review_request_id, *args, **kwargs):
        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        profile, profile_is_new = \
            Profile.objects.get_or_create(user=request.user)

        if not profile_is_new:
            profile.starred_review_requests.remove(review_request)
            profile.save()

        return 200, {}

    @webapi_login_required
    def action_close(self, request, review_request_id, *args, **kwargs):
        type_map = {
            'submitted': ReviewRequest.SUBMITTED,
            'discarded': ReviewRequest.DISCARDED,
        }

        close_type = request.POST.get('type', kwargs.get('type', None))

        if close_type not in type_map:
            return INVALID_ATTRIBUTE, {
                'attribute': close_type,
            }

        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)
            review_request.close(type_map[close_type], request.user)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST
        except PermissionError:
            return HttpResponseForbidden()

        return 200, {}

    @webapi_login_required
    def action_reopen(self, request, review_request_id, *args, **kwargs):
        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)
            review_request.reopen(request.user)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST
        except PermissionError:
            return HttpResponseForbidden()

        return 200, {}

    @webapi_login_required
    def action_publish(self, request, review_request_id, *args, **kwargs):
        try:
            review_request = ReviewRequest.objects.get(pk=review_request_id)

            if not review_request.can_publish():
                return NOTHING_TO_PUBLISH

            review_request.publish(request.user)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST
        except PermissionError:
            return HttpResponseForbidden()

        return 200, {}


class ServerInfoResource(WebAPIResource):
    name = 'info'
    name_plural = 'info'

    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        site = Site.objects.get_current()
        siteconfig = SiteConfiguration.objects.get_current()

        url = '%s://%s%s' % (siteconfig.get('site_domain_method'), site.domain,
                             settings.SITE_ROOT)

        return 200, {
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
        }


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


diffSetResource = DiffSetResource()
fileDiffResource = FileDiffResource()
reviewGroupResource = ReviewGroupResource()
repositoryResource = RepositoryResource()
reviewRequestResource = ReviewRequestResource()
screenshotCommentResource = ScreenshotCommentResource()
screenshotResource = ScreenshotResource()
serverInfoResource = ServerInfoResource()
userResource = UserResource()
