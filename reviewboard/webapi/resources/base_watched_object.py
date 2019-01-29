from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)
from djblets.webapi.fields import StringFieldType

from reviewboard.accounts.models import Profile
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required)
from reviewboard.webapi.resources import resources


class BaseWatchedObjectResource(WebAPIResource):
    """A base resource for objects watched by a user."""
    watched_resource = None
    uri_object_key = 'watched_obj_id'
    profile_field = None
    star_function = None
    unstar_function = None

    allowed_methods = ('GET', 'POST', 'DELETE')

    @property
    def uri_object_key_regex(self):
        return self.watched_resource.uri_object_key_regex

    def get_queryset(self, request, username, local_site_name=None,
                     *args, **kwargs):
        try:
            local_site = self._get_local_site(local_site_name)
            if local_site:
                user = local_site.users.get(username=username)
                profile = user.get_profile()
            else:
                profile = Profile.objects.get(user__username=username)

            q = self.watched_resource.get_queryset(
                request, local_site_name=local_site_name, *args, **kwargs)
            q = q.filter(starred_by=profile)
            return q
        except Profile.DoesNotExist:
            return self.watched_resource.model.objects.none()

    @webapi_check_login_required
    def get(self, request, watched_obj_id, *args, **kwargs):
        try:
            q = self.get_queryset(request, *args, **kwargs)
            obj = self.get_watched_object(q, watched_obj_id, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        return HttpResponseRedirect(
            self.watched_resource.get_href(obj, request, *args, **kwargs))

    @webapi_check_login_required
    @webapi_response_errors(DOES_NOT_EXIST)
    def get_list(self, request, *args, **kwargs):
        # TODO: Handle pagination and ?counts-only=1
        try:
            objects = [
                self.serialize_object(obj)
                for obj in self.get_queryset(request, is_list=True,
                                             *args, **kwargs)
            ]

            return 200, {
                self.list_result_key: objects,
            }
        except User.DoesNotExist:
            return DOES_NOT_EXIST

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(required={
        'object_id': {
            'type': StringFieldType,
            'description': 'The ID of the object to watch.',
        },
    })
    def create(self, request, object_id, *args, **kwargs):
        try:
            obj_kwargs = kwargs.copy()
            obj_kwargs[self.watched_resource.uri_object_key] = object_id
            obj = self.watched_resource.get_object(request, *args,
                                                   **obj_kwargs)
            user = resources.user.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not resources.user.has_modify_permissions(request, user,
                                                     *args, **kwargs):
            return self.get_no_access_error(request)

        profile = request.user.get_profile()
        star = getattr(profile, self.star_function)
        star(obj)

        return 201, {
            self.item_result_key: obj,
        }

    @webapi_check_local_site
    @webapi_login_required
    def delete(self, request, watched_obj_id, *args, **kwargs):
        try:
            obj_kwargs = kwargs.copy()
            obj_kwargs[self.watched_resource.uri_object_key] = watched_obj_id
            obj = self.watched_resource.get_object(request, *args,
                                                   **obj_kwargs)
            user = resources.user.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not resources.user.has_modify_permissions(request, user,
                                                     *args, **kwargs):
            return self.get_no_access_error(request)

        profile, profile_is_new = request.user.get_profile(return_is_new=True)

        if not profile_is_new:
            unstar = getattr(profile, self.unstar_function)
            unstar(obj)

        return 204, {}

    def serialize_object(self, obj, *args, **kwargs):
        return {
            'id': obj.pk,
            self.item_result_key: obj,
        }

    def get_watched_object(self, queryset, obj_id, *args, **kwargs):
        return queryset.get(pk=obj_id)
