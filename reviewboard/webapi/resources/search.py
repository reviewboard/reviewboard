from __future__ import unicode_literals

from django.db.models import Q
from djblets.webapi.resources import UserResource as DjbletsUserResource

from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)


class SearchResource(WebAPIResource, DjbletsUserResource):
    """
    Provides information on users, groups and review requests.

    This is the resource for the autocomplete widget for
    quick search. This resource helps filter for
    users, groups and review requests.
    """
    name = 'search'
    singleton = True

    def has_access_permissions(self, request, *args, **kwargs):
        return True

    @webapi_check_local_site
    @webapi_check_login_required
    def get(self, request, local_site_name=None, fullname=None, q=None,
            displayname=None, id=None, *args, **kwargs):
        """Returns information on users, groups and review requests.

        This is used by the autocomplete widget for quick search to
        get information on users, groups and review requests. This
        function returns users' first name, last name and username,
        groups' name and display name, and review requests' ID and
        summary.
        """
        search_q = request.GET.get('q', None)
        local_site = self._get_local_site(local_site_name)
        if local_site:
            query = local_site.users.filter(is_active=True)
        else:
            query = self.model.objects.filter(is_active=True)

        if search_q:
            q = (Q(username__istartswith=search_q) |
                 Q(first_name__istartswith=search_q) |
                 Q(last_name__istartswith=search_q))

            if request.GET.get('fullname', None):
                q = q | (Q(first_name__istartswith=search_q) |
                         Q(last_name__istartswith=search_q))

            query = query.filter(q)

        search_q = request.GET.get('q', None)
        local_site = self._get_local_site(local_site_name)
        query_groups = Group.objects.filter(local_site=local_site)

        if search_q:
            q = (Q(name__istartswith=search_q) |
                 Q(display_name__istartswith=search_q))

            if request.GET.get('displayname', None):
                q = q | Q(display_name__istartswith=search_q)

            query_groups = query_groups.filter(q)

        search_q = request.GET.get('q', None)
        query_review_requests = \
            ReviewRequest.objects.filter(local_site=local_site)

        if search_q:
            q = (Q(id__istartswith=search_q) |
                 Q(summary__icontains=search_q))

            if request.GET.get('id', None):
                q = q | Q(id__istartswith=search_q)

            query_review_requests = query_review_requests.filter(q)

        return 200, {
            self.name: {
                'users': query,
                'groups': query_groups,
                'review_requests': query_review_requests,
            },
        }


search_resource = SearchResource()
