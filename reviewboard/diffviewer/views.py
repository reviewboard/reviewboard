"""Views for the diff viewer."""

from __future__ import annotations

import logging
import os
import re
import traceback
from io import BytesIO
from typing import Any, Mapping, Optional, TYPE_CHECKING, Union
from zipfile import ZipFile

from django.conf import settings
from django.core.paginator import InvalidPage, Paginator
from django.http import (HttpResponse,
                         HttpResponseNotFound,
                         HttpResponseNotModified,
                         HttpResponseServerError,
                         Http404)
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import NoReverseMatch
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.generic.base import TemplateView, View
from djblets.util.http import encode_etag, etag_if_none_match, set_etag
from housekeeping import deprecate_non_keyword_only_args
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from typing_extensions import NotRequired, TypedDict

from reviewboard.deprecation import (
    RemovedInReviewBoard80Warning,
    RemovedInReviewBoard90Warning,
)
from reviewboard.diffviewer.commit_utils import (
    SerializedCommitHistoryDiffEntry,
    diff_histories)
from reviewboard.diffviewer.diffutils import get_diff_files
from reviewboard.diffviewer.errors import PatchError, UserVisibleError
from reviewboard.diffviewer.models import DiffCommit, DiffSet, FileDiff
from reviewboard.diffviewer.renderers import (
    DiffRenderer,
    get_diff_renderer,
    get_diff_renderer_class,
)
from reviewboard.diffviewer.settings import DiffSettings
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from django.http import HttpRequest

    from reviewboard.diffviewer.diffutils import SerializedDiffFile
    from reviewboard.diffviewer.models.diffcommit import SerializedDiffCommit


logger = logging.getLogger(__name__)


class SerializedPaginationInfo(TypedDict):
    """Serialized information about pagination.

    Version Added:
        7.0
    """

    #: Whether the diff has been paginated.
    is_paginated: bool

    #: The current page number.
    current_page: int

    #: The total number of pages.
    pages: int

    #: The set of all page numbers.
    page_numbers: list[int]

    #: Whether there's another page after the current one.
    has_next: bool

    #: Whether there's another page before the current one.
    has_previous: bool

    #: The number of the next page, if available.
    next_page: NotRequired[int]

    #: The number of the previous page, if available.
    previous_page: NotRequired[int]


class SerializedRevisionInfo(TypedDict):
    """Serialized information about diff revisions.

    Version Added:
        7.0
    """

    #: The current diff revision.
    revision: int

    #: Whether the current page is an interdiff.
    is_interdiff: bool

    #: The current interdiff revision, if available.
    interdiff_revision: Optional[int]

    #: The current base commit ID, when viewing a commit range.
    base_commit_id: Optional[int]

    #: The current tip commit ID, when viewing a commit range.
    tip_commit_id: Optional[int]

    #: The most recent diff revision, if available.
    latest_revision: NotRequired[Optional[int]]

    #: Whether the current page is showing a draft diff.
    is_draft_diff: NotRequired[bool]

    #: Whether the current page is showing a draft interdiff.
    is_draft_interdiff: NotRequired[bool]


class SerializedDiffContext(TypedDict):
    """Serialized diff information.

    Version Added:
        7.0
    """

    #: The set of commits for the current diff revision.
    commits: Optional[list[SerializedDiffCommit]]

    #: The diff of commits between two diff revisions.
    #:
    #: This will only be populated when viewing an interdiff.
    commit_history_diff: Optional[list[SerializedCommitHistoryDiffEntry]]

    #: A list of filename patterns to limit the view to.
    filename_patterns: list[str]

    #: Pagination information for the current diff.
    pagination: SerializedPaginationInfo

    #: Revision information for the current diff.
    revision: SerializedRevisionInfo


class DiffViewerContext(TypedDict):
    """Render context for the diff viewer views.

    Version Added:
        7.0
    """

    #: Whether to collapse all expandable diff context.
    collapseall: bool

    #: The template context information for the diff.
    diff_context: SerializedDiffContext

    #: The current diff.
    diffset: DiffSet

    #: The current interdiff, if available.
    interdiffset: Optional[DiffSet]

    #: The list of all files in the current diff/interdiff.
    files: list[SerializedDiffFile]


