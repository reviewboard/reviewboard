"""Views for rendering diff fragments."""

from __future__ import annotations

import io
import logging
import os
import struct
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Tuple

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.cache import patch_cache_control
from django.utils.safestring import SafeString, mark_safe
from django.views.generic.base import ContextMixin, View
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.http import encode_etag
from djblets.views.generic.etag import ETagViewMixin
from housekeeping import deprecate_non_keyword_only_args
from typing_extensions import TypedDict

from reviewboard.attachments.mimetypes import guess_mimetype
from reviewboard.attachments.models import FileAttachment
from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.diffviewer.diffutils import (get_file_chunks_in_range,
                                              get_last_header_before_line,
                                              get_last_line_number_in_diff,
                                              get_sha256)
from reviewboard.diffviewer.models import FileDiff
from reviewboard.diffviewer.settings import DiffSettings
from reviewboard.diffviewer.views import (DiffFragmentView,
                                          exception_traceback_string)
from reviewboard.reviews.models import Comment, FileAttachmentComment
from reviewboard.reviews.ui.base import ReviewUI
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin
from reviewboard.scmtools.core import FileLookupContext
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from collections.abc import Mapping

    from reviewboard.diffviewer.diffutils import SerializedDiffFile
    from reviewboard.diffviewer.models import DiffCommit
    from reviewboard.diffviewer.renderers import DiffRenderer


logger = logging.getLogger(__name__)


class CommentFragment(TypedDict):
    """A comment fragment.

    Version Added:
        6.0
    """

    #: The diff comment.
    #:
    #: Type:
    #:     reviewboard.reviews.models.diff_comment.Comment
    comment: Comment

    #: The rendered diff fragment HTML.
    #:
    #: Type:
    #:     django.utils.safestring.SafeString
    html: SafeString

    #: The diff chunks included in the fragment.
    #:
    #: This is the information returned by
    #: :py:func:`~reviewboard.diffviewer.diffutils.get_file_chunks_in_range`.
    #:
    #: Type:
    #:     list
    chunks: List[Dict]


