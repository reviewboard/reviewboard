from __future__ import unicode_literals

import logging

from django.db.models import Q
from django.utils import six
from djblets.gravatars import get_gravatar_url
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)
from djblets.webapi.resources.user import UserResource as DjbletsUserResource

from reviewboard.accounts.backends import get_enabled_auth_backends
from reviewboard.accounts.errors import UserQueryError
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.errors import USER_QUERY_ERROR
from reviewboard.webapi.resources import resources


class UserResource(WebAPIResource, DjbletsUserResource):
    """
    Provides information on registered users.

    If a user's profile is private, the fields ``email``, ``first_name``,
    ``last_name``, and ``fullname`` will be omitted for non-staff users.
    """
    item_child_resources = [
        resources.api_token,
        resources.archived_review_request,
        resources.muted_review_request,
        resources.watched,
    ]

    fields = dict({
        'avatar_url': {
            'type': six.text_type,
            'description': 'The URL for an avatar representing the user.',
            'added_in': '1.6.14',
        },
    }, **DjbletsUserResource.fields)

    hidden_fields = ('email', 'first_name', 'last_name', 'fullname')

    def get_queryset(self, request, local_site_name=None, *args, **kwargs):
        search_q = request.GET.get('q', None)

        for backend in get_enabled_auth_backends():
            try:
                backend.query_users(search_q, request)
            except Exception as e:
                logging.error('Error when calling query_users for auth '
                              'backend %r: %s',
                              backend, e, exc_info=1)

        local_site = self._get_local_site(local_site_name)
        is_list = kwargs.get('is_list', False)

        # When accessing individual users (not is_list) on public local sites,
        # we allow accessing any username. This is so that the links on reviews
        # and review requests from non-members won't be 404. The list is still
        # restricted to members of the site to avoid leaking information.
        if local_site and (is_list or not local_site.public):
            query = local_site.users.filter(is_active=True)
        else:
            query = self.model.objects.filter(is_active=True)

        if search_q:
            q = None

            # Auth backends may have special naming conventions for users that
            # they'd like to be represented in search. If any auth backends
            # implement search_users, prefer that over the built-in searching.
            for backend in get_enabled_auth_backends():
                try:
                    q = backend.search_users(search_q, request)
                except Exception as e:
                    logging.error('Error when calling search_users for auth '
                                  'backend %r: %s',
                                  backend, e, exc_info=1)

                if q:
                    break

            if not q:
                q = Q(username__istartswith=search_q)

                if request.GET.get('fullname', None):
                    q = q | (Q(first_name__istartswith=search_q) |
                             Q(last_name__istartswith=search_q))

            query = query.filter(q)

        return query.extra(select={
            'is_private': ('SELECT is_private FROM accounts_profile '
                           'WHERE accounts_profile.user_id = auth_user.id')
        })

    def serialize_object(self, obj, request=None, *args, **kwargs):
        data = super(UserResource, self).serialize_object(
            obj, request=request, *args, **kwargs)

        if request:
            # Hide user info from anonymous users and non-staff users (if
            # his/her profile is private).
            if not obj.is_profile_visible(request.user):
                for field in self.hidden_fields:
                    del data[field]

        return data

    def serialize_url_field(self, user, **kwargs):
        return local_site_reverse('user', kwargs['request'],
                                  kwargs={'username': user.username})

    def serialize_avatar_url_field(self, user, request=None, **kwargs):
        return get_gravatar_url(request, user)

    def has_access_permissions(self, *args, **kwargs):
        return True

    @webapi_check_local_site
    @webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED, DOES_NOT_EXIST,
                            USER_QUERY_ERROR)
    @webapi_request_fields(
        optional={
            'q': {
                'type': six.text_type,
                'description': 'The string that the username (or the first '
                               'name or last name when using ``fullname``) '
                               'must start with in order to be included in '
                               'the list. This is case-insensitive.',
            },
            'fullname': {
                'type': bool,
                'description': 'Specifies whether ``q`` should also match '
                               'the beginning of the first name or last name.',
            },
        },
        allow_unknown=True
    )
    def get_list(self, *args, **kwargs):
        """Retrieves the list of users on the site.

        This includes only the users who have active accounts on the site.
        Any account that has been disabled (for inactivity, spam reasons,
        or anything else) will be excluded from the list.

        The list of users can be filtered down using the ``q`` and
        ``fullname`` parameters.

        Setting ``q`` to a value will by default limit the results to
        usernames starting with that value. This is a case-insensitive
        comparison.

        If ``fullname`` is set to ``1``, the first and last names will also be
        checked along with the username. ``fullname`` is ignored if ``q``
        is not set.

        For example, accessing ``/api/users/?q=bo&fullname=1`` will list
        any users with a username, first name or last name starting with
        ``bo``.
        """
        try:
            return super(UserResource, self).get_list(*args, **kwargs)
        except UserQueryError as e:
            return USER_QUERY_ERROR.with_message(e.msg)

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Retrieve information on a registered user.

        This mainly returns some basic information (username, full name,
        e-mail address) and links to that user's root Watched Items resource,
        which is used for keeping track of the groups and review requests
        that the user has "starred".
        """
        pass


user_resource = UserResource()
