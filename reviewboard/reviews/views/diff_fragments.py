"""Views for rendering diff fragments."""

import io
import logging
import struct
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_list_or_404
from django.template.loader import render_to_string
from django.utils.cache import patch_cache_control
from django.utils.safestring import SafeString, mark_safe
from django.views.generic.base import ContextMixin, View
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.dates import get_latest_timestamp
from djblets.views.generic.etag import ETagViewMixin
from typing_extensions import TypedDict

from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.diffutils import (get_file_chunks_in_range,
                                              get_last_header_before_line,
                                              get_last_line_number_in_diff)
from reviewboard.diffviewer.models import FileDiff
from reviewboard.diffviewer.renderers import DiffRenderer
from reviewboard.diffviewer.settings import DiffSettings
from reviewboard.diffviewer.views import (DiffFragmentView,
                                          exception_traceback_string)
from reviewboard.reviews.models import Comment
from reviewboard.reviews.ui.base import ReviewUI
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin
from reviewboard.site.urlresolvers import local_site_reverse


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
            max_line = get_last_line_number_in_diff(
                context=context,
                filediff=comment.filediff,
                interfilediff=comment.interfilediff,
                diff_settings=diff_settings)

            first_line = max(1, comment.first_line - lines_of_context[0])
            last_line = min(comment.last_line + lines_of_context[1], max_line)
            num_lines = last_line - first_line + 1

            chunks = list(get_file_chunks_in_range(
                context=context,
                filediff=comment.filediff,
                interfilediff=comment.interfilediff,
                first_line=first_line,
                num_lines=num_lines,
                diff_settings=diff_settings))

            comment_context = {
                'comment': comment,
                'header': get_last_header_before_line(
                    context=context,
                    filediff=comment.filediff,
                    interfilediff=comment.interfilediff,
                    target_line=first_line,
                    diff_settings=diff_settings),
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
                        'depot_filename': comment.filediff.source_file,
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
                Positional arguments passsed to the handler.

            **kwargs (dict, unused):
                Keyword arguments passed to the handler.

        Returns:
            str:
            The ETag for the page.
        """
        q = (Q(pk__in=comment_ids.split(',')) &
             Q(review__review_request=self.review_request))

        if request.user.is_authenticated:
            q &= Q(review__public=True) | Q(review__user=request.user)
        else:
            q &= Q(review__public=True)

        self.comments = get_list_or_404(Comment, q)

        latest_timestamp = get_latest_timestamp(
            comment.timestamp
            for comment in self.comments
        )

        return '%s:%s:%s' % (comment_ids, latest_timestamp,
                             settings.TEMPLATE_SERIAL)

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

    def process_diffset_info(
        self,
        revision: int,
        interdiff_revision: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Process and return information on the desired diff.

        The diff IDs and other data passed to the view can be processed and
        converted into DiffSets. A dictionary with the DiffSet and FileDiff
        information will be returned.

        If the review request cannot be accessed by the user, an HttpResponse
        will be returned instead.

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
        user = self.request.user
        draft = self.review_request.get_draft(user)

        if interdiff_revision is not None:
            interdiffset = self.get_diff(interdiff_revision, draft)
        else:
            interdiffset = None

        diffset = self.get_diff(revision, draft)

        return super().process_diffset_info(
            diffset_or_id=diffset,
            interdiffset_or_id=interdiffset,
            **kwargs)

    def create_renderer(
        self,
        diff_file: Dict[str, Any],
        *args,
        **kwargs,
    ) -> DiffRenderer:
        """Create the DiffRenderer for this fragment.

        This will augment the renderer for binary files by looking up
        file attachments, if review UIs are involved, disabling caching.

        Args:
            diff_file (dict):
                The information on the diff file to render.

            *args (tuple):
                Additional positional arguments from the parent class.

            **kwargs (dict):
                Additional keyword arguments from the parent class.

        Returns:
            reviewboard.diffviewer.renderers.DiffRenderer:
            The resulting diff renderer.
        """
        renderer = super().create_renderer(
            diff_file=diff_file, *args, **kwargs)

        if diff_file['binary']:
            # Determine the file attachments to display in the diff viewer,
            # if any.
            filediff = diff_file['filediff']
            interfilediff = diff_file['interfilediff']

            orig_attachment = None
            modified_attachment = None

            if diff_file['force_interdiff']:
                orig_attachment = self._get_diff_file_attachment(filediff)
                modified_attachment = \
                    self._get_diff_file_attachment(interfilediff)
            else:
                modified_attachment = self._get_diff_file_attachment(filediff)

                if not diff_file['is_new_file']:
                    orig_attachment = \
                        self._get_diff_file_attachment(filediff, False)

            diff_review_ui = None
            diff_review_ui_html = None
            orig_review_ui = None
            orig_review_ui_html = None
            modified_review_ui = None
            modified_review_ui_html = None

            if orig_attachment:
                orig_review_ui = orig_attachment.review_ui

            if modified_attachment:
                modified_review_ui = modified_attachment.review_ui

            # See if we're able to generate a diff review UI for these files.
            if (orig_review_ui and modified_review_ui and
                orig_review_ui.__class__ is modified_review_ui.__class__ and
                modified_review_ui.supports_diffing):
                # Both files are able to be diffed by this review UI.
                # We'll display a special diff review UI instead of two
                # side-by-side review UIs.
                diff_review_ui = modified_review_ui
                diff_review_ui.set_diff_against(orig_attachment)
                diff_review_ui_html = \
                    self._render_review_ui(diff_review_ui, False)
            else:
                # We won't be showing a diff of these files. Instead, just
                # grab the review UIs and render them.
                orig_review_ui_html = \
                    self._render_review_ui(orig_review_ui)
                modified_review_ui_html = \
                    self._render_review_ui(modified_review_ui)

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
            return mark_safe(review_ui.render_to_string(self.request))

        return None

    def _get_diff_file_attachment(
        self,
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
            logger.error('More than one FileAttachments associated with '
                         'FileDiff %s',
                         filediff.pk,
                         exc_info=True)
            return None
