from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)

from reviewboard.reviews.models import Group
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.errors import INVALID_USER
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.user import UserResource


class ReviewGroupUserResource(UserResource):
    """Provides information on users that are members of a review group."""
    allowed_methods = ('GET', 'POST', 'DELETE')

    policy_id = 'review_group_user'

    def get_queryset(self, request, group_name, local_site_name=None,
                     *args, **kwargs):
        group = Group.objects.get(name=group_name,
                                  local_site__name=local_site_name)
        return group.users.all()

    def has_access_permissions(self, request, user, *args, **kwargs):
        group = resources.review_group.get_object(request, *args, **kwargs)
        return group.is_accessible_by(request.user)

    def has_list_access_permissions(self, request, *args, **kwargs):
        group = resources.review_group.get_object(request, *args, **kwargs)
        return group.is_accessible_by(request.user)

    def has_modify_permissions(self, request, group, username, local_site):
        return (
            resources.review_group.has_modify_permissions(request, group) or
            (request.user.username == username and
             group.is_accessible_by(request.user))
        )

    def has_delete_permissions(self, request, user, *args, **kwargs):
        group = resources.review_group.get_object(request, *args, **kwargs)
        return group.is_mutable_by(request.user)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_USER,
                            NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(required={
        'username': {
            'type': six.text_type,
            'description': 'The user to add to the group.',
            'added_in': '1.6.14',
        },
    })
    def create(self, request, username, *args, **kwargs):
        """Adds a user to a review group."""
        group_resource = resources.review_group

        try:
            group = group_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        local_site = self._get_local_site(kwargs.get('local_site_name', None))

        if (not group_resource.has_access_permissions(request, group) or
            not self.has_modify_permissions(request, group, username,
                                            local_site)):
            return self.get_no_access_error(request)

        try:
            if local_site:
                user = local_site.users.get(username=username)
            else:
                user = User.objects.get(username=username)
        except ObjectDoesNotExist:
            return INVALID_USER

        group.users.add(user)

        return 201, {
            self.item_result_key: user,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_USER,
                            NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        """Removes a user from a review group."""
        group_resource = resources.review_group

        try:
            group = group_resource.get_object(request, *args, **kwargs)
            user = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        local_site = self._get_local_site(kwargs.get('local_site_name', None))

        if (not group_resource.has_access_permissions(request, group) or
            not self.has_modify_permissions(request, group, user.username,
                                            local_site)):
            return self.get_no_access_error(request)

        group.users.remove(user)

        return 204, {}

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Retrieves the list of users belonging to a specific review group.

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
        pass


review_group_user_resource = ReviewGroupUserResource()
