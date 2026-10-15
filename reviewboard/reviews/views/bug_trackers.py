"""Views for interacting with bug trackers."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
    JsonResponse,
)
from django.utils.html import escape, strip_tags
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView, View

from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.hostingsvcs.models import (
    ConfiguredBugTracker,
    SENTINEL_BUG_TRACKER_SERVICE_NAME,
)
from reviewboard.reviews.markdown_utils import render_markdown
from reviewboard.reviews.models.bug import Bug
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from typing import Any

    from reviewboard.reviews.models import ReviewRequest


def _resolve_bug_tracker(
    request: HttpRequest,
    review_request: ReviewRequest,
    bug_tracker_id: int,
) -> tuple[ConfiguredBugTracker | None, HttpResponse | None]:
    """Resolve a bug tracker for a tracker-qualified bug view.

    This checks the tracker's existence and enabled state, the Local
    Site, and the requesting user's conditions.

    Version Added:
        9.0

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        review_request (reviewboard.reviews.models.ReviewRequest):
            The review request the bug is viewed on.

        bug_tracker_id (int):
            The ID of the bug tracker.

    Returns:
        tuple:
        A 2-tuple of:

        Tuple:
            0 (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker. If an error occurred, this will be ``None``.

            1 (django.http.HttpResponse):
                An error response. If the tracker resolved, this will be
                ``None``.
    """
    bug_tracker = (
        ConfiguredBugTracker.objects
        .filter(pk=bug_tracker_id,
                enabled=True,
                local_site=review_request.local_site_id)
        .exclude(service_name=SENTINEL_BUG_TRACKER_SERVICE_NAME)
        .first()
    )

    if bug_tracker is None:
        return None, HttpResponseNotFound(
            _('Unable to find bug tracker'))

    if not bug_tracker.is_usable_by(request.user, request=request):
        return None, HttpResponseForbidden(
            _('You do not have access to this bug tracker'))

    return bug_tracker, None


class BugInfoboxView(ReviewRequestViewMixin, TemplateView):
    """Displays information on a bug, for use in bug pop-up infoboxes.

    This is meant to be embedded in other pages, rather than being
    a standalone page.
    """

    template_name = 'reviews/bug_infobox.html'

    HTML_ENTITY_RE = re.compile(r'(&[a-z]+;)')
    HTML_ENTITY_MAP = {
        '&quot;': '"',
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
    }

    def get(
        self,
        request: HttpRequest,
        bug_id: str,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests for this view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            bug_id (str):
                The ID of the bug to view.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client.

            If details on a bug could not be found or fetching bug information
            is not supported, this will return a a :http:`404`.
        """
        request = self.request
        review_request = self.review_request
        bug_tracker_id = kwargs.pop('bug_tracker_id', None)

        self.bug_id = bug_id
        self.bug_tracker_id = bug_tracker_id

        if bug_tracker_id is not None:
            # This is the tracker-qualified route.
            tracker, error_response = _resolve_bug_tracker(
                request, review_request, bug_tracker_id)

            if error_response is not None:
                return error_response

            if tracker is None:
                return HttpResponseNotFound(
                    _('Unable to find bug tracker with ID {}')
                    .format(bug_tracker_id))

            service = tracker.service
            assert isinstance(service, BaseHostingService)

            if not service.supports_bug_info:
                return HttpResponseNotFound(
                    _('Bug tracker {} does not support metadata')
                    .format(tracker.name))

            self.bug_info = service.get_bug_info(config=tracker,
                                                 bug_id=bug_id)
            bug_tracker_name = tracker.name
        else:
            repository = review_request.repository

            if not repository:
                return HttpResponseNotFound(
                    _('Review Request does not have an associated '
                      'repository'))

            default_bug_tracker = repository.get_default_bug_tracker()

            if default_bug_tracker is None:
                return HttpResponseNotFound(
                    _('Unable to find bug tracker service'))

            bug_tracker = default_bug_tracker.service

            if not isinstance(bug_tracker, BaseBugTracker):
                return HttpResponseNotFound(
                    _('Bug tracker {} does not support metadata')
                    .format(bug_tracker.name))

            self.bug_info = bug_tracker.get_bug_info(
                repository=repository,
                bug_id=bug_id)
            bug_tracker_name = bug_tracker.name

        if (not self.bug_info.get('summary') and
            not self.bug_info.get('description')):
            return HttpResponseNotFound(
                _(
                    'No bug metadata found for bug {bug_id} on bug tracker '
                    '{bug_tracker}'
                ).format(bug_id=bug_id, bug_tracker=bug_tracker_name))

        return super().get(request, **kwargs)

    def get_context_data(
        self,
        **kwargs,
    ) -> dict[str, Any]:
        """Return context data for the template.

        Args:
            **kwargs (dict):
                Keyword arguments passed to the view.

        Returns:
            dict:
            The resulting context data for the template.
        """
        description_text_format = self.bug_info.get('description_text_format',
                                                    'plain')
        description = self.normalize_text(self.bug_info['description'],
                                          description_text_format)

        if (bug_tracker_id := self.bug_tracker_id) is not None:
            bug_url = local_site_reverse(
                'bug_tracker_bug_url',
                local_site=self.local_site,
                args=[self.review_request.display_id, bug_tracker_id,
                      self.bug_id])
        else:
            bug_url = local_site_reverse(
                'bug_url',
                local_site=self.local_site,
                args=[self.review_request.display_id, self.bug_id])

        context_data = super().get_context_data(**kwargs)
        context_data.update({
            'bug_id': self.bug_id,
            'bug_url': bug_url,
            'bug_description': description,
            'bug_description_rich_text': description_text_format == 'markdown',
            'bug_status': self.bug_info['status'],
            'bug_summary': self.bug_info['summary'],
        })

        return context_data

    def normalize_text(
        self,
        text: str,
        text_format: str,
    ) -> SafeString:
        """Normalize the text for display.

        Based on the text format, this will sanitize and normalize the text
        so it's suitable for rendering to HTML.

        HTML text will have tags stripped away and certain common entities
        replaced.

        Markdown text will be rendered using our default Markdown parser
        rules.

        Plain text (or any unknown text format) will simply be escaped and
        wrapped, with paragraphs left intact.

        Args:
            text (str):
                The text to normalize for display.

            text_format (str):
                The text format. This should be one of ``html``, ``markdown``,
                or ``plain``.

        Returns:
            django.utils.safestring.SafeString:
            The resulting text, safe for rendering in HTML.
        """
        if text_format == 'html':
            # We want to strip the tags away, but keep certain common entities.
            text = (
                escape(self.HTML_ENTITY_RE.sub(
                    lambda m: (self.HTML_ENTITY_MAP.get(m.group(0)) or
                               m.group(0)),
                    strip_tags(text)))
                .replace('\n\n', '<br><br>'))
        elif text_format == 'markdown':
            # This might not know every bit of Markdown that's thrown at us,
            # but we'll do the best we can.
            text = render_markdown(text)
        else:
            # Should be plain text, but don't trust it.
            text = escape(text).replace('\n\n', '<br><br>')

        return mark_safe(text)


class TrackedBugInfoView(ReviewRequestViewMixin, View):
    """Provides metadata for bugs on a bug tracker, as JSON.

    This backs the detailed bug tables on a review request. Metadata
    cached locally is served as-is, and anything stale is refreshed from
    the bug tracker.

    Version Added:
        9.0
    """

    #: The maximum number of bugs that can be looked up in one request.
    MAX_BUGS = 100

    def get(
        self,
        request: HttpRequest,
        bug_tracker_id: int,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests for this view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            bug_tracker_id (int):
                The ID of the bug tracker the bugs are on.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The metadata for the requested bugs, keyed off the bug ID.
        """
        tracker, error_response = _resolve_bug_tracker(
            request, self.review_request, bug_tracker_id)

        if error_response is not None:
            return error_response

        assert tracker is not None

        bug_ids = [
            bug_id
            for bug_id in request.GET.get('bug-ids', '').split(',')
            if bug_id
        ][:self.MAX_BUGS]

        if bug_ids:
            metadata = Bug.objects.fetch_bug_info(bug_tracker=tracker,
                                                  bug_ids=bug_ids)
        else:
            metadata = {}

        return JsonResponse({
            'bugs': metadata,
        })


class BugURLRedirectView(ReviewRequestViewMixin, View):
    """Redirects the user to an external bug report."""

    def get(
        self,
        request: HttpRequest,
        bug_id: str,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests for this view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            bug_id (str):
                The ID of the bug report to redirect to.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response redirecting the client.
        """
        bug_tracker_id = kwargs.get('bug_tracker_id')

        if bug_tracker_id is not None:
            # This is the tracker-qualified route.
            tracker, error_response = _resolve_bug_tracker(
                request, self.review_request, bug_tracker_id)

            if error_response is not None:
                return error_response

            bug_url = tracker.get_bug_url(bug_id)

            if not bug_url:
                return HttpResponseNotFound(
                    _('The bug tracker does not have a URL for this bug'))

            # Need to create a custom HttpResponse because a non-HTTP url
            # scheme will cause HttpResponseRedirect to fail with a
            # "Disallowed Redirect".
            response = HttpResponse(status=302)
            response['Location'] = bug_url

            return response

        repository = self.review_request.repository

        if not repository:
            return HttpResponseNotFound(
                _('Review Request does not have an associated repository'))

        # Need to create a custom HttpResponse because a non-HTTP url scheme
        # will cause HttpResponseRedirect to fail with a "Disallowed Redirect".
        response = HttpResponse(status=302)
        response['Location'] = repository.bug_tracker % bug_id

        return response
