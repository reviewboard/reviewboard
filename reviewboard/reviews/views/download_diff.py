"""Views for downloading diffs."""

import logging
from typing import Optional

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic.base import View
from djblets.util.http import set_last_modified

from reviewboard.diffviewer.diffutils import (convert_to_unicode,
                                              get_filediff_encodings,
                                              get_original_file,
                                              get_patched_file)
from reviewboard.diffviewer.views import DownloadPatchErrorBundleView
from reviewboard.reviews.views.diff_fragments import ReviewsDiffFragmentView
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin
from reviewboard.scmtools.errors import FileNotFoundError


logger = logging.getLogger(__name__)


class DownloadDiffFileView(ReviewRequestViewMixin, View):
    """Downloads an original or modified file from a diff.

    This will fetch the file from a FileDiff, optionally patching it,
    and return the result as an HttpResponse.
    """

    TYPE_ORIG = 0
    TYPE_MODIFIED = 1

    file_type = TYPE_ORIG

    def get(
        self,
        request: HttpRequest,
        revision: int,
        filediff_id: int,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests for this view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            revision (int):
                The revision of the diff to download the file from.

            filediff_id (int):
                The ID of the FileDiff corresponding to the file to download.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client.
        """
        review_request = self.review_request
        draft = review_request.get_draft(request.user)
        diffset = self.get_diff(revision, draft)
        filediff = get_object_or_404(diffset.files, pk=filediff_id)

        try:
            data = get_original_file(filediff=filediff,
                                     request=request)
        except FileNotFoundError:
            logger.exception(
                'Could not retrieve file "%s" (revision %s) for filediff '
                'ID %s',
                filediff.dest_detail, revision, filediff_id,
                extra={'request': request})
            raise Http404

        if self.file_type == self.TYPE_MODIFIED:
            data = get_patched_file(source_data=data,
                                    filediff=filediff,
                                    request=request)

        encoding_list = get_filediff_encodings(filediff)
        data = convert_to_unicode(data, encoding_list)[1]

        return HttpResponse(data, content_type='text/plain; charset=utf-8')


class DownloadRawDiffView(ReviewRequestViewMixin, View):
    """View for downloading a raw diff from a review request.

    This will generate a single raw diff file spanning all the FileDiffs
    in a diffset for the revision specified in the URL.
    """

    def get(
        self,
        request: HttpRequest,
        revision: Optional[int] = None,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests for this view.

        This will generate the raw diff file and send it to the client.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            revision (int, optional):
                The revision of the diff to download. Defaults to the latest
                revision.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client.
        """
        review_request = self.review_request

        draft = review_request.get_draft(request.user)
        diffset = self.get_diff(revision, draft)

        tool = review_request.repository.get_scmtool()
        data = tool.get_parser(b'').raw_diff(diffset)

        resp = HttpResponse(data, content_type='text/x-patch')

        if diffset.name == 'diff':
            filename = 'rb%d.patch' % review_request.display_id
        else:
            # Get rid of any Unicode characters that may be in the filename.
            filename = diffset.name.encode('ascii', 'ignore').decode('ascii')

            # Content-Disposition headers containing commas break on Chrome 16
            # and newer. To avoid this, replace any commas in the filename with
            # an underscore. Was bug 3704.
            filename = filename.replace(',', '_')

        resp['Content-Disposition'] = 'attachment; filename=%s' % filename
        set_last_modified(resp, diffset.timestamp)

        return resp


class ReviewsDownloadPatchErrorBundleView(DownloadPatchErrorBundleView,
                                          ReviewsDiffFragmentView):
    """A view to download the patch error bundle.

    This view allows users to download a bundle containing data to help debug
    issues when a patch fails to apply. The bundle will contain the diff, the
    original file (as returned by the SCMTool), and the rejects file, if
    applicable.
    """
