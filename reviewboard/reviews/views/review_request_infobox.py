"""View for rendering the review request infobox."""

from typing import Any, Dict

from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView

from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import ReviewRequest
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin
from reviewboard.site.urlresolvers import local_site_reverse


class ReviewRequestInfoboxView(ReviewRequestViewMixin, TemplateView):
    """Display a review request info popup.

    This produces the information needed to be displayed in a summarized
    information box upon hovering over a link to a review request.

    This is meant to be embedded in other pages, rather than being
    a standalone page.
    """

    template_name = 'reviews/review_request_infobox.html'

    MAX_REVIEWS = 3

    def get_context_data(
        self,
        **kwargs,
    ) -> Dict[str, Any]:
        """Handle HTTP GET requests for this view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response containing the infobox, or an error if the
            infobox could not be provided.
        """
        review_request = self.review_request
        draft = review_request.get_draft(self.request.user)

        # We only want to show one label. If there's a draft, then that's
        # the most important information, so we'll only show that. Otherwise,
        # we'll show the submitted/discarded state.
        label = None

        if draft:
            label = ('review-request-infobox-label-draft', _('Draft'))
        elif review_request.status == ReviewRequest.SUBMITTED:
            label = ('review-request-infobox-label-submitted', _('Submitted'))
        elif review_request.status == ReviewRequest.DISCARDED:
            label = ('review-request-infobox-label-discarded', _('Discarded'))

        if label:
            label = format_html('<label class="{0}">{1}</label>', *label)

        # Fetch information on the reviews for this review request.
        review_count = (
            review_request.reviews
            .filter(public=True, base_reply_to__isnull=True)
            .count()
        )

        # Fetch information on the draft for this review request.
        diffset = None

        if draft and draft.diffset_id:
            diffset = draft.diffset

        if not diffset and review_request.diffset_history_id:
            try:
                diffset = (
                    DiffSet.objects
                    .filter(history__pk=review_request.diffset_history_id)
                    .latest()
                )
            except DiffSet.DoesNotExist:
                pass

        if diffset:
            diff_url = '%s#index_header' % local_site_reverse(
                'view-diff-revision',
                args=[review_request.display_id, diffset.revision],
                local_site=review_request.local_site)
        else:
            diff_url = None

        return {
            'review_request': review_request,
            'review_request_label': label or '',
            'review_request_details': draft or review_request,
            'issue_total_count': (review_request.issue_open_count +
                                  review_request.issue_resolved_count +
                                  review_request.issue_dropped_count +
                                  review_request.issue_verifying_count),
            'review_count': review_count,
            'diffset': diffset,
            'diff_url': diff_url,
        }