def build_diff_comment_fragments(
    *,
    comments: List[Comment],
    context: Dict[str, Any],
    comment_template_name: str = 'reviews/diff_comment_fragment.html',
    error_template_name: str = 'diffviewer/diff_fragment_error.html',
    lines_of_context: Optional[List[int]] = None,
    show_controls: bool = False,
    request: Optional[HttpRequest] = None,
) -> Tuple[bool, List[CommentFragment]]:
    """Construct and return the comment fragment data.

    Args:
        comments (list of reviewboard.reviews.models.diff_comment.Comment):
            The comments to return diff fragments for.

        context (dict):
            The rendering context.

        comment_template_name (str, optional):
            The template to use for rendering the comment fragment.

        error_template_name (str, optional):
            The template to use for rendering errors.

        lines_of_context (list of int, optional):
            A 2-element list containing the number of additional lines of
            context to render above and below each fragment.

        show_controls (bool, optional):
            Whether to show expand controls in the rendered output.

        request (django.http.HttpRequest, optional):
            The HTTP request from the client, if available.

    Returns:
        tuple:
        A 2-tuple containing:

        Tuple:
            0 (bool):
                Whether any errors occurred.

            1 (list of CommentFragment):
                The rendered comment fragments.
    """
    comment_entries = []
    had_error = False
    siteconfig = SiteConfiguration.objects.get_current()
    diff_settings = DiffSettings.create(request=request)

    if lines_of_context is None:
        lines_of_context = [0, 0]

    for comment in comments:
        try:
            base_commit: Optional[DiffCommit] = None
            tip_commit: Optional[DiffCommit] = None

            base_filediff = comment.base_filediff

            if base_filediff:
                base_commit = base_filediff.commit

            if comment.filediff.commit_id:
                tip_commit = comment.filediff.commit

            max_line = get_last_line_number_in_diff(
                context=context,
                filediff=comment.filediff,
                interfilediff=comment.interfilediff,
                diff_settings=diff_settings,
                base_filediff=base_filediff,
                base_commit=base_commit,
                tip_commit=tip_commit)

            first_line = max(1, comment.first_line - lines_of_context[0])
            last_line = min(comment.last_line + lines_of_context[1], max_line)
            num_lines = last_line - first_line + 1

            chunks = list(get_file_chunks_in_range(
                context=context,
                filediff=comment.filediff,
                interfilediff=comment.interfilediff,
                first_line=first_line,
                num_lines=num_lines,
                diff_settings=diff_settings,
                base_filediff=base_filediff,
                base_commit=base_commit,
                tip_commit=tip_commit
            ))

            comment_context = {
                'comment': comment,
                'header': get_last_header_before_line(
                    context=context,
                    filediff=comment.filediff,
                    interfilediff=comment.interfilediff,
                    target_line=first_line,
                    diff_settings=diff_settings,
                    base_filediff=base_filediff,
                    base_commit=base_commit,
                    tip_commit=tip_commit),
                'chunks': chunks,
                'domain': Site.objects.get_current().domain,
                'domain_method': siteconfig.get('site_domain_method'),
                'lines_of_context': lines_of_context,
                'expandable_above': show_controls and first_line != 1,
                'expandable_below': show_controls and last_line != max_line,
                'collapsible': lines_of_context != [0, 0],
                'lines_above': first_line - 1,
                'lines_below': max_line - last_line,
                'first_line': first_line,
            }
            comment_context.update(context)
            content = render_to_string(template_name=comment_template_name,
                                       context=comment_context,
                                       request=request)
        except Exception as e:
            content = exception_traceback_string(
                None, e, error_template_name, {
                    'comment': comment,
                    'file': {
                        'orig_filename': comment.filediff.source_file,
                        'index': None,
                        'filediff': comment.filediff,
                    },
                    'domain': Site.objects.get_current().domain,
                    'domain_method': siteconfig.get("site_domain_method"),
                })

            # It's bad that we failed, and we'll return a 500, but we'll
            # still return content for anything we have. This will prevent any
            # caching.
            had_error = True
            chunks = []

        comment_entries.append(CommentFragment(
            comment=comment,
            html=content,
            chunks=chunks))

    return had_error, comment_entries