def get_collapse_diff(request):
    if request.GET.get('expand', False):
        return False
    elif request.GET.get('collapse', False):
        return True
    elif 'collapsediffs' in request.COOKIES:
        return (request.COOKIES['collapsediffs'] == "True")
    else:
        return True


class DiffViewerView(TemplateView):
    """Renders the main diff viewer.

    This renders the diff viewer for a given DiffSet (or an interdiff
    between two DiffSets). It handles loading information on the diffs,
    generating the side-by-side view, and pagination.

    The view expects the following parameters to be provided:

    ``diffset``
        The DiffSet to render.

    The following may also be provided:

    ``interdiffset``
        A DiffSet object representing the other end of an interdiff range.

    The following query parameters can be passed in on the URL:

    ``?expand=1``
        Expands all files within the diff viewer.

    ``?collapse=1``
        Collapses all files within the diff viewer, showing only
        modifications and a few lines of context.

    ``?file=<id>``
        Renders only the FileDiff represented by the provided ID.

    ``?filenames=<pattern>[,<pattern>,...]``
        Renders files matching the given filenames or
        :py:mod:`patterns <fnmatch>`. Patterns are case-sensitive.

    ``?page=<pagenum>``
        Renders diffs found on the given page number, if the diff viewer
        is paginated.

    ``?base-commit-id=<id>``
        The ID of the base commit to use to generate the diff for diffs created
        with multiple commits.

        Only changes from after the specified commit will be included in the
        diff.

    ``?tip-commit-id=<id>``
        The ID of the tip commit to use to generate the diff for diffs created
        created with history.

        No changes from beyond this commit will be included in the diff.
    """

    template_name = 'diffviewer/view_diff.html'
    fragment_error_template_name = 'diffviewer/diff_fragment_error.html'

    def get(
        self,
        request: HttpRequest,
        diffset: DiffSet,
        interdiffset: Optional[DiffSet] = None,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle GET requests for this view.

        This will render the full diff viewer based on the provided
        parameters.

        The full rendering time will be logged.

        If there's any exception thrown during rendering, an error page
        with a traceback will be returned instead.
        """
        self.collapse_diffs = get_collapse_diff(request)

        if interdiffset:
            logger.debug('Generating diff viewer page for interdiffset '
                         'ids %s-%s',
                         diffset.pk, interdiffset.pk,
                         extra={'request': request})
        else:
            logger.debug('Generating diff viewer page for filediff id %s',
                         diffset.pk,
                         extra={'request': request})

        try:
            response = super().get(
                request, diffset=diffset, interdiffset=interdiffset,
                *args, **kwargs)

            if interdiffset:
                logger.debug('Done generating diff viewer page for '
                             'interdiffset ids %s-%s',
                             diffset.pk, interdiffset.pk,
                             extra={'request': request})
            else:
                logger.debug('Done generating diff viewer page for filediff '
                             'id %s',
                             diffset.pk,
                             extra={'request': request})

            return response
        except Exception as e:
            if interdiffset:
                interdiffset_id = interdiffset.pk
            else:
                interdiffset_id = None

            logger.exception('%s.get: Error rendering diff for diffset '
                             'ID=%s, interdiffset ID=%s: %s',
                             self.__class__.__name__,
                             diffset.pk,
                             interdiffset_id,
                             e,
                             extra={'request': request})

            return exception_traceback(request, e, self.template_name)

    def render_to_response(self, *args, **kwargs) -> HttpResponse:
        """Render the page to an HttpResponse.

        This renders the diff viewer page, based on the context data
        generated, and sets cookies before returning an HttpResponse to
        the client.

        Args:
            *args (tuple):
                Positional arguments to pass through to the parent class.

            **kwargs (tuple):
                Keyword arguments to pass through to the parent class.

        Returns:
            django.http.HttpResponse:
            The response to send back to the client.
        """
        response = super().render_to_response(*args, **kwargs)
        response.set_cookie('collapsediffs', self.collapse_diffs)

        return response

    @deprecate_non_keyword_only_args(RemovedInReviewBoard80Warning)
    def get_context_data(
        self,
        *,
        diffset: DiffSet,
        interdiffset: Optional[DiffSet],
        all_commits: list[DiffCommit],
        base_commit: Optional[DiffCommit],
        tip_commit: Optional[DiffCommit],
        extra_context: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> DiffViewerContext:
        """Calculate and return data used for rendering the diff viewer.

        This handles all the hard work of generating the data backing the
        side-by-side diff, handling pagination, and more. The data is
        collected into a context dictionary and returned for rendering.

        Version Changed:
            7.0:
            * Added typed dicts for return data.
            * Made arguments keyword-only.
            * Added ``all_commits``, ``base_commit``, and ``tip_commit``
              arguments.

        Args:
            diffset (reviewboard.diffviewer.models.DiffSet):
                The diffset being viewed.

            interdiffset (reviewboard.diffviewer.models.DiffSet):
                The interdiff diffset, if present.

            all_commits (list of reviewboard.diffviewer.models.DiffCommit):
                The list of all commits in all diffs on the review request.

            base_commit (reviewboard.diffviewer.models.DiffCommit):
                The base commit, when viewing a commit range.

            tip_commit (reviewboard.diffviewer.models.DiffCommit):
                The tip commit, when viewing a commit range.

            extra_context (dict, optional):
                Extra information to add to the context.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            dict:
            Context to use when rendering the template.
        """
        try:
            filename_patterns = \
                re.split(r',+\s*', self.request.GET['filenames'].strip())
        except KeyError:
            filename_patterns = []

        diff_settings = DiffSettings.create(request=self.request)
        files = get_diff_files(
            diffset=diffset,
            interdiffset=interdiffset,
            request=self.request,
            filename_patterns=filename_patterns,
            base_commit=base_commit,
            tip_commit=tip_commit,
            diff_settings=diff_settings)

        paginator = Paginator(files,
                              diff_settings.paginate_by,
                              diff_settings.paginate_orphans)

        page_num = int(self.request.GET.get('page', 1))

        if self.request.GET.get('file', False):
            file_id = int(self.request.GET['file'])

            for i, f in enumerate(files):
                if f['filediff'].pk == file_id:
                    page_num = min(i // paginator.per_page + 1,
                                   paginator.num_pages)

                    break

        try:
            page = paginator.page(page_num)
        except InvalidPage:
            page = paginator.page(paginator.num_pages)

        diff_context: SerializedDiffContext = {
            'commits': None,
            'commit_history_diff': None,
            'filename_patterns': filename_patterns,
            'revision': {
                'revision': diffset.revision,
                'is_interdiff': interdiffset is not None,
                'interdiff_revision': (interdiffset.revision
                                       if interdiffset else None),
                'base_commit_id': base_commit and base_commit.pk,
                'tip_commit_id': tip_commit and tip_commit.pk,
            },
            'pagination': {
                'is_paginated': page.has_other_pages(),
                'current_page': page.number,
                'pages': paginator.num_pages,
                'page_numbers': list(paginator.page_range),
                'has_next': page.has_next(),
                'has_previous': page.has_previous(),
            },
        }

        if page.has_next():
            diff_context['pagination']['next_page'] = page.next_page_number()

        if page.has_previous():
            diff_context['pagination']['previous_page'] = \
                page.previous_page_number()

        if diffset.commit_count > 0:
            diff_commits = [
                commit
                for commit in all_commits
                if commit.diffset_id == diffset.pk
            ]

            diff_context['commits'] = [
                commit.serialize()
                for commit in diff_commits
            ]

            if interdiffset:
                interdiff_commits = [
                    commit
                    for commit in all_commits
                    if commit.diffset_id == interdiffset.pk
                ]

                diff_context['commit_history_diff'] = [
                    entry.serialize()
                    for entry in diff_histories(diff_commits,
                                                interdiff_commits)
                ]

                diff_context['commits'].extend(
                    commit.serialize()
                    for commit in interdiff_commits
                )

        context: DiffViewerContext = {
            'diff_context': diff_context,
            'diffset': diffset,
            'interdiffset': interdiffset,
            'files': list(page.object_list),
            'collapseall': self.collapse_diffs,
        }

        if extra_context is not None:
            context.update(extra_context)

        return context


class DiffFragmentView(View):
    """Renders a fragment from a file in the diff viewer.

    Based on the diffset data and other arguments provided, this will render
    a fragment from a file in a diff. This may be the entire file, or some
    chunk within.

    The view expects the following parameters to be provided:

        * diffset_or_id
          - A DiffSet object or the ID for one.

        * filediff_id
          - The ID of a FileDiff within the DiffSet.

    The following may also be provided:

        * interdiffset_or_id
          - A DiffSet object or the ID for one representing the other end of
            an interdiff range.

        * interfilediff_id
          - A FileDiff ID for the other end of a revision range.

        * chunk_index
          - The index (0-based) of the chunk to render. If left out, the
            entire file will be rendered.

    Both ``filediff_id` and ``interfilediff_id`` need to be available in the
    URL (or otherwise passed to :py:meth:`get`). ``diffset_or_id`` and
    ``interdiffset_or_id`` are needed in :py:meth:`process_diffset_info`, and
    so must be passed either in the URL or in a subclass's definition of
    that method.

    The following query parameters can be passed in on the URL:

    ``?lines-of-context=<count>``
        A number of lines of context to include above and below the chunk.

    ``?base-filediff-id<=id>``
        The primary key of the base FileDiff.

        This parameter is ignored if the review request was created without
        commit history support.

        This conflicts with the ``interfilediff_id``.
    """

    template_name = 'diffviewer/diff_file_fragment.html'
    error_template_name = 'diffviewer/diff_fragment_error.html'
    patch_error_template_name = 'diffviewer/diff_fragment_patch_error.html'

    def get(self, request, *args, **kwargs):
        """Handle GET requests for this view.

        This will create the renderer for the diff fragment, render it, and
        return it.

        If there's an error when rendering the diff fragment, an error page
        will be rendered and returned instead.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            *args (tuple):
                Additional positional arguments for the view.

            **kwargs (dict):
                Additional keyword arguments for the view.

        Returns:
            django.http.HttpResponse:
            A response containing the rendered fragment.
        """
        filediff_id = kwargs.get('filediff_id')
        interfilediff_id = kwargs.get('interfilediff_id')
        chunk_index = kwargs.get('chunk_index')

        base_filediff_id = request.GET.get('base-filediff-id')

        try:
            renderer_settings = self._get_renderer_settings(**kwargs)
            etag = self.make_etag(
                request=request,
                renderer_settings=renderer_settings,
                **kwargs)

            if etag_if_none_match(request, etag):
                return HttpResponseNotModified()

            diff_info = self.process_diffset_info(
                base_filediff_id=base_filediff_id,
                **kwargs)
        except Http404:
            raise
        except Exception as e:
            logger.exception('%s.get: Error when processing diffset info '
                             'for filediff ID=%s, interfilediff ID=%s, '
                             'chunk_index=%s: %s',
                             self.__class__.__name__,
                             filediff_id,
                             interfilediff_id,
                             chunk_index,
                             e,
                             extra={'request': request})

            return exception_traceback(self.request, e,
                                       self.error_template_name)

        kwargs.update(diff_info)

        try:
            context = self.get_context_data(**kwargs)

            renderer = self.create_renderer(
                request=request,
                context=context,
                renderer_settings=renderer_settings,
                **kwargs)
            response = renderer.render_to_response(request)
        except PatchError as e:
            logger.warning(
                '%s.get: PatchError when rendering diffset for filediff '
                'ID=%s, interfilediff ID=%s, chunk_index=%s: %s',
                self.__class__.__name__,
                filediff_id,
                interfilediff_id,
                chunk_index,
                e,
                extra={'request': request})

            try:
                url_kwargs = {
                    key: kwargs[key]
                    for key in ('chunk_index', 'interfilediff_id',
                                'review_request_id', 'filediff_id',
                                'revision', 'interdiff_revision')
                    if key in kwargs and kwargs[key] is not None
                }

                bundle_url = local_site_reverse('patch-error-bundle',
                                                kwargs=url_kwargs,
                                                request=request)
            except NoReverseMatch:
                # We'll sometimes see errors about this failing to resolve when
                # web crawlers start accessing fragment URLs without the proper
                # attributes. Ignore them.
                bundle_url = ''

            if e.rejects:
                lexer = get_lexer_by_name('diff')
                formatter = HtmlFormatter()
                rejects = highlight(e.rejects, lexer, formatter)
            else:
                rejects = None

            return HttpResponseServerError(render_to_string(
                template_name=self.patch_error_template_name,
                context={
                    'bundle_url': bundle_url,
                    'file': diff_info['diff_file'],
                    'filename': os.path.basename(e.filename),
                    'patch_output': e.error_output,
                    'rejects': mark_safe(rejects),
                },
                request=request))
        except FileNotFoundError as e:
            return HttpResponseServerError(render_to_string(
                template_name=self.error_template_name,
                context={
                    'error': e,
                    'file': diff_info['diff_file'],
                },
                request=request))
        except Exception as e:
            logger.exception('%s.get: Error when rendering diffset for '
                             'filediff ID=%s, interfilediff ID=%s, '
                             'chunkindex=%s: %s',
                             self.__class__.__name__,
                             filediff_id,
                             interfilediff_id,
                             chunk_index,
                             e,
                             extra={'request': request})

            return exception_traceback(
                self.request, e, self.error_template_name,
                extra_context={
                    'file': diff_info['diff_file'],
                })

        if response.status_code == 200:
            set_etag(response, etag)

        return response

    @deprecate_non_keyword_only_args(RemovedInReviewBoard90Warning)
    def make_etag(
        self,
        *,
        renderer_settings: Mapping[str, Any],
        filediff_id: int,
        interfilediff_id: (int | None) = None,
        request: (HttpRequest | None) = None,
        **kwargs,
    ) -> str:
        """Return an ETag identifying this render.

        Version Changed:
            7.1.0:
            * Deprecated non-keyword arguments.
            * Added the ``request`` parameter.

        Args:
            renderer_settings (dict):
                The settings determining how to render this diff.

                The following keys are required: ``collapse_all`` and
                ``highlighting``.

                The following key is optional: ``show_deleted``.

            filediff_id (int):
                The ID of the
                :py:class:`~reviewboard.diffviewer.models.filediff.FileDiff`
                being rendered.

            interfilediff_id (int):
                The ID of the
                :py:class:`~reviewboard.diffviewer.models.filediff.FileDiff` on
                the other side of the diff revision, if viewing an interdiff.

            request (django.http.HttpRequest, optional):
                The request from the client.

                Version Added:
                    7.1.0

            **kwargs (dict):
                Additional keyword arguments passed to the function.

        Returns:
            str:
            The encoded ETag identifying this render.
        """
        return encode_etag(
            '%s:%s:%s:%s:%s:%s'
            % (get_diff_renderer_class(),
               renderer_settings['diff_settings'].state_hash,
               renderer_settings['collapse_all'],
               filediff_id,
               interfilediff_id,
               settings.TEMPLATE_SERIAL))

    def process_diffset_info(
        self,
        diffset_or_id: DiffSet | int,
        filediff_id: int,
        interfilediff_id: (int | None) = None,
        interdiffset_or_id: (DiffSet | int | None) = None,
        base_filediff_id: (int | None) = None,
        **kwargs,
    ) -> Mapping[str, Any]:
        """Process and return information on the desired diff.

        The diff IDs and other data passed to the view can be processed and
        converted into DiffSets. A dictionary with the DiffSet and FileDiff
        information will be returned.

        Args:
            diffset_or_id (reviewboard.diffviewer.models.diffset.DiffSet or
                           int):
                The DiffSet object, or the ID of the diffset.

            filediff_id (int):
                The ID of the FileDiff.

            interfilediff_id (int, optional):
                The ID of the FileDiff for rendering an interdiff, if present.

            interdiffset_or_id (reviewboard.diffviewer.models.diffset.DiffSet
                                or int):
                The diffset object, or the ID of the diffset.

            base_filediff_id (int):
                The ID of the base FileDiff to use, if present. This may only
                be provided if ``filediff_id`` is provided and
                ``interfilediff_id`` is not.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            dict:
            Information about the diff.
        """
        # Depending on whether we're invoked from a URL or from a wrapper
        # with precomputed diffsets, we may be working with either IDs or
        # actual objects. If they're objects, just use them as-is. Otherwise,
        # if they're IDs, we want to grab them both (if both are provided)
        # in one go, to save on an SQL query.
        diffset = None
        interdiffset = None

        diffset_ids = []

        if isinstance(diffset_or_id, DiffSet):
            diffset = diffset_or_id
        else:
            diffset_ids.append(diffset_or_id)

        if interdiffset_or_id:
            if isinstance(interdiffset_or_id, DiffSet):
                interdiffset = interdiffset_or_id
            else:
                diffset_ids.append(interdiffset_or_id)

        if diffset_ids:
            diffsets = DiffSet.objects.filter(pk__in=diffset_ids)

            if len(diffsets) != len(diffset_ids):
                raise Http404

            for temp_diffset in diffsets:
                if temp_diffset.pk == diffset_or_id:
                    diffset = temp_diffset
                elif temp_diffset.pk == interdiffset_or_id:
                    interdiffset = temp_diffset
                else:
                    assert False

        filediff = get_object_or_404(FileDiff, pk=filediff_id, diffset=diffset)

        base_filediff = None
        interfilediff = None

        if interfilediff_id and base_filediff_id:
            raise UserVisibleError(_(
                'Cannot generate an interdiff when base FileDiff ID is '
                'specified.'
            ))
        elif interfilediff_id:
            interfilediff = get_object_or_404(FileDiff, pk=interfilediff_id,
                                              diffset=interdiffset)
        elif base_filediff_id:
            base_filediff = get_object_or_404(FileDiff, pk=base_filediff_id,
                                              diffset=diffset)

            ancestors = filediff.get_ancestors(minimal=False)

            if base_filediff not in ancestors:
                raise UserVisibleError(_(
                    'The requested FileDiff (ID %s) is not a valid base '
                    'FileDiff for FileDiff %s.'
                ) % (base_filediff_id, filediff_id))

        assert diffset is not None

        # Store this so we don't end up causing an SQL query later when looking
        # this up.
        filediff.diffset = diffset

        diff_file = self._get_requested_diff_file(
            diffset=diffset,
            filediff=filediff,
            interdiffset=interdiffset,
            interfilediff=interfilediff,
            base_filediff=base_filediff,
            diff_settings=DiffSettings.create(request=self.request))

        if not diff_file:
            raise UserVisibleError(
                _('Internal error. Unable to locate file record for '
                  'filediff %s')
                % filediff.pk)

        return {
            'diffset': diffset,
            'interdiffset': interdiffset,
            'filediff': filediff,
            'diff_file': diff_file,
        }

    @deprecate_non_keyword_only_args(RemovedInReviewBoard90Warning)
    def create_renderer(
        self,
        *,
        context: Mapping[str, Any],
        renderer_settings: Mapping[str, Any],
        diff_file: SerializedDiffFile,
        request: HttpRequest,
        **kwargs,
    ) -> DiffRenderer:
        """Create the renderer for the diff.

        This calculates all the state and data needed for rendering, and
        constructs a DiffRenderer with that data. That renderer is then
        returned, ready for rendering.

        If there's an error in looking up the necessary information, this
        may raise a UserVisibleError (best case), or some other form of
        Exception.

        Version Changed:
            7.1.0:
            * Deprecated non-keyword arguments.
            * Added the ``request`` parameter.

        Args:
            context (dict):
                The template rendering context.

            renderer_settings (dict):
                The diff renderer settings.settings

            diff_file (reviewboard.diffviewer.diffutils.SerializedDiffFile):
                The information on the diff file to render.

            request (django.http.HttpRequest):
                The request from the client.

                Version Added:
                    7.1.0

            **kwargs (dict):
                Keyword arguments, for future expansion.

        Returns:
            reviewboard.diffviewer.renderers.DiffRenderer:
            The resulting diff renderer.
        """
        return get_diff_renderer(
            diff_file,
            extra_context=context,
            template_name=self.template_name,
            **renderer_settings)

    def get_context_data(self, *args, **kwargs):
        """Returns context data used for rendering the view.

        This can be overridden by subclasses to provide additional data for the
        view.
        """
        return {}

    def _get_renderer_settings(self, chunk_index=None, **kwargs):
        """Calculate the render settings for the display of a diff.

        This will calculate settings based on user preferences and URL
        parameters. It does not calculate the state of any DiffSets or
        FileDiffs.
        """
        try:
            lines_of_context = self.request.GET.get('lines-of-context', '')
            lines_of_context = [int(i) for i in lines_of_context.split(',', 1)]
        except (TypeError, ValueError):
            lines_of_context = None

        if chunk_index is not None:
            try:
                chunk_index = int(chunk_index)
            except (TypeError, ValueError):
                chunk_index = None

        if lines_of_context:
            collapse_all = True
        elif chunk_index is not None:
            # If we're currently expanding part of a chunk, we want to render
            # the entire chunk without any lines collapsed. In the case of
            # showing a range of lines, we're going to get all chunks and then
            # only show the range. This is so that we won't have separate
            # cached entries for each range.
            collapse_all = False
        else:
            collapse_all = get_collapse_diff(self.request)

        show_deleted = (self.request.GET.get('show-deleted') == '1')

        return {
            'chunk_index': chunk_index,
            'collapse_all': collapse_all,
            'diff_settings': DiffSettings.create(request=self.request),
            'lines_of_context': lines_of_context,
            'show_deleted': show_deleted,
        }

    def _get_requested_diff_file(
        self,
        *,
        diffset: DiffSet,
        filediff: Optional[FileDiff],
        interdiffset: Optional[DiffSet],
        interfilediff: Optional[FileDiff],
        base_filediff: Optional[FileDiff],
        diff_settings: Optional[DiffSettings],
    ) -> Optional[SerializedDiffFile]:
        """Fetch information on the requested diff.

        This will look up information on the diff that's to be rendered
        and return it, if found. It may also augment it with additional
        data.

        The file will not contain chunk information. That must be specifically
        populated later.

        Version Changed:
            7.0.4:
            * Made arguments keyword-only.
            * Added the ``diff_settings`` argument.

        Args:
            diffset (reviewboard.diffviewer.models.diffset.DiffSet):
                The diffset containing the files to return.

            filediff (reviewboard.diffviewer.models.filediff.FileDiff,
                      optional):
                A specific file in the diff to return information for.

            interdiffset (reviewboard.diffviewer.models.diffset.DiffSet,
                          optional):
                A second diffset used for an interdiff range.

            interfilediff (reviewboard.diffviewer.models.filediff.FileDiff,
                           optional):
                A second specific file in ``interdiffset`` used to return
                information for. This should be provided if ``filediff`` and
                ``interdiffset`` are both provided. If it's ``None`` in this
                case, then the diff will be shown as reverted for this file.

                This may not be provided if ``base_filediff`` is provided.

            base_filediff (reviewbaord.diffviewer.models.filediff.FileDiff,
                           optional):
                The base FileDiff to use.

                This may only be provided if ``filediff`` is provided and
                ``interfilediff`` is not.

            diff_settings (reviewboard.diffviewer.settings.DiffSettings,
                           optional):
                The diff settings object. This will become mandatory in Review
                Board 9.0.

                Version Added:
                    7.0.4

        Returns:
            SerializedDiffFile:
            The serialized file information.
        """
        files = get_diff_files(diffset=diffset,
                               interdiffset=interdiffset,
                               filediff=filediff,
                               interfilediff=interfilediff,
                               base_filediff=base_filediff,
                               request=self.request,
                               diff_settings=diff_settings)

        if files:
            diff_file = files[0]

            try:
                diff_file['index'] = int(self.request.GET['index'])
            except (KeyError, ValueError):
                pass

            return diff_file

        return None


class DownloadPatchErrorBundleView(DiffFragmentView):
    """A view to download the patch error bundle.

    This view allows users to download a bundle containing data to help debug
    issues when a patch fails to apply. The bundle will contain the diff, the
    original file (as returned by the SCMTool), and the rejects file, if
    applicable.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET requests for this view.

        This will create the renderer for the diff fragment and render it in
        order to get the PatchError information. It then returns a response
        with a zip file containing all the debug data.

        If no PatchError occurred, this will return a 404.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            *args (tuple):
                Additional positional arguments for the view.

            **kwargs (dict):
                Additional keyword arguments for the view.

        Returns:
            django.http.HttpResponse:
            A response containing the data bundle.
        """
        try:
            renderer_settings = self._get_renderer_settings(**kwargs)
            etag = self.make_etag(renderer_settings=renderer_settings,
                                  request=request, **kwargs)

            if etag_if_none_match(request, etag):
                return HttpResponseNotModified()

            diff_info = self.process_diffset_info(**kwargs)
        except Http404:
            return HttpResponseNotFound()
        except Exception as e:
            logger.exception(
                '%s.get: Error when processing diffset info for filediff '
                'ID=%s, interfilediff ID=%s, chunk_index=%s: %s',
                self.__class__.__name__,
                kwargs.get('filediff_id'),
                kwargs.get('interfilediff_id'),
                kwargs.get('chunk_index'),
                e,
                extra={'request': request})
            return HttpResponseServerError()

        kwargs.update(diff_info)

        try:
            context = self.get_context_data(**kwargs)

            renderer = self.create_renderer(
                request=request,
                context=context,
                renderer_settings=renderer_settings,
                **kwargs)
            renderer.render_to_response(request)
        except PatchError as e:
            patch_error = e
        except Exception as e:
            logger.exception(
                '%s.get: Error when rendering diffset for filediff ID=%s, '
                'interfilediff ID=%s, chunk_index=%s: %s',
                self.__class__.__name__,
                kwargs.get('filediff_id'),
                kwargs.get('interfilediff_id'),
                kwargs.get('chunk_index'),
                e,
                extra={'request': request})
            return HttpResponseServerError()
        else:
            return HttpResponseNotFound()

        zip_data = BytesIO()

        with ZipFile(zip_data, 'w') as zipfile:
            basename = os.path.basename(patch_error.filename)
            zipfile.writestr('%s.orig' % basename, patch_error.orig_file)
            zipfile.writestr('%s.diff' % basename, patch_error.diff)

            if patch_error.rejects:
                zipfile.writestr('%s.rej' % basename, patch_error.rejects)

            if patch_error.new_file:
                zipfile.writestr('%s.new' % basename, patch_error.new_file)

        rsp = HttpResponse(zip_data.getvalue(),
                           content_type='application/zip')
        rsp['Content-Disposition'] = \
            'attachment; filename=%s.zip' % basename

        return rsp


def exception_traceback_string(request, e, template_name, extra_context={}):
    context = {'error': e}
    context.update(extra_context)

    if not isinstance(e, UserVisibleError):
        context['trace'] = traceback.format_exc()

    return render_to_string(template_name=template_name,
                            context=context,
                            request=request)


def exception_traceback(request, e, template_name, extra_context={}):
    return HttpResponseServerError(
        exception_traceback_string(request, e, template_name, extra_context))
