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

    def has_access_permissions(self, *args, **kwargs):
        """Return whether or not users have access to this resource.

        This resource is accessible to any users that have access to the API.

        Args:
            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Returns:
            bool:
            Always ``True``.
        """
        return True

    @webapi_request_fields(
        optional={
            'q': {
                'type': six.text_type,
                'description': 'The text to search for.',
            },
            'displayname': {
                'type': bool,
                'description': 'This field is deprecated and ignored. It '
                               'will be removed in a future release of '
                               'Review Board.',
            },
            'fullname': {
                'type': bool,
                'description': 'Whether or not to include users whose full '
                               'name includes the search text.',
            },
            'id': {
                'type': int,
                'description': 'A specific review request ID to search for.',
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
    def get(self, request, max_results=None, *args, **kwargs):
        """Returns information on users, groups and review requests.

        This is used by the autocomplete widget for quick search to get
        information on users, groups and review requests. This function returns
        users' first name, last name and username, groups' name and display
        name, and review requests' ID and summary.
        """
        max_results = min((max_results or 25), 200)

        try:
            # We have to keep the parameter named id for backwards
            # compatibility, but it would override the builtin of the same
            # name.
            kwargs['id_q'] = kwargs.pop('id')
        except KeyError:
            pass

        return 200, {
            self.name: {
                'users': self._search_users(
                    request=request,
                    *args,
                    **kwargs)[:max_results],
                'groups': self._search_groups(
                    request=request,
                    *args,
                    **kwargs)[:max_results],
                'review_requests': self._search_review_requests(
                    request=request,
                    *args,
                    **kwargs)[:max_results],
            },
        }

    def _search_users(self, local_site=None, fullname=None, q=None, *args,
                      **kwargs):
        """Search for users and return the results.

        Args:
            local_site (reviewboard.site.models.LocalSite, optional):
                The current local site.

            fullname (bool, optional):
                Whether or not to perform a search against the users' full
                names.

            q (unicode, optional):
                The search text.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Returns:
            django.db.models.query.QuerySet:
            A query set for users matching the given arguments.
        """
        if local_site:
            users = local_site.users.filter(is_active=True)
        else:
            users = self.model.objects.filter(is_active=True)

        if q:
            parts = q.split(' ', 1)

            if len(parts) > 1:
                query = (
                    (Q(first_name__istartswith=parts[0]) &
                     Q(last_name__istartswith=parts[1])) |
                    (Q(first_name__istartswith=parts[1]) &
                     Q(last_name__istartswith=parts[0]))
                )

                if fullname:
                    query |= (Q(first_name__istartswith=q) |
                              Q(last_name__istartswith=q))
            else:
                query = (Q(username__istartswith=q) |
                         Q(first_name__istartswith=q) |
                         Q(last_name__istartswith=q))

            users = users.filter(query)

        return users

    def _search_groups(self, request, local_site=None, q=None, *args,
                       **kwargs):
        """Search for review groups and return the results.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            local_site (reviewboard.site.models.LocalSite, optional):
                The current local site.

            q (unicode, optional):
                The search text.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Returns:
            django.db.models.query.QuerySet:
            A query set for review groups matching the given arguments.
        """
        groups = Group.objects.accessible(request.user, local_site=local_site)

        if q:
            groups = groups.filter(
                Q(name__istartswith=q) |
                Q(display_name__istartswith=q)
            )

        # Group.objects.accessible only respects visible_only for
        # non-superusers. We add this here to make the behavior consistent.
        return groups.filter(visible=True)

    def _search_review_requests(self, request, local_site=None, q=None,
                                id_q=None, *args, **kwargs):
        """Search for a user and return the results.

        Args:
            local_site (reviewboard.site.models.LocalSite, optional):
                The current local site.

            q (unicode, optional):
                The search text.

            id_q (int, optional):
                An optional ID to search against review request IDs.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Returns:
            django.db.models.query.QuerySet:
            A query set for users matching the given arguments.
        """
        review_requests = ReviewRequest.objects.public(filter_private=True,
                                                       user=request.user,
                                                       local_site=local_site,
                                                       status=None)

        query = Q()

        if q:
            if local_site:
                query |= Q(local_id__istartswith=q)
            else:
                query |= Q(id__startswith=q)

            if len(q) >= self.MIN_SUMMARY_LEN:
                query |= Q(summary__istartswith=q)

        if id_q:
            if local_site:
                query |= Q(local_id__startswith=id_q)
            else:
                query |= Q(id__startswith=id_q)

        return review_requests.filter(query)


search_resource = SearchResource()
