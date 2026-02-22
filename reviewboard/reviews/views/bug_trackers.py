"""Views for interacting with bug trackers."""

import re
from typing import Any, Dict

from django.http import (HttpRequest,
                         HttpResponse,
                         HttpResponseNotFound)
from django.utils.html import escape, strip_tags
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView, View

from reviewboard.hostingsvcs.bugtracker import BugTracker
from reviewboard.reviews.markdown_utils import render_markdown
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin
from reviewboard.site.urlresolvers import local_site_reverse


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
        repository = review_request.repository

        if not repository:
            return HttpResponseNotFound(
                _('Review Request does not have an associated repository'))

        bug_tracker = repository.bug_tracker_service

        if not bug_tracker:
            return HttpResponseNotFound(
                _('Unable to find bug tracker service'))

        if not isinstance(bug_tracker, BugTracker):
            return HttpResponseNotFound(
                _('Bug tracker %s does not support metadata')
                % bug_tracker.name)

        self.bug_id = bug_id
        self.bug_info = bug_tracker.get_bug_info(repository, bug_id)

        if (not self.bug_info.get('summary') and
            not self.bug_info.get('description')):
            return HttpResponseNotFound(
                _('No bug metadata found for bug %(bug_id)s on bug tracker '
                  '%(bug_tracker)s') % {
                    'bug_id': bug_id,
                    'bug_tracker': bug_tracker.name,
                })

        return super().get(request, **kwargs)

    def get_context_data(
        self,
        **kwargs,
    ) -> Dict[str, Any]:
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

        bug_url = local_site_reverse(
            'bug_url',
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
        repository = self.review_request.repository

        if not repository:
            return HttpResponseNotFound(
                _('Review Request does not have an associated repository'))

        # Need to create a custom HttpResponse because a non-HTTP url scheme
        # will cause HttpResponseRedirect to fail with a "Disallowed Redirect".
        response = HttpResponse(status=302)
        response['Location'] = repository.bug_tracker % bug_id

        return response
