from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.utils import six
from django.utils.six.moves.urllib.parse import quote as urllib_quote
from djblets.util.decorators import augment_method_from
from djblets.util.http import get_http_requested_mimetype, set_last_modified
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)
from djblets.webapi.responses import WebAPIResponse

from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.diffutils import (get_diff_files,
                                              populate_diff_chunks)
from reviewboard.diffviewer.models import FileDiff
from reviewboard.webapi.base import CUSTOM_MIMETYPE_BASE, WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.diff_file_attachment import \
    DiffFileAttachmentResource


class FileDiffResource(WebAPIResource):
    """Provides information on per-file diffs.

    Each of these contains a single, self-contained diff file that
    applies to exactly one file on a repository.
    """
    model = FileDiff
    name = 'file'
    allowed_methods = ('GET', 'PUT')
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the file diff.',
        },
        'extra_data': {
            'type': dict,
            'description': 'Extra data as part of the diff. '
                           'This can be set by the API or extensions.',
        },
        'source_file': {
            'type': six.text_type,
            'description': 'The original name of the modified file in the '
                           'diff.',
        },
        'dest_file': {
            'type': six.text_type,
            'description': 'The new name of the patched file. This may be '
                           'the same as the existing file.',
        },
        'source_revision': {
            'type': six.text_type,
            'description': 'The revision of the file being modified. This '
                           'is a valid revision in the repository.',
        },
        'dest_detail': {
            'type': six.text_type,
            'description': 'Additional information of the destination file. '
                           'This is parsed from the diff, but is usually '
                           'not used for anything.',
        },
        'source_attachment': {
            'type': DiffFileAttachmentResource,
            'description': "The file attachment for the contents of the "
                           "original file for this file diff, if representing "
                           "a binary file.",
        },
        'dest_attachment': {
            'type': DiffFileAttachmentResource,
            'description': "The file attachment for the contents of the "
                           "patched file for this file diff, if representing "
                           "a binary file.",
        },
    }
    item_child_resources = [
        resources.filediff_comment,
        resources.original_file,
        resources.patched_file,
    ]

    uri_object_key = 'filediff_id'
    model_parent_key = 'diffset'

    DIFF_DATA_MIMETYPE_BASE = CUSTOM_MIMETYPE_BASE + '.diff.data'
    DIFF_DATA_MIMETYPE_JSON = DIFF_DATA_MIMETYPE_BASE + '+json'
    DIFF_DATA_MIMETYPE_XML = DIFF_DATA_MIMETYPE_BASE + '+xml'

    allowed_mimetypes = WebAPIResource.allowed_mimetypes + [
        {'item': 'text/x-patch'},
        {'item': DIFF_DATA_MIMETYPE_JSON},
        {'item': DIFF_DATA_MIMETYPE_XML},
    ]

    def serialize_source_attachment_field(self, filediff, **kwargs):
        try:
            return FileAttachment.objects.get_for_filediff(filediff,
                                                           modified=False)
        except FileAttachment.DoesNotExist:
            return None

    def serialize_dest_attachment_field(self, filediff, **kwargs):
        try:
            return FileAttachment.objects.get_for_filediff(filediff,
                                                           modified=True)
        except FileAttachment.DoesNotExist:
            return None

    def get_last_modified(self, request, obj, *args, **kwargs):
        return obj.diffset.timestamp

    def get_queryset(self, request, review_request_id, diff_revision,
                     local_site_name=None, *args, **kwargs):
        if local_site_name:
            review_request = resources.review_request.get_object(
                request,
                review_request_id=review_request_id,
                diff_revision=diff_revision,
                local_site_name=local_site_name,
                *args,
                **kwargs)
            review_request_id = review_request.pk

        return self.model.objects.filter(
            diffset__history__review_request=review_request_id,
            diffset__revision=diff_revision)

    def has_access_permissions(self, request, filediff, *args, **kwargs):
        review_request = resources.review_request.get_object(
            request, *args, **kwargs)

        return resources.review_request.has_access_permissions(
            request, review_request, *args, **kwargs)

    def has_modify_permissions(self, request, filedif, *args, **kwargs):
        review_request = resources.review_request.get_object(
            request, *args, **kwargs)

        return resources.review_request.has_modify_permissions(
            request, review_request, *args, **kwargs)

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of public per-file diffs on the review request.

        Each per-file diff has information about the diff. It does not
        provide the contents of the diff. For that, access the per-file diff's
        resource directly and use the correct mimetype.
        """
        pass

    def get_links(self, *args, **kwargs):
        """Returns a dictionary of links coming off this resource.

        If the file represented by the FileDiffResource is new,
        the link to the OriginalFileResource will be removed.
        Alternatively, if the file is deleted, the link to the
        PatchedFileResource will be removed.
        """
        links = super(FileDiffResource, self).get_links(*args, **kwargs)

        obj = kwargs.get('obj')

        # Only remove the links if we are returning them for
        # a specific filediff, and not a list of filediffs.
        if obj:
            if obj.is_new:
                del links[resources.original_file.name_plural]

            if obj.deleted:
                del links[resources.patched_file.name_plural]

        return links

    @webapi_check_login_required
    @webapi_check_local_site
    def get(self, request, *args, **kwargs):
        """Returns the information or contents on a per-file diff.

        The output varies by mimetype.

        If :mimetype:`application/json` or :mimetype:`application/xml` is
        used, then the fields for the diff are returned, like with any other
        resource.

        If :mimetype:`text/x-patch` is used, then the actual diff file itself
        is returned. This diff should be as it was when uploaded originally,
        for this file only, with potentially some extra SCM-specific headers
        stripped.

        If :mimetype:`application/vnd.reviewboard.org.diff.data+json` or
        :mimetype:`application/vnd.reviewboard.org.diff.data+xml` is used,
        then the raw diff data (lists of inserts, deletes, replaces, moves,
        header information, etc.) is returned in either JSON or XML. This
        contains nearly all of the information used to render the diff in
        the diff viewer, and can be useful for building a diff viewer that
        interfaces with Review Board.

        If ``?syntax-highlighting=1`` is passed, the rendered diff content
        for each line will contain HTML markup showing syntax highlighting.
        Otherwise, the content will be in plain text.

        The format of the diff data is a bit complex. The data is stored
        under a top-level ``diff_data`` element and contains the following
        information:

        .. webapi-resource-field-list::

           .. webapi-resource-field::
              :name: binary
              :type: bool

              Whether or not the file is a binary file. Binary files won't
              have any diff content to display.

           .. webapi-resource-field::
              :name: changed_chunk_indexes
              :type: list[int]

              The list of chunks in the diff that have actual changes
              (inserts, deletes, or replaces).

           .. webapi-resource-field::
              :name: chunks
              :type: list[dict]

              A list of chunks. These are used to render the diff. See
              below.

           .. webapi-resource-field::
              :name: new_file
              :type: bool

              Whether or not this is a newly added file, rather than an
              existing file in the repository.

           .. webapi-resource-field::
              :name: num_changes
              :type: int

              The number of changes made in this file (chunks of adds,
              removes, or deletes).

        Each chunk contains the following fields:

        .. webapi-resource-field-list::

           .. webapi-resource-field::
              :name: change
              :type: ('equal', 'delete', 'insert', 'replace')

              The type of change on this chunk. The type influences what
              sort of information is available for the chunk.

           .. webapi-resource-field::
              :name: collapsable
              :type: bool

              Whether or not this chunk is collapseable. A collapseable
              chunk is one that is hidden by default in the diff viewer,
              but can be expanded. These will always be ``equal`` chunks,
              but not every ``equal`` chunk is necessarily collapseable (as
              they may be there to provide surrounding context for the
              changes).

           .. webapi-resource-field::
              :name: index
              :type: int

              The index of the chunk. This is 0-based.

           .. webapi-resource-field::
              :name: lines
              :type: list[list]

              The list of rendered lines for a side-by-side diff. Each
              entry in the list is itself a list with 8 items:

              1. Row number of the line in the combined side-by-side diff.
              2. The line number of the line in the left-hand file, as an
                 integer (for ``replace``, ``delete``, and ``equal``
                 chunks) or an empty string (for ``insert``).
              3. The text for the line in the left-hand file.
              4. The indexes within the text for the left-hand file that
                 have been replaced by text in the right-hand side. Each
                 index is a list of ``start, end`` positions, 0-based.
                 This is only available for ``replace`` lines. Otherwise
                 the list is empty.
              5. The line number of the line in the right-hand file, as an
                 integer (for ``replace``, ``insert`` and ``equal`` chunks)
                 or an empty string (for ``delete``).
              6. The text for the line in the right-hand file.
              7. The indexes within the text for the right-hand file that
                 are replacements for text in the left-hand file. Each
                 index is a list of ``start, end`` positions, 0-based.
                 This is only available for ``replace`` lines. Otherwise
                 the list is empty.
              8. A boolean that indicates if the line contains only
                 whitespace changes.

           .. webapi-resource-field::
              :name: meta
              :type: dict

              Additional information about the chunk. See below for more
              information.

           .. webapi-resource-field::
              :name: numlines
              :type: int

              The number of lines in the chunk.

        A chunk's meta information contains:

        .. webapi-resource-field-list::

           .. webapi-resource-field::
              :name: headers
              :type: list[[unicode, unicode]]

              Class definitions, function definitions, or other useful
              headers that should be displayed before this chunk. This helps
              users to identify where in a file they are and what the current
              chunk may be a part of.

           .. webapi-resource-field::
              :name: whitespace_chunk
              :type: bool

              Whether or not the entire chunk consists only of whitespace
              changes.

           .. webapi-resource-field::
              :name: whitespace_lines
              :type: list[[int, int]]

              A list of ``(start, end)`` row indexes in the lins that contain
              whitespace-only changes. These are 1-based.

        Other meta information may be available, but most is intended for
        internal use and shouldn't be relied upon.
        """
        mimetype = get_http_requested_mimetype(
            request,
            [
                mimetype['item']
                for mimetype in self.allowed_mimetypes
            ])

        if mimetype == 'text/x-patch':
            return self._get_patch(request, *args, **kwargs)
        elif mimetype.startswith(self.DIFF_DATA_MIMETYPE_BASE + "+"):
            return self._get_diff_data(request, mimetype, *args, **kwargs)
        else:
            return super(FileDiffResource, self).get(request, *args, **kwargs)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        allow_unknown=True
    )
    def update(self, request, extra_fields={}, *args, **kwargs):
        """Updates a per-file diff.

        This is used solely for updating extra data on a file's diff.
        The contents of a diff cannot be modified.

        Extra data can be stored for later lookup by passing
        ``extra_data.key_name=value``. The ``key_name`` and ``value`` can be
        any valid strings. Passing a blank ``value`` will remove the key. The
        ``extra_data.`` prefix is required.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            filediff = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return self._no_access_error(request.user)

        if extra_fields:
            self.import_extra_data(filediff, filediff.extra_data, extra_fields)
            filediff.save(update_fields=['extra_data'])

        return 200, {
            self.item_result_key: filediff,
        }

    def _get_patch(self, request, *args, **kwargs):
        try:
            resources.review_request.get_object(request, *args, **kwargs)
            filediff = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        resp = HttpResponse(filediff.diff, content_type='text/x-patch')
        filename = '%s.patch' % urllib_quote(filediff.source_file)
        resp['Content-Disposition'] = 'inline; filename=%s' % filename
        set_last_modified(resp, filediff.diffset.timestamp)

        return resp

    def _get_diff_data(self, request, mimetype, *args, **kwargs):
        try:
            resources.review_request.get_object(request, *args, **kwargs)
            filediff = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        highlighting = request.GET.get('syntax-highlighting', False)

        files = get_diff_files(filediff.diffset, filediff, request=request)
        populate_diff_chunks(files, highlighting, request=request)

        if not files:
            # This may not be the right error here.
            return DOES_NOT_EXIST

        assert len(files) == 1
        f = files[0]

        payload = {
            'diff_data': {
                'binary': f['binary'],
                'chunks': f['chunks'],
                'num_changes': f['num_changes'],
                'changed_chunk_indexes': f['changed_chunk_indexes'],
                'new_file': f['newfile'],
            }
        }

        # XXX: Kind of a hack.
        api_format = mimetype.split('+')[-1]

        resp = WebAPIResponse(request, payload, api_format=api_format)
        set_last_modified(resp, filediff.diffset.timestamp)

        return resp


filediff_resource = FileDiffResource()
