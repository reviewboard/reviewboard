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
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.errors import INVALID_USER
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.user import UserResource


class ReviewGroupUserResource(UserResource):
    """Provides information on users that are members of a review group."""

    name = 'review_group_user'
    item_result_key = 'user'
    list_result_key = 'users'
    uri_name = 'users'

    # We do not want the watched resource to be available under this resource
    # as it will have the wrong URL and does not make sense as a sub-resource;
    # we will be serializing a link to the user resource and it can be found
    # from there.
    item_child_resources = []

    allowed_methods = ('GET', 'POST', 'DELETE')

    policy_id = 'review_group_user'

    def get_queryset(self, request, group_name, local_site_name=None,
                     *args, **kwargs):
        group = Group.objects.get(name=group_name,
                                  local_site__name=local_site_name)
        return group.users.all()

    def get_href_parent_ids(self, obj, **kwargs):
        """Return the href parent IDs for the object.

        Args:
            obj (django.contrib.auth.models.User):
                The user.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            The parent IDs to be used to determine the href of the resource.
        """
        # Since we do not have a direct link to the model parent (the
        # Group.users field is a many-to-many field so we cannot use it because
        # the reverse relation is not unique), we have to manually generate the
        # parent IDs from the parent resource.
        parent_id_key = self._parent_resource.uri_object_key
        return {
            parent_id_key: kwargs[parent_id_key],
        }

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        """Return the related links for the resource.

        Args:
            obj (django.contrib.auth.models.User, optional):
                The user for which links are being generated.

            request (django.http.HttpRequest):
                The current HTTP request.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            The related links for the resource.
        """
        links = super(ReviewGroupUserResource, self).get_related_links(
            obj, request, *args, **kwargs)

        # We only want the 'user' link when this is an item resource.
        if self.uri_object_key in kwargs:
            username = kwargs[self.uri_object_key]
            links['user'] = {
                'href': resources.user.get_item_url(username=username),
                'method': 'GET',
            }

        return links

    def get_serializer_for_object(self, obj):
        """Return the serializer for an object.

        If the object is a :py:class:`~django.contrib.auth.models.User`
        instance, we will serialize it (instead of the
        :py:class:`~reviewboard.webapi.resources.user.UserResource` resource
        so that the links will be correct. Otherwise, the POST and DELETE links
        will be for the actual user instead of for this resource.

        Args:
            obj (django.db.models.base.Model):
                The model being serialized.

        Returns:
            djblets.webapi.resources.base.WebAPIResource:
            The resource that should be used to serialize the object.
        """
        if isinstance(obj, User):
            return self

        return super(ReviewGroupUserResource, self).get_serializer_for_object(
            obj)

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
    @webapi_request_fields(optional={
        'fullname': {
            'type': bool,
            'description': ''
        },
        'q': {
            'type': six.text_type,
            'description': 'Limit the results to usernames starting with the '
                           'provided value. This is case-insensitive.',
        },
    })
    @augment_method_from(UserResource)
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
