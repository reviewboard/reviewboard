"""API resource for managing a repository's group ACL.

Version Added:
    4.0.11
"""

from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)
from djblets.webapi.fields import StringFieldType

from reviewboard.reviews.models import Group
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.errors import INVALID_GROUP
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.review_group import ReviewGroupResource


class RepositoryGroupResource(ReviewGroupResource):
    """Provides information on groups that are allowed access to a repository.

    Version Added:
        4.0.11
    """

    name = 'repository_group'
    item_result_key = 'group'
    list_result_key = 'groups'
    uri_name = 'groups'
    mimetype_list_resource_name = 'repository-groups'
    mimetype_item_resource_name = 'repository-group'

    # We don't want any group child resources to be available under this
    # resource, as they will have the wrong URLs, and do not make sense as
    # sub-resources. We will be serializing a link to the authoritative group
    # resource and children can be found from there.
    item_child_resources = []

    allowed_methods = ('GET', 'POST', 'DELETE')

    policy_id = 'repository_group'

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

        return repository.review_groups.all()

    def get_href_parent_ids(self, obj, **kwargs):
        """Return the href parent IDs for the object.

        Args:
            obj (reviewboard.reviews.models.Group):
                The review group.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            The parent IDs to be used to determine the href of the resource.
        """
        # Since we do not have a direct link to the model parent (the
        # Repository.review_groups field is a many-to-many field so we cannot
        # use it because the reverse relation is not unique), we have to
        # manually generate the parent IDs from the parent resource.
        parent_id_key = self._parent_resource.uri_object_key

        return {
            parent_id_key: kwargs[parent_id_key],
        }

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        """Return the related links for the resource.

        Args:
            obj (reviewboard.reviews.models.Group, optional):
                The group for which links are being generated.

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
        links = super(RepositoryGroupResource, self).get_related_links(
            obj, request=request, *args, **kwargs)

        # We only want the 'group' link when this is an item resource.
        if self.uri_object_key in kwargs:
            group_name = kwargs[self.uri_object_key]
            links['group'] = {
                'href': resources.review_group.get_item_url(
                    group_name=group_name),
                'method': 'GET',
            }

        return links

    def get_serializer_for_object(self, obj):
        """Return the serializer for an object.

        If the object is a :py:class:`~reviewboard.reviews.models.Group`
        instance, we will serialize it (instead of the
        :py:class:`~reviewboard.webapi.resources.review_group.ReviewGroupResource`
        resource so that the links will be correct. Otherwise, the POST and
        DELETE links will be for the actual user instead of for this resource.

        Args:
            obj (django.db.models.base.Model):
                The model being serialized.

        Returns:
            djblets.webapi.resources.base.WebAPIResource:
            The resource that should be used to serialize the object.
        """
        if isinstance(obj, Group):
            return self

        return super(RepositoryGroupResource, self).get_serializer_for_object(
            obj)

    def has_access_permissions(self, request, group, *args, **kwargs):
        """Return whether the item resource can be accessed.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            group (reviewboard.reviews.models.group.Group, unused):
                The group in the resource item URL. This is unused because we
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
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_GROUP, NOT_LOGGED_IN,
                            PERMISSION_DENIED)
    @webapi_request_fields(required={
        'group_name': {
            'type': StringFieldType,
            'description': 'The group to add to the repository ACL.',
        },
    })
    def create(self, request, group_name, local_site_name=None,
               *args, **kwargs):
        """Adds a group to the repository ACL."""
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
                group = local_site.groups.get(name=group_name,
                                              invite_only=True)
            else:
                group = Group.objects.get(name=group_name,
                                          invite_only=True)
        except ObjectDoesNotExist:
            return INVALID_GROUP

        repository.review_groups.add(group)

        return 201, {
            self.item_result_key: group,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        """Removes a group from the repository ACL."""
        repo_resource = resources.repository

        try:
            repository = repo_resource.get_object(request, *args, **kwargs)
            group = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not repo_resource.has_modify_permissions(request, repository):
            return self.get_no_access_error(request)

        repository.review_groups.remove(group)

        return 204, {}


repository_group_resource = RepositoryGroupResource()
