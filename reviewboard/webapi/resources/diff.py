from __future__ import unicode_literals

import logging

from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.http import HttpResponse
from django.utils import six
from djblets.util.http import get_http_requested_mimetype, set_last_modified
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_ATTRIBUTE,
                                   INVALID_FORM_DATA, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)
from djblets.webapi.fields import (DateTimeFieldType,
                                   DictFieldType,
                                   FileFieldType,
                                   IntFieldType,
                                   ResourceFieldType,
                                   StringFieldType)

from reviewboard.diffviewer.errors import DiffTooBigError, EmptyDiffError
from reviewboard.diffviewer.features import dvcs_feature
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.forms import UploadDiffForm
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.webapi.base import ImportExtraDataError, WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)
from reviewboard.webapi.errors import (DIFF_EMPTY,
                                       DIFF_TOO_BIG,
                                       REPO_FILE_NOT_FOUND)
from reviewboard.webapi.resources import resources


logger = logging.getLogger(__name__)


class DiffResource(WebAPIResource):
    """Provides information on a collection of complete diffs.

    Each diff contains individual per-file diffs as child resources.
    A diff is revisioned, and more than one can be associated with any
    particular review request.
    """
    model = DiffSet
    name = 'diff'
    fields = {
        'id': {
            'type': IntFieldType,
            'description': 'The numeric ID of the diff.',
        },
        'extra_data': {
            'type': DictFieldType,
            'description': 'Extra data as part of the diff. '
                           'This can be set by the API or extensions.',
            'added_in': '2.0',
        },
        'name': {
            'type': StringFieldType,
            'description': 'The name of the diff, usually the filename.',
        },
        'revision': {
            'type': IntFieldType,
            'description': 'The revision of the diff. Starts at 1 for public '
                           'diffs. Draft diffs may be at 0.',
        },
        'timestamp': {
            'type': DateTimeFieldType,
            'description': 'The date and time that the diff was uploaded.',
        },
        'repository': {
            'type': ResourceFieldType,
            'resource': 'reviewboard.webapi.resources.repository.'
                        'RepositoryResource',
            'description': 'The repository that the diff is applied against.',
        },
        'basedir': {
            'type': StringFieldType,
            'description': 'The base directory that will prepended to all '
                           'paths in the diff. This is needed for some types '
                           'of repositories. The directory must be between '
                           'the root of the repository and the top directory '
                           'referenced in the diff paths.',
            'added_in': '1.7',
        },
        'base_commit_id': {
            'type': StringFieldType,
            'description': 'The ID/revision this change is built upon. '
                           'If using a parent diff, then this is the base '
                           'for that diff. This may not be provided for all '
                           'diffs or repository types, depending on how the '
                           'diff was uploaded.',
            'added_in': '1.7.13',
        },
        'commit_count': {
            'type': IntFieldType,
            'description': 'The number of commits present in the case of '
                           'review requests created with commit history.',
            'added_in': '4.0',
        },
    }
    item_child_resources = [
        resources.diffcommit,
        resources.filediff,
    ]

    allowed_methods = ('GET', 'POST', 'PUT')

    uri_object_key = 'diff_revision'
    model_object_key = 'revision'
    model_parent_key = 'history'
    last_modified_field = 'timestamp'

    allowed_mimetypes = WebAPIResource.allowed_mimetypes + [
        {'item': 'text/x-patch'},
    ]

    def get_queryset(self, request, *args, **kwargs):
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
        except ReviewRequest.DoesNotExist:
            raise self.model.DoesNotExist

        return self.model.objects.filter(
            history__review_request=review_request)

    def get_parent_object(self, diffset):
        return diffset.history.review_request.get()

    def has_access_permissions(self, request, diffset, *args, **kwargs):
        review_request = diffset.history.review_request.get()
        return review_request.is_accessible_by(request.user)

    def has_modify_permissions(self, request, diffset, *args, **kwargs):
        review_request = diffset.history.review_request.get()
        return review_request.is_mutable_by(request.user)

    @webapi_check_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST)
    def get_list(self, *args, **kwargs):
        """Returns the list of public diffs on the review request.

        Each diff has a revision and list of per-file diffs associated with it.
        """
        try:
            return super(DiffResource, self).get_list(*args, **kwargs)
        except self.model.DoesNotExist:
            return DOES_NOT_EXIST

    @webapi_check_login_required
    @webapi_check_local_site
    def get(self, request, *args, **kwargs):
        """Returns the information or contents on a particular diff.

        The output varies by mimetype.

        If :mimetype:`application/json` or :mimetype:`application/xml` is
        used, then the fields for the diff are returned, like with any other
        resource.

        If :mimetype:`text/x-patch` is used, then the actual diff file itself
        is returned. This diff should be as it was when uploaded originally,
        with potentially some extra SCM-specific headers stripped. The
        contents will contain that of all per-file diffs that make up this
        diff.
        """
        mimetype = get_http_requested_mimetype(
            request,
            [
                mimetype['item']
                for mimetype in self.allowed_mimetypes
            ])

        if mimetype == 'text/x-patch':
            return self._get_patch(request, *args, **kwargs)
        else:
            return super(DiffResource, self).get(request, *args, **kwargs)

    def _get_patch(self, request, *args, **kwargs):
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            diffset = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        tool = review_request.repository.get_scmtool()
        data = tool.get_parser(b'').raw_diff(diffset)

        resp = HttpResponse(data, content_type='text/x-patch')

        if diffset.name == 'diff':
            filename = 'bug%s.patch' % \
                       review_request.bugs_closed.replace(',', '_')
        else:
            filename = diffset.name

        resp['Content-Disposition'] = 'inline; filename=%s' % filename
        set_last_modified(resp, diffset.timestamp)

        return resp

    @webapi_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED,
                            REPO_FILE_NOT_FOUND, INVALID_FORM_DATA,
                            INVALID_ATTRIBUTE, DIFF_EMPTY, DIFF_TOO_BIG)
    @webapi_request_fields(
        optional={
            'path': {
                'type': FileFieldType,
                'description': 'The main diff to upload.',
            },
            'basedir': {
                'type': StringFieldType,
                'description': 'The base directory that will prepended to '
                               'all paths in the diff. This is needed for '
                               'some types of repositories. The directory '
                               'must be between the root of the repository '
                               'and the top directory referenced in the '
                               'diff paths.',
            },
            'parent_diff_path': {
                'type': FileFieldType,
                'description': 'The optional parent diff to upload.',
            },
            'base_commit_id': {
                'type': StringFieldType,
                'description': 'The ID/revision this change is built upon. '
                               'If using a parent diff, then this is the base '
                               'for that diff. This may not be provided for '
                               'all diffs or repository types, depending on '
                               'how the diff was uploaded.',
                'added_in': '1.7.13',
            },
        },
        allow_unknown=True
    )
    def create(self, request, extra_fields={}, local_site=None, *args,
               **kwargs):
        """Creates a new diff by parsing an uploaded diff file.

        This will implicitly create the new Review Request draft, which can
        be updated separately and then published.

        This accepts a unified diff file, validates it, and stores it along
        with the draft of a review request. The new diff will have a revision
        of 0.

        A parent diff can be uploaded along with the main diff. A parent diff
        is a diff based on an existing commit in the repository, which will
        be applied before the main diff. The parent diff will not be included
        in the diff viewer. It's useful when developing a change based on a
        branch that is not yet committed. In this case, a parent diff of the
        parent branch would be provided along with the diff of the new commit,
        and only the new commit will be shown.

        It is expected that the client will send the data as part of a
        :mimetype:`multipart/form-data` mimetype. The main diff's name and
        content would be stored in the ``path`` field. If a parent diff is
        provided, its name and content would be stored in the
        ``parent_diff_path`` field.

        An example of this would be::

            -- SoMe BoUnDaRy
            Content-Disposition: form-data; name=path; filename="foo.diff"

            <Unified Diff Content Here>
            -- SoMe BoUnDaRy --

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        # Prevent a circular dependency, as ReviewRequestDraftResource
        # needs DraftDiffResource, which needs DiffResource.
        from reviewboard.webapi.resources.review_request_draft import \
            ReviewRequestDraftResource

        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return self.get_no_access_error(request)

        if review_request.repository is None:
            return INVALID_ATTRIBUTE, {
                'reason': 'This review request was created as attachments-'
                          'only, with no repository.',
            }
        elif review_request.created_with_history:
            assert dvcs_feature.is_enabled(request=request)

            if 'path' in request.FILES:
                return INVALID_FORM_DATA, {
                    'reason': (
                        'This review request was created with support for '
                        'multiple commits.\n'
                        '\n'
                        'Create an empty diff revision and upload commits to '
                        'that instead.'
                    ),
                }

            diffset = DiffSet.objects.create_empty(
                repository=review_request.repository,
                base_commit_id=request.POST.get('base_commit_id'))
            diffset.update_revision_from_history(
                review_request.diffset_history)
            diffset.save(update_fields=('revision',))
        else:
            form_data = request.POST.copy()
            form = UploadDiffForm(review_request,
                                  data=form_data,
                                  files=request.FILES,
                                  request=request)

            if not form.is_valid():
                return INVALID_FORM_DATA, {
                    'fields': self._get_form_errors(form),
                }

            try:
                diffset = form.create()
            except FileNotFoundError as e:
                return REPO_FILE_NOT_FOUND, {
                    'file': e.path,
                    'revision': six.text_type(e.revision)
                }
            except EmptyDiffError as e:
                return DIFF_EMPTY
            except DiffTooBigError as e:
                return DIFF_TOO_BIG, {
                    'reason': six.text_type(e),
                    'max_size': e.max_diff_size,
                }
            except Exception as e:
                # This could be very wrong, but at least they'll see the error.
                # We probably want a new error type for this.
                logger.error("Error uploading new diff: %s", e, exc_info=1,
                             request=request)

                return INVALID_FORM_DATA, {
                    'fields': {
                        'path': [six.text_type(e)]
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
                return self.get_no_access_error(request)

        draft.diffset = diffset

        # We only want to add default reviewers the first time.  Was bug 318.
        if review_request.can_add_default_reviewers():
            draft.add_default_reviewers()

        draft.save()

        if extra_fields:
            try:
                self.import_extra_data(diffset, diffset.extra_data,
                                       extra_fields)
            except ImportExtraDataError as e:
                return e.error_payload

            diffset.save(update_fields=['extra_data'])

        if discarded_diffset:
            discarded_diffset.delete()

        # E-mail gets sent when the draft is saved.

        return 201, {
            self.item_result_key: diffset,
        }

    @webapi_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(allow_unknown=True)
    def update(self, request, extra_fields={}, *args, **kwargs):
        """Updates a diff.

        This is used solely for updating extra data on a diff. The contents
        of a diff cannot be modified.

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            diffset = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return self.get_no_access_error(request)

        if extra_fields:
            try:
                self.import_extra_data(diffset, diffset.extra_data,
                                       extra_fields)
            except ImportExtraDataError as e:
                return e.error_payload

            diffset.save(update_fields=['extra_data'])

        return 200, {
            self.item_result_key: diffset,
        }

    def get_links(self, child_resources=[], obj=None, request=None,
                  *args, **kwargs):
        """Return the links for the resource.

        If the DVCS feature is disabled, links to resources that require the
        feature will not be included.

        Args:
            child_resource (list of reviewboard.webapi.base.WebAPIResource):
                The list of child resources for which links are to be
                serialized.

            obj (reviewboard.diffviewer.models.diffset.DiffSet, optional):
                The object whose links are being serialized.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            A dictionary of serialized links for the resource.
        """
        if (obj is not None and
            not dvcs_feature.is_enabled(request=request) and
            resources.diffcommit in child_resources):
            child_resources = list(child_resources)
            child_resources.remove(resources.diffcommit)

        return super(DiffResource, self).get_links(
            child_resources, obj=obj, request=request, *args, **kwargs)

    def serialize_object(self, obj, request=None, *args, **kwargs):
        """Serialize a DiffSet.

        This method excludes fields from features that are not enabled.

        Args:
            obj (reviewboard.diffviewer.models.diffset.DiffSet):
                The DiffSet to serialize.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            The serialized DiffSet.
        """
        result = super(DiffResource, self).serialize_object(
            obj, request=request, *args, **kwargs)

        if not dvcs_feature.is_enabled(request=request):
            # The field may not have been serialized (e.g., if `only-fields`
            # was set to a subset of fields that excludes
            # `created_with_history`).
            result.pop('commit_count', None)

        return result


diff_resource = DiffResource()
