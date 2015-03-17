from __future__ import unicode_literals

from django.http import HttpResponseRedirect
from django.shortcuts import render, render_to_response
from djblets.siteconfig.models import SiteConfiguration
from haystack.inputs import Raw
from haystack.query import SearchQuerySet
from haystack.views import SearchView

from reviewboard.accounts.decorators import check_login_required
from reviewboard.reviews.models import ReviewRequest
from reviewboard.search.indexes import BaseSearchIndex
from reviewboard.site.decorators import check_local_site_access
from reviewboard.site.urlresolvers import local_site_reverse


class RBSearchView(SearchView):
    """Provides search functionality for information on Review Board."""

    template = 'search/results.html'

    ADJACENT_PAGES = 3

    def __init__(self, *args, **kwargs):
        siteconfig = SiteConfiguration.objects.get_current()
        self.enabled = siteconfig.get('search_enable')

        super(RBSearchView, self).__init__(
            load_all=False,
            searchqueryset=SearchQuerySet,
            results_per_page=siteconfig.get('search_results_per_page'),
            *args, **kwargs)

    def __call__(self, request, local_site=None, local_site_name=None,
                 *args, **kwargs):
        """Handles requests to this view.

        This will first check if the search result is just a digit, which is
        assumed to be a review request ID. If it is, the user will be
        redirected to the review request.

        Otherwise, the search will be carried out based on the query.
        """
        self.request = request
        self.local_site = local_site

        query = self.get_query()

        # If the query is an integer, then assume that it's a review request
        # ID that we'll want to redirect to. This mirrors behavior we've had
        # since Review Board 1.7.
        if query.isdigit():
            try:
                review_request = ReviewRequest.objects.for_id(query,
                                                              local_site)
                return HttpResponseRedirect(review_request.get_absolute_url())
            except ReviewRequest.DoesNotExist:
                pass

        if not self.enabled:
            return render(request, 'search/search_disabled.html')

        return super(RBSearchView, self).__call__(request)

    def get_query(self):
        """Return the normalized query string from the request."""
        return self.request.GET.get('q', '').strip()

    def get_results(self):
        """Return a set of results matching the query."""
        sqs = self.searchqueryset()

        if self.query.isdigit():
            sqs = sqs.filter(review_request_id=self.query)
        else:
            sqs = sqs.filter(content=Raw(self.query))

        if self.local_site:
            local_site_id = self.local_site.pk
        else:
            local_site_id = BaseSearchIndex.NO_LOCAL_SITE_ID

        sqs = sqs.filter_and(local_sites__contains=local_site_id)
        sqs = sqs.order_by('-last_updated')

        self.total_hits = len(sqs)

        return sqs

    def extra_context(self):
        """Return extra context for rendering the results list."""
        return {
            'hits_returned': len(self.results),
            'total_hits': self.total_hits,
        }

    def create_response(self):
        """Create a response based on the search results."""
        if not self.query:
            return HttpResponseRedirect(
                local_site_reverse('all-review-requests',
                                   request=self.request))

        if self.query.isdigit() and self.results:
            return HttpResponseRedirect(
                self.results[0].object.get_absolute_url())

        paginator, page = self.build_page()
        page_nums = range(max(1, page.number - self.ADJACENT_PAGES),
                          min(paginator.num_pages,
                              page.number + self.ADJACENT_PAGES) + 1)

        context = {
            'query': self.query,
            'page': page,
            'paginator': paginator,
            'is_paginated': page.has_other_pages(),
            'show_first_page': 1 not in page_nums,
            'show_last_page': paginator.num_pages not in page_nums,
            'page_numbers': page_nums,
        }
        context.update(self.extra_context())

        return render_to_response(
            self.template, context,
            context_instance=self.context_class(self.request))


@check_login_required
@check_local_site_access
def search(*args, **kwargs):
    """Provide results for a given search."""
    search_view = RBSearchView()
    return search_view(*args, **kwargs)