class CommentDiffFragmentsView(ReviewRequestViewMixin, ETagViewMixin,
                               ContextMixin, View):
    """View for rendering a section of a diff that a comment pertains to.

    This takes in one or more
    :py:class:`~reviewboard.reviews.models.diff_comment.Comment` IDs
    (comma-separated) as part of the URL and returns a payload containing
    data and HTML for each comment's diff fragment, which the client can
    parse in order to dynamically load the fragments into the page.

    The resulting format is a custom, condensed format containing the comment
    ID and HTML for each diff fragment. It's designed to be quick to parse and
    reduces the amount of data to send across the wire (unlike a format like
    JSON, which would add overhead to the serialization/deserialization time
    and data size when storing HTML, or JavaScript, which releases prior to
    3.0 used to handle injecting fragments into the DOM).

    Each entry in the payload is in the following format, with all entries
    joined together:

        <comment ID>\\n
        <html length>\\n
        <html content>

    The format is subject to change without notice, and should not be relied
    upon by third parties.

    The following URL query options are supported:

    ``allow_expansion``:
        Whether expansion controls should be shown to the user. To enable
        this, the caller must pass a value of ``1``. This is disabled by
        default.

    ``lines_of_context``:
        The number of lines of context before and after the commented region
        of the diff. This is in the form of ``pre,post``, where both are the
        numbers of lines. This defaults to ``0,0``.
    """

    comment_template_name = 'reviews/diff_comment_fragment.html'
    error_template_name = 'diffviewer/diff_fragment_error.html'

    content_type = 'application/javascript'

    EXPIRATION_SECONDS = 60 * 60 * 24 * 365  # 1 year

    def get_etag_data(
        self,
        request: HttpRequest,
        comment_ids: str,
        *args,
        **kwargs,
    ) -> str:
        """Return an ETag for the view.

        This will look up state needed for the request and generate a
        suitable ETag. Some of the information will be stored for later
        computation of the template context.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            comment_ids (str):
                A list of comment IDs to render.

            *args (tuple, unused):
                Positional arguments passed to the handler.

            **kwargs (dict, unused):
                Keyword arguments passed to the handler.

        Returns:
            str:
            The ETag for the page.

        Raises:
            django.http.Http404:
                The given parameters were not valid.
        """
        q = (Q(pk__in=comment_ids.split(',')) &
             Q(review__review_request=self.review_request))

        if request.user.is_authenticated:
            q &= Q(review__public=True) | Q(review__user=request.user)
        else:
            q &= Q(review__public=True)

        comments = list(Comment.objects.filter(q).order_by('pk'))

        if not comments:
            raise Http404()

        timestamps = ':'.join(
            comment.timestamp.isoformat()
            for comment in comments
        )

        self.comments = comments

        return f'{comment_ids}:{timestamps}:{settings.TEMPLATE_SERIAL}'

    def get(
        self,
        request: HttpRequest,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests for this view.

        This will generate a payload for the diff comments being loaded and
        pass them in a format that can be parsed by the client.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            **kwargs (dict):
                Keyword arguments passed to the view.

        Returns:
            django.http.HttpResponse:
            The HTTP response containing the fragments payload.
        """
        lines_of_context = request.GET.get('lines_of_context', '0,0')
        allow_expansion = (request.GET.get('allow_expansion') == '1')

        try:
            lines_of_context = [int(i) for i in lines_of_context.split(',')]

            # Ensure that we have 2 values for lines_of_context. If only one is
            # given, assume it is both the before and after context. If more
            # than two are given, only consider the first two. If somehow we
            # get no lines of context value, we will default to [0, 0].

            if len(lines_of_context) == 1:
                lines_of_context.append(lines_of_context[0])
            elif len(lines_of_context) > 2:
                lines_of_context = lines_of_context[0:2]
            elif len(lines_of_context) == 0:
                raise ValueError
        except ValueError:
            lines_of_context = [0, 0]

        context = super().get_context_data(**kwargs)
        context.update({
            'request': request,
            'user': request.user,
        })

        payload = io.BytesIO()
        had_error, comment_entries = build_diff_comment_fragments(
            comments=self.comments,
            context=context,
            comment_template_name=self.comment_template_name,
            error_template_name=self.error_template_name,
            lines_of_context=lines_of_context,
            show_controls=allow_expansion)

        for entry in comment_entries:
            html = entry['html'].strip().encode('utf-8')

            payload.write(struct.pack(b'<LL', entry['comment'].pk, len(html)))
            payload.write(html)

        result = payload.getvalue()
        payload.close()

        response = HttpResponse(result,
                                content_type='text/plain; charset=utf-8')

        if had_error:
            patch_cache_control(response,
                                no_cache=True,
                                no_store=True,
                                max_age=0,
                                must_revalidate=True)

        return response


class ReviewsDiffFragmentView(ReviewRequestViewMixin, DiffFragmentView):
    """Renders a fragment from a file in the diff viewer.

    Displays just a fragment of a diff or interdiff owned by the given
    review request. The fragment is identified by the chunk index in the
    diff.

    ``review_request_id``:
        The ID of the ReviewRequest containing the diff to render.

    ``revision``:
        The DiffSet revision to render.

    ``filediff_id``:
        The ID of the FileDiff within the DiffSet.

    The following may also be provided:

    ``interdiff_revision``:
        The second DiffSet revision in an interdiff revision range.

    ``chunk_index``:
        The index (0-based) of the chunk to render. If left out, the
        entire file will be rendered.

    ``local_site``:
        The LocalSite the ReviewRequest must be on, if any.

    See :py:class:`~reviewboard.diffviewer.views.DiffFragmentView` for the
    accepted query parameters.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the view.

        Args:
            *args (tuple):
                Positional arguments to pass through to the parent class.

            **kwargs (dict):
                Keyword arguments to pass through to the parent class.
        """
        super().__init__(*args, **kwargs)

        self._cached_diffset_info: (Mapping[str, Any] | None) = None

    def process_diffset_info(
        self,
        revision: int,
        interdiff_revision: (int | None) = None,
        **kwargs,
    ) -> Mapping[str, Any]:
        """Process and return information on the desired diff.

        The diff IDs and other data passed to the view can be processed and
        converted into DiffSets. A dictionary with the DiffSet and FileDiff
        information will be returned.

        Args:
            revision (int):
                The revision of the diff to view.

            interdiff_revision (int, optional):
                The second diff revision if viewing an interdiff.

            **kwargs (dict):
                Keyword arguments passed to the view.

        Returns:
            dict:
            Information on the diff for use in the template and in queries.
        """
        if self._cached_diffset_info is not None:
            return self._cached_diffset_info

        draft = self.review_request.get_draft(user=self.request.user)

        if interdiff_revision is not None:
            interdiffset = self.get_diff(interdiff_revision, draft)
        else:
            interdiffset = None

        diffset = self.get_diff(revision, draft)

        info = super().process_diffset_info(
            diffset_or_id=diffset,
            interdiffset_or_id=interdiffset,
            **kwargs)

        self._cached_diffset_info = info

        return info

    def make_etag(
        self,
        *,
        request: (HttpRequest | None) = None,
        **kwargs,
    ) -> str:
        """Return an ETag identifying this render.

        Version Added:
            7.1.0

        Args:
            request (django.http.HttpRequest):
                The request from the client.

                Version Added:
                    7.1.0

            **kwargs (dict):
                Additional keyword arguments passed to the function.

        Returns:
            str:
            The encoded ETag identifying this render.

        Raises:
            django.http.Http404:
                The diff for the given parameters was not found.
        """
        etag = super().make_etag(request=request, **kwargs)

        filediff_id = kwargs.get('filediff_id')
        filediff = get_object_or_404(FileDiff, pk=filediff_id)

        if filediff.binary:
            # For binary files, serialized comments get included with the
            # Review UI's rendered HTML. We therefore need to include the
            # comment timestamps in the ETag or reloading the page can
            # show out of date comments.
            #
            # This isn't an issue for non-binary files because all the comments
            # are included along with the main diff viewer page, rather than
            # with individual fragments.
            assert request is not None

            diff_info = self.process_diffset_info(
                base_filediff_id=request.GET.get('base-filediff-id'),
                **kwargs)
            diff_file = diff_info['diff_file']

            orig_attachment, modified_attachment = \
                self._get_attachment_objects_for_binary(
                    request=request,
                    filediff=diff_file['filediff'],
                    interfilediff=diff_file['interfilediff'],
                    base_filediff=diff_file['base_filediff'],
                    force_interdiff=diff_file['force_interdiff'],
                    is_new_file=diff_file['is_new_file'],
                )

            if orig_attachment or modified_attachment:
                comment_timestamps = (
                    FileAttachmentComment.objects.for_file_attachment(
                        attachment=modified_attachment,
                        diff_against_file_attachment=orig_attachment,
                        user=request.user,
                    )
                    .order_by('pk')
                    .values_list('timestamp', flat=True)
                )

                if comment_timestamps:
                    timestamps = ':'.join(
                        timestamp.isoformat()
                        for timestamp in comment_timestamps
                    )
                    etag = encode_etag(f'{etag}:{timestamps}')

        return etag

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
        """Create the DiffRenderer for this fragment.

        This will augment the renderer for binary files by looking up
        file attachments, if review UIs are involved, disabling caching.

        Version Changed:
            7.1:
            * Deprecated non-keyword arguments.
            * Added the ``request`` parameter.

        Args:
            context (dict):
                The current render context.

            renderer_settings (dict):
                The diff renderer settings.

            diff_file (reviewboard.diffviewer.diffutils.SerializedDiffFile):
                The information on the diff file to render.

            request (django.http.HttpRequest):
                The request from the client.

            **kwargs (dict):
                Additional keyword arguments from the parent class.

        Returns:
            reviewboard.diffviewer.renderers.DiffRenderer:
            The resulting diff renderer.
        """
        renderer = super().create_renderer(
            request=request,
            context=context,
            renderer_settings=renderer_settings,
            diff_file=diff_file,
            **kwargs)

        if diff_file['binary']:
            # Determine the file attachments to display in the diff viewer,
            # if any.
            orig_attachment, modified_attachment = \
                self._get_attachment_objects_for_binary(
                    request=request,
                    filediff=diff_file['filediff'],
                    interfilediff=diff_file['interfilediff'],
                    base_filediff=diff_file['base_filediff'],
                    force_interdiff=diff_file['force_interdiff'],
                    is_new_file=diff_file['is_new_file'],
                )

            diff_review_ui_html: (str | None) = None
            orig_review_ui_class: (type[ReviewUI[Any, Any, Any]] | None) = None
            orig_review_ui_html: (str | None) = None
            modified_review_ui_class: (
                type[ReviewUI[Any, Any, Any]] |
                None
            ) = None
            modified_review_ui_html: (str | None) = None
            review_request = context['review_request']

            if orig_attachment:
                orig_review_ui_class = ReviewUI.for_object(orig_attachment)

            if modified_attachment:
                modified_review_ui_class = ReviewUI.for_object(
                    modified_attachment)

            if (orig_review_ui_class is not None and
                orig_review_ui_class is modified_review_ui_class and
                orig_review_ui_class.supports_diffing):
                review_ui = orig_review_ui_class(
                    review_request=review_request,
                    obj=modified_attachment)
                review_ui.set_diff_against(orig_attachment)
                diff_review_ui_html = self._render_review_ui(review_ui)
            else:
                if orig_review_ui_class:
                    review_ui = orig_review_ui_class(
                        review_request=review_request,
                        obj=orig_attachment)
                    orig_review_ui_html = self._render_review_ui(review_ui)

                if modified_review_ui_class:
                    review_ui = modified_review_ui_class(
                        review_request=review_request,
                        obj=modified_attachment)
                    modified_review_ui_html = self._render_review_ui(review_ui)

            if (diff_review_ui_html or orig_review_ui_html or
                modified_review_ui_html):
                # Don't cache the view, because the Review UI may care about
                # state that we can't anticipate. At the least, it may have
                # comments or other data that change between renders, and we
                # don't want that to go stale.
                renderer.allow_caching = False

            renderer.extra_context.update({
                'orig_diff_file_attachment': orig_attachment,
                'modified_diff_file_attachment': modified_attachment,
                'orig_attachment_review_ui_html': orig_review_ui_html,
                'modified_attachment_review_ui_html': modified_review_ui_html,
                'diff_attachment_review_ui_html': diff_review_ui_html,
            })

        renderer.extra_context.update(
            self._get_download_links(renderer, diff_file))

        return renderer

    def _get_attachment_objects_for_binary(
        self,
        *,
        request: HttpRequest,
        filediff: FileDiff,
        interfilediff: FileDiff | None,
        base_filediff: FileDiff | None,
        force_interdiff: bool,
        is_new_file: bool,
    ) -> tuple[FileAttachment | None, FileAttachment | None]:
        """Return the file attachments to display in the diff viewer.

        For any binary files which are part of the change, we use file
        attachments for storage and review.

        Version Added:
            7.1.0

        Args:
            request (django.http.HttpRequest):
                The request from the client.

            filediff (reviewboard.diffviewer.models.FileDiff):
                The filediff for the file.

            interfilediff (reviewboard.diffviewer.models.FileDiff):
                The filediff for the interdiff, if present.

            base_filediff (reviewboard.diffviewer.models.FileDiff):
                The filediff for the base diff, if present.

            force_interdiff (bool):
                Whether to force rendering an interdiff.

                This is used to show correct interdiffs for files that were
                reverted in later versions.

            is_new_file (bool):
                Whether the filediff corresponds to a newly-added file.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (reviewboard.attachments.models.FileAttachment):
                    The file attachment for the original version of the file,
                    if present.

                1 (reviewboard.attachments.models.FileAttachment):
                    The file attachment for the modified version of the file,
                    if present.
        """
        orig_attachment: (FileAttachment | None) = None
        modified_attachment: (FileAttachment | None) = None

        if force_interdiff:
            if interfilediff:
                orig_attachment = self._get_diff_file_attachment(
                    filediff=filediff)
                modified_attachment = self._get_diff_file_attachment(
                    filediff=interfilediff)
            else:
                # We're forcing an interdiff but have no interfilediff, which
                # means this is a reverted file.
                orig_attachment = self._get_diff_file_attachment(
                    filediff=filediff)
                modified_attachment = self._get_diff_file_attachment(
                    filediff=filediff,
                    use_modified=False)
        else:
            modified_attachment = self._get_diff_file_attachment(
                filediff=filediff)

            if base_filediff is not None:
                orig_attachment = self._get_diff_file_attachment(
                    filediff=base_filediff)
            elif not is_new_file:
                orig_attachment = self._get_diff_file_attachment(
                    filediff=filediff, use_modified=False)

                if (orig_attachment is None and
                    modified_attachment is not None):
                    # We only fetch the original version of the file if we
                    # already have an attachment for the modified version. This
                    # way we're not cluttering up the DB and filesystem with
                    # attachments that aren't helpful for the review process.
                    orig_attachment = self._create_attachment_for_orig(
                        request=request, filediff=filediff)

        return orig_attachment, modified_attachment

    def get_context_data(
        self,
        **kwargs,
    ) -> Dict[str, Any]:
        """"Return context for rendering the view.

        Args:
            **kwargs (dict):
                Keyword arguments passed to the view.

        Returns:
            dict:
            Context to use for rendering templates.
        """
        return {
            'review_request': self.review_request,
        }

    def _get_download_links(
        self,
        renderer: DiffRenderer,
        diff_file: Dict[str, Any],
    ) -> Dict[str, Optional[str]]:
        """Return links for downloading the files used for the diff.

        Args:
            renderer (reviewboard.diffviewer.renderers.DiffRenderer):
                The diff renderer.

            diff_file (dict):
                The diff file information.

        Returns:
            dict:
            A dictionary containing ``download_orig_url`` and
            ``download_modified_url`` keys, with the URLs to download the
            original and modified files.
        """
        if diff_file['binary']:
            orig_attachment = \
                renderer.extra_context['orig_diff_file_attachment']
            modified_attachment = \
                renderer.extra_context['modified_diff_file_attachment']

            if orig_attachment:
                download_orig_url = orig_attachment.get_absolute_url()
            else:
                download_orig_url = None

            if modified_attachment:
                download_modified_url = modified_attachment.get_absolute_url()
            else:
                download_modified_url = None
        else:
            filediff = diff_file['filediff']
            interfilediff = diff_file['interfilediff']
            diffset = filediff.diffset

            if interfilediff:
                orig_url_name = 'download-modified-file'
                modified_revision = interfilediff.diffset.revision
                modified_filediff_id = interfilediff.pk
            else:
                orig_url_name = 'download-orig-file'
                modified_revision = diffset.revision
                modified_filediff_id = filediff.pk

            download_orig_url = local_site_reverse(
                orig_url_name,
                request=self.request,
                kwargs={
                    'review_request_id': self.review_request.display_id,
                    'revision': diffset.revision,
                    'filediff_id': filediff.pk,
                })

            download_modified_url = local_site_reverse(
                'download-modified-file',
                request=self.request,
                kwargs={
                    'review_request_id': self.review_request.display_id,
                    'revision': modified_revision,
                    'filediff_id': modified_filediff_id,
                })

        return {
            'download_orig_url': download_orig_url,
            'download_modified_url': download_modified_url,
        }

    def _render_review_ui(
        self,
        review_ui: Optional[ReviewUI],
        inline_only: bool = True,
    ) -> Optional[SafeString]:
        """Render the review UI for a file attachment.

        Args:
            review_ui (reviewboard.reviews.ui.base.ReviewUI):
                The review UI to render.

            inline_only (bool):
                Whether to limit rendering to review UIs that support inline
                mode.

        Returns:
            django.utils.safestring.SafeString:
            The rendered review UI HTML, if available. ``None`` if not.
        """
        if review_ui and (not inline_only or review_ui.allow_inline):
            return mark_safe(review_ui.render_to_string(self.request,
                                                        inline=True))

        return None

    def _get_diff_file_attachment(
        self,
        *,
        filediff: FileDiff,
        use_modified: bool = True,
    ) -> Optional[FileAttachment]:
        """Fetch the FileAttachment associated with a FileDiff.

        Args:
            filediff (reviewboard.diffviewer.models.filediff.FileDiff):
                The FileDiff to find a linked attachment.

            use_modified (bool):
                Whether to return the attachment for the modified version (new
                file). If ``False``, will return the FileAttachment for the
                original file.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The matching file attachment, if available. If no matching
            attachment is found, or if more than one is found associated with
            the FileDiff, ``None`` is returned.
        """
        if not filediff:
            return None

        try:
            return FileAttachment.objects.get_for_filediff(filediff,
                                                           use_modified)
        except ObjectDoesNotExist:
            return None
        except MultipleObjectsReturned:
            # Only one FileAttachment should be associated with a FileDiff
            logger.exception('More than one FileAttachments associated with '
                             'FileDiff %s',
                             filediff.pk,
                             extra={'request': self.request})

            return None

    def _create_attachment_for_orig(
        self,
        *,
        request: HttpRequest,
        filediff: FileDiff,
    ) -> FileAttachment | None:
        """Create an attachment for the original version of a binary file.

        New versions of binary files in diffs are expected to be uploaded by
        RBTools, but the original version may need to be fetched from the
        repository.

        Version Added:
            7.0

        Args:
            request (django.http.HttpRequest):
                The request from the server.

            filediff (reviewboard.diffviewer.models.filediff.Filediff):
                The FileDiff for the attachment.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The newly-created file attachment, or ``None`` if the creation
            failed.
        """
        extra_data = filediff.extra_data or {}

        if filediff.commit is not None:
            commit_extra_data = filediff.commit.extra_data
        else:
            commit_extra_data = {}

        diffset = filediff.diffset

        context = FileLookupContext(
            request=request,
            base_commit_id=diffset.base_commit_id,
            diff_extra_data=diffset.extra_data,
            commit_extra_data=commit_extra_data,
            file_extra_data=extra_data)

        try:
            repository = filediff.get_repository()
            file_contents = repository.get_file(
                path=filediff.source_file,
                revision=filediff.source_revision,
                context=context)
            attachment_extra_data = {
                'sha256_checksum': get_sha256(file_contents),
            }

            with ContentFile(file_contents) as file_obj:
                attachment = FileAttachment.objects.create_from_filediff(
                    extra_data=attachment_extra_data,
                    filediff=filediff,
                    from_modified=False,
                    mimetype=guess_mimetype(file_obj))

                attachment.file.save(
                    os.path.basename(filediff.source_file),
                    file_obj)

            logger.debug('Creating new file attachment for binary file %s '
                         '(%s) in repository %s',
                         filediff.source_file,
                         filediff.source_revision,
                         repository)

            return attachment
        except Exception as e:
            logger.exception(
                'Unable to fetch original version of binary file %s (%s): %s',
                filediff.source_file,
                filediff.source_revision,
                e)

            return None
