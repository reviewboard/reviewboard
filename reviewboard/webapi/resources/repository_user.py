"""API resource for managing a repository's user ACL.

Version Added:
    4.0.11
"""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)
from djblets.webapi.fields import BooleanFieldType, StringFieldType

from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.errors import INVALID_USER
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.user import UserResource


class RepositoryUserResource(UserResource):
    """Provides information on users who are allowed access to a repository.

    Version Added:
        4.0.11
    """

    name = 'repository_user'
    item_result_key = 'user'
    list_result_key = 'users'
    uri_name = 'users'

    # We do not want the watched resource to be available under this resource
    # as it will have the wrong URL and does not make sense as a sub-resource;
    # we will be serializing a link to the user resource and it can be found
    # from there.
    item_child_resources = []

    allowed_methods = ('GET', 'POST', 'DELETE')

    policy_id = 'repository_user'

    def get_queryset(self, request, *args, **kwargs):
        """Return a queryset for the repository users.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments passed through to the parent resource.

            **kwargs (dict):
                Keyword arguments passed through to the parent resource.

        Returns:
            django.db.models.query.QuerySet:
            The queryset for the users.
        """
        try:
            repository = resources.repository.get_object(request, *args,
                                                         **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        return repository.users.all()

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
        # Repository.users field is a many-to-many field so we cannot use it
        # because the reverse relation is not unique), we have to manually
        # generate the parent IDs from the parent resource.
        parent_id_key = self._parent_resource.uri_object_key

        return {
            parent_id_key: kwargs[parent_id_key],
        }

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        """Return the related links for the resource.

        Args:
            obj (django.contrib.auth.models.User, optional):
                The user for which links are being generated.

            request (django.http.HttpRequest, optional):
                The current HTTP request.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            The related links for the resource.
        """
        links = super(RepositoryUserResource, self).get_related_links(
            obj, request=request, *args, **kwargs)

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

        return super(RepositoryUserResource, self).get_serializer_for_object(
            obj)

    def has_access_permissions(self, request, user, *args, **kwargs):
        """Return whether the item resource can be accessed.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            user (django.contrib.auth.models.User, unused):
                The user in the resource item URL. This is unused because we
                only care about repository-level access here.

            *args (tuple):
                Positional arguments to pass to the parent resource.

            **kwargs (dict):
                Keyword arguments to pass to the parent resource.

        Returns:
            bool:
            Whether the current user can access the item resource.
        """
        repository = resources.repository.get_object(request, *args, **kwargs)
        return repository.is_mutable_by(request.user)

    def has_list_access_permissions(self, request, *args, **kwargs):
        """Return whether the list resource can be accessed.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments to pass to the parent resource.

            **kwargs (dict):
                Keyword arguments to pass to the parent resource.

        Returns:
            bool:
            Whether the current user can access the list resource.
        """
        repository = resources.repository.get_object(request, *args, **kwargs)
        return repository.is_mutable_by(request.user)

    def has_modify_permissions(self, request, *args, **kwargs):
        """Return whether the resource can be modified.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments to pass to the parent resource.

            **kwargs (dict):
                Keyword arguments to pass to the parent resource.

        Returns:
            bool:
            Whether the current user can modify the resource.
        """
        repository = resources.repository.get_object(request, *args, **kwargs)
        return repository.is_mutable_by(request.user)

    def has_delete_permissions(self, request, *args, **kwargs):
        """Return whether the resource can be deleted.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments to pass to the parent resource.

            **kwargs (dict):
                Keyword arguments to pass to the parent resource.

        Returns:
            bool:
            Whether the current user can delete the resource.
        """
        repository = resources.repository.get_object(request, *args, **kwargs)
        return repository.is_mutable_by(request.user)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_USER, NOT_LOGGED_IN,
                            PERMISSION_DENIED)
    @webapi_request_fields(required={
        'username': {
            'type': StringFieldType,
            'description': 'The user to add to the repository ACL.',
        },
    })
    def create(self, request, username, local_site_name=None, *args, **kwargs):
        """Adds a user to the repository ACL."""
        repo_resource = resources.repository

        try:
            repository = repo_resource.get_object(
                request, local_site_name=local_site_name, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not repo_resource.has_modify_permissions(request, repository):
            return self.get_no_access_error(request)

        local_site = self._get_local_site(local_site_name)

        try:
            if local_site:
                user = local_site.users.get(username=username)
            else:
                user = User.objects.get(username=username)
        except ObjectDoesNotExist:
            return INVALID_USER

        repository.users.add(user)

        return 201, {
            self.item_result_key: user,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        """Removes a user from the repository ACL."""
        repo_resource = resources.repository

        try:
            repository = repo_resource.get_object(request, *args, **kwargs)
            user = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not repo_resource.has_modify_permissions(request, repository):
            return self.get_no_access_error(request)

        repository.users.remove(user)

        return 204, {}

    @webapi_check_local_site
    @webapi_request_fields(optional={
        'fullname': {
            'type': BooleanFieldType,
            'description': ''
        },
        'q': {
            'type': StringFieldType,
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


repository_user_resource = RepositoryUserResource()
