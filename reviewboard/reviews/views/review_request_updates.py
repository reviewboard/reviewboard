"""View for sending data for updating the review request page."""

import io
import json
import logging
import struct
from typing import Optional

import dateutil.parser
from django.conf import settings
from django.http import (Http404,
                         HttpRequest,
                         HttpResponse,
                         HttpResponseBadRequest)
from django.template.loader import render_to_string
from django.utils.timezone import is_aware, make_aware, utc
from django.views.generic.base import ContextMixin, View
from djblets.util.serializers import DjbletsJSONEncoder
from djblets.views.generic.etag import ETagViewMixin

from reviewboard.reviews.context import make_review_request_context
from reviewboard.reviews.detail import ReviewRequestPageData, entry_registry
from reviewboard.reviews.markdown_utils import is_rich_text_default_for_user
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin


logger = logging.getLogger(__name__)


class ReviewRequestUpdatesView(ReviewRequestViewMixin, ETagViewMixin,
                               ContextMixin, View):
    """Internal view for sending data for updating the review request page.

    This view serializes data representing components of the review request
    page (the issue summary table and entries) that need to periodically
    update without a full page reload. It's used internally by the page to
    request and handle updates.

    The resulting format is a custom, condensed format containing metadata
    information and HTML for each component being updated. It's designed
    to be quick to parse and reduces the amount of data to send across the
    wire (unlike a format like JSON, which would add overhead to the
    serialization/deserialization time and data size when storing HTML).

    Each entry in the payload is in the following format, with all entries
    joined together:

        <metadata length>\\n
        <metadata content>
        <html length>\\n
        <html content>

    The format is subject to change without notice, and should not be
    relied upon by third parties.
    """

    def __init__(
        self,
        **kwargs,
    ) -> None:
        """Initialize the view.

        Args:
            **kwargs (tuple):
                Keyword arguments passed to :py:meth:`as_view`.
        """
        super().__init__(**kwargs)

        self.entry_ids = {}
        self.data = None
        self.since = None

    def pre_dispatch(
        self,
        request: HttpRequest,
        *args,
        **kwargs
    ) -> Optional[HttpResponse]:
        """Look up and validate state before dispatching the request.

        This looks up information based on the request before performing any
        ETag generation or otherwise handling the HTTP request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Positional arguments passsed to the view.

            **kwargs (dict, unused):
                Keyword arguments passed to the view.

        Returns:
            django.http.HttpResponse:
            The HTTP response containing the updates payload.

        Raises:
            Http404:
                The entry state could not be loaded.
        """
        super().pre_dispatch(request, *args, **kwargs)

        # Find out which entries and IDs (if any) that the caller is most
        # interested in.
        entries_str = request.GET.get('entries')

        if entries_str:
            try:
                for entry_part in entries_str.split(';'):
                    entry_type, entry_ids = entry_part.split(':')
                    self.entry_ids[entry_type] = set(entry_ids.split(','))
            except ValueError as e:
                return HttpResponseBadRequest('Invalid ?entries= value: %s'
                                              % e)

        if self.entry_ids:
            entry_classes = []

            for entry_type in self.entry_ids.keys():
                entry_cls = entry_registry.get_entry(entry_type)

                if entry_cls:
                    entry_classes.append(entry_cls)
        else:
            entry_classes = list(entry_registry)

        if not entry_classes:
            raise Http404

        self.since = request.GET.get('since')

        self.data = ReviewRequestPageData(self.review_request, request,
                                          entry_classes=entry_classes)

    def get_etag_data(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> str:
        """Return an ETag for the view.

        This will look up state needed for the request and generate a
        suitable ETag. Some of the information will be stored for later
        computation of the payload.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Positional arguments passsed to the handler.

            **kwargs (dict, unused):
                Keyword arguments passed to the handler.

        Returns:
            str:
            The ETag for the page.
        """
        review_request = self.review_request
        data = self.data
        assert data is not None

        # Build page data only for the entry we care about.
        data.query_data_pre_etag()

        last_activity_time = review_request.get_last_activity_info(
            data.diffsets, data.reviews)['timestamp']

        entry_etags = ':'.join(
            entry_cls.build_etag_data(data)
            for entry_cls in entry_registry
        )

        return ':'.join(str(value) for value in (
            request.user,
            last_activity_time,
            data.latest_review_timestamp,
            review_request.last_review_activity_timestamp,
            entry_etags,
            is_rich_text_default_for_user(request.user),
            settings.AJAX_SERIAL,
        ))

    def get(
        self,
        request: HttpRequest,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests for this view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client. This will contain the
            custom update payload content.
        """
        request = self.request
        review_request = self.review_request
        data = self.data
        since = self.since

        assert data is not None

        # Finish any querying needed by entries on this page.
        data.query_data_post_etag()

        # Gather all the entries into a single list.
        #
        # Note that the order in which we build the resulting list of entries
        # doesn't matter at this stage, but it does need to be consistent.
        # The current order (main, initial) is based on Python 2.7 sort order,
        # which our tests are based on. This could be changed in the future.
        all_entries = data.get_entries()
        entries = all_entries['main'] + all_entries['initial']

        if self.entry_ids:
            # If specific entry IDs have been requested, limit the results
            # to those.
            entries = (
                entry
                for entry in entries
                if (entry.entry_type_id in self.entry_ids and
                    entry.entry_id in self.entry_ids[entry.entry_type_id])
            )

        # See if the caller only wants to fetch entries updated since a given
        # timestamp.
        if since:
            since = dateutil.parser.parse(since)

            if not is_aware(since):
                since = make_aware(since, utc)

            entries = (
                entry
                for entry in entries
                if (entry.updated_timestamp is not None and
                    entry.updated_timestamp.replace(microsecond=0) > since)
            )

        # We can now begin to serialize the payload for all the updates.
        payload = io.BytesIO()
        base_entry_context = None
        needs_issue_summary_table = False

        for entry in entries:
            metadata = {
                'type': 'entry',
                'entryType': entry.entry_type_id,
                'entryID': entry.entry_id,
                'etag': entry.build_etag_data(data, entry=entry),
                'addedTimestamp': entry.added_timestamp,
                'updatedTimestamp': entry.updated_timestamp,
                'modelData': entry.get_js_model_data(),
                'viewOptions': entry.get_js_view_data(),
            }

            if base_entry_context is None:
                # Now that we know the context is needed for entries,
                # we can construct and populate it.
                base_entry_context = super().get_context_data(**kwargs)
                base_entry_context.update(
                    make_review_request_context(request, review_request))

            try:
                html = render_to_string(
                    template_name=entry.template_name,
                    context=dict({
                        'show_entry_statuses_area': (
                            entry.entry_pos == entry.ENTRY_POS_MAIN),
                        'entry': entry,
                    }, **base_entry_context),
                    request=request)

                self._write_update(payload, metadata, html)
            except Exception as e:
                logger.error('Error rendering review request page entry '
                             '%r: %s',
                             entry, e,
                             extra={'request': request})

            if entry.needs_reviews:
                needs_issue_summary_table = True

        # If any of the entries required any information on reviews, then
        # the state of the issue summary table may have changed. We'll need
        # to send this along as well.
        if (needs_issue_summary_table and
            (since is None or
             data.latest_issue_timestamp.replace(microsecond=0) > since)):
            metadata = {
                'type': 'issue-summary-table',
                'updatedTimestamp': data.latest_issue_timestamp,
            }

            html = render_to_string(
                template_name='reviews/review_issue_summary_table.html',
                context={
                    'issue_counts': data.issue_counts,
                    'issues': data.issues,
                },
                request=request)

            self._write_update(payload, metadata, html)

        # The payload's complete. Close it out and send to the client.
        result = payload.getvalue()
        payload.close()

        return HttpResponse(result, content_type='text/plain; charset=utf-8')

    def _write_update(
        self,
        payload: io.BytesIO,
        metadata: dict,
        html: str,
    ) -> None:
        """Write an update to the payload.

        This will format the metadata and HTML for the update and write it.

        Args:
            payload (io.BytesIO):
                The payload to write to.

            metadata (dict):
                The JSON-serializable metadata to write.

            html (str):
                The HTML to write.
        """
        metadata_bytes = (
            json.dumps(metadata,
                       cls=DjbletsJSONEncoder,
                       sort_keys=True)
            .encode('utf-8')
        )
        html_bytes = html.strip().encode('utf-8')

        payload.write(struct.pack(b'<L', len(metadata_bytes)))
        payload.write(metadata_bytes)
        payload.write(struct.pack(b'<L', len(html_bytes)))
        payload.write(html_bytes)
