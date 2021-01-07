"""Views for searching."""

from __future__ import unicode_literals

from collections import OrderedDict

from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import six
from haystack.generic_views import SearchView
from haystack.query import SearchQuerySet

from reviewboard.accounts.mixins import (CheckLoginRequiredViewMixin,
                                         UserProfileRequiredViewMixin)
from reviewboard.avatars import avatar_services
from reviewboard.reviews.models import ReviewRequest
from reviewboard.search import search_backend_registry
from reviewboard.search.forms import RBSearchForm
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.site.mixins import CheckLocalSiteAccessViewMixin


class RBSearchView(CheckLoginRequiredViewMixin,
                   CheckLocalSiteAccessViewMixin,
                   UserProfileRequiredViewMixin,
                   SearchView):
    """The Review Board search view."""

    template_name = 'search/results.html'
    disabled_template_name = 'search/search_disabled.html'
    form_class = RBSearchForm

    load_all = False

    # This is normally set on Haystack's SearchMixin class to an instance,
    # at which point the backend loads and is then reused for all queries.
    # Not great, since that assumes the backend will never change. Not a
    # healthy assumption for us. So we clear it out here and set it on dispatch
    # instead.
    queryset = None

    ADJACENT_PAGES = 5

    @property
    def paginate_by(self):
        """The number of search results per page."""
        return search_backend_registry.results_per_page

    def dispatch(self, request, local_site=None, *args, **kwargs):
        """Dispatch the view.

        If search is disabled, the search will not be performed and the user
        will be informed.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            local_site (reviewboard.site.models.LocalSite):
                The LocalSite on which the search is being performed.

            *args (tuple, unused):
                Ignored positional arguments.

            **kwargs (dict, unused):
                Ignored keyword arguments.

        Returns:
            django.http.HttpResponse:
            The HTTP response for the search.
        """
        if not search_backend_registry.search_enabled:
            return render(request, self.disabled_template_name)

        self.queryset = SearchQuerySet()

        form_class = self.get_form_class()
        form = form_class(user=request.user,
                          local_site=local_site,
                          **self.get_form_kwargs())

        if not form.is_valid():
            return self.form_invalid(form)

        query = form.cleaned_data.get(self.search_field, '')

        if not query:
            return HttpResponseRedirect(
                local_site_reverse('all-review-requests',
                                   local_site=local_site),
            )

        if query.isdigit():
            # If the query is an integer, then assume that it's a review
            # request ID that we'll want to redirect to. This mirrors behavior
            # we've had since Review Board 1.7.
            try:
                review_request = ReviewRequest.objects.for_id(query,
                                                              local_site)
            except ReviewRequest.DoesNotExist:
                pass
            else:
                if review_request.is_accessible_by(self.request.user,
                                                   local_site=local_site,
                                                   request=request):
                    return HttpResponseRedirect(
                        review_request.get_absolute_url()
                    )

        return self.form_valid(form)

    def get_context_data(self, form=None, **kwargs):
        """Return context data for rendering the view.

        Args:
            form (reviewboard.search.forms.RBSearchForm):
                The search form instance.

                This will be included in the returned dictionary.

            **kwargs (dict):
                Additional context to be added to the returned dictionary.

        Returns:
            dict:
            The context dictionary.
        """
        context = super(RBSearchView, self).get_context_data(form=form,
                                                             **kwargs)

        paginator = context['paginator']
        page_obj = context['page_obj']
        object_list = context['object_list']

        page_nums = range(max(1, page_obj.number - self.ADJACENT_PAGES),
                          min(paginator.num_pages,
                              page_obj.number + self.ADJACENT_PAGES) + 1)

        active_filters = form.cleaned_data.get('model_filter',
                                               [form.FILTER_ALL])

        context.update({
            'filter_types': OrderedDict(
                (filter_id, dict(active=(filter_id in active_filters),
                                 **filter_type))
                for filter_id, filter_type in six.iteritems(form.FILTER_TYPES)
            ),
            'hits_returned': len(object_list),
            'page_numbers': page_nums,
            'show_first_page': 1 not in page_nums,
            'show_last_page': paginator.num_pages not in page_nums,
        })

        return context

    def render_to_response(self, context, **response_kwargs):
        """Render the search page.

        Args:
            context (dict):
                A dictionary of context from :py:meth:`get_context_data`.

            **response_kwargs (dict);
                Keyword arguments to be passed to the response class.

        Returns:
            django.http.HttpResponse:
            The rendered response.
        """
        show_users = False

        # We only need to fetch users if the search is for just users or
        # both users and review requests (i.e., the '' ID).
        if avatar_services.avatars_enabled:
            show_users = any(
                filter_type['active'] and User in filter_type['models']
                for filter_type in six.itervalues(context['filter_types'])
            )

        if show_users:
            page_obj = context['page_obj']

            user_pks = {
                int(result.pk)
                for result in page_obj
                if result.content_type() == 'auth.user'
            }

            users = {
                user.pk: user
                for user in (
                    User.objects
                    .filter(pk__in=user_pks)
                    .select_related('profile')
                )
            }

            for result in page_obj:
                if result.content_type() == 'auth.user':
                    result.user = users[int(result.pk)]

        return super(RBSearchView, self).render_to_response(context,
                                                            **response_kwargs)
