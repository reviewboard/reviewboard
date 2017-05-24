from __future__ import unicode_literals

from django.db.models import Q
from django.utils import six
from djblets.webapi.decorators import webapi_request_fields
from djblets.webapi.resources.user import UserResource as DjbletsUserResource

from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)


class SearchResource(WebAPIResource, DjbletsUserResource):
    """
    Provides information on users, groups and review requests.

    This is the resource for the autocomplete widget for quick search. This
    resource helps filter for users, groups and review requests.
    """
    added_in = '1.6'

    name = 'search'
    singleton = True

    MIN_SUMMARY_LEN = 4

    def has_access_permissions(self, request, *args, **kwargs):
        return True

    @webapi_request_fields(
        optional={
            'q': {
                'type': six.text_type,
                'description': 'The text to search for.',
            },
            'displayname': {
                'type': bool,
                'description': 'Whether or not to include groups whose '
                               'display_name field includes the search text.',
            },
            'fullname': {
                'type': bool,
                'description': 'Whether or not to include users whose full '
                               'name includes the search text.',
            },
            'id': {
                'type': bool,
                'description': 'Whether or not to include review requests '
                               'with IDs that start with the given search '
                               'text.',
            },
            'max_results': {
                'type': int,
                'description': 'The maximum number of results to return '
                                'for each type of matching object. By '
                                'default, this is 25. There is a hard limit '
                                'of 200.',
            },
        },
        allow_unknown=True,
    )
    @webapi_check_local_site
    @webapi_check_login_required
    def get(self, request, displayname=None, fullname=None, id=None,
            max_results=None, q=None, local_site_name=None, *args, **kwargs):
        """Returns information on users, groups and review requests.

        This is used by the autocomplete widget for quick search to get
        information on users, groups and review requests. This function returns
        users' first name, last name and username, groups' name and display
        name, and review requests' ID and summary.
        """
        q = request.GET.get('q', None)
        local_site = self._get_local_site(local_site_name)

        if local_site:
            query_users = local_site.users.filter(is_active=True)
        else:
            query_users = self.model.objects.filter(is_active=True)

        query_groups = Group.objects.filter(local_site=local_site)
        query_review_requests = \
            ReviewRequest.objects.filter(local_site=local_site)

        if q:
            # Try to match users.
            parts = q.split(' ', 1)

            query = Q()

            if len(parts) > 1:
                query |= ((Q(first_name__istartswith=parts[0]) &
                           Q(last_name__istartswith=parts[1])) |
                          (Q(first_name__istartswith=parts[1]) &
                           Q(last_name__istartswith=parts[0])))
            else:
                query |= (Q(username__istartswith=q) |
                          Q(first_name__istartswith=q) |
                          Q(last_name__istartswith=q))

            if fullname:
                query = query | (Q(first_name__istartswith=q) |
                                 Q(last_name__istartswith=q))

            query_users = query_users.filter(query)

            # Try to match groups.
            query = (Q(name__istartswith=q) |
                     Q(display_name__istartswith=q))

            if displayname:
                query = query | Q(display_name__istartswith=q)

            query_groups = query_groups.filter(query)

            # Try to match summaries or IDs.
            query = Q(id__istartswith=q)

            if len(q) >= self.MIN_SUMMARY_LEN:
                query |= Q(summary__istartswith=q)

            if id:
                query |= Q(id__istartswith=id)

            query_review_requests = query_review_requests.filter(query)

        max_results = min((max_results or 25), 200)

        return 200, {
            self.name: {
                'users': query_users[:max_results],
                'groups': query_groups[:max_results],
                'review_requests': query_review_requests[:max_results],
            },
        }


search_resource = SearchResource()
