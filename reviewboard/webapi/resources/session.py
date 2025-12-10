"""API resource for user session management."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from djblets.util.json_utils import json_merge_patch
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_request_fields)
from djblets.webapi.errors import INVALID_FORM_DATA
from djblets.webapi.resources.registry import get_resource_for_object

from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)

if TYPE_CHECKING:
    from django.http import HttpRequest

    from djblets.webapi.resources.base import WebAPIResourceHandlerResult
    from djblets.webapi.responses import WebAPIResponsePayload


class SessionResource(WebAPIResource):
    """Information on the active user's session.

    This includes information on the user currently logged in through the
    calling client, if any. Currently, the resource links to that user's
    own resource, making it easy to figure out the user's information and
    any useful related resources.
    """

    name = 'session'
    singleton = True
    allowed_methods = ('GET', 'PUT', 'DELETE')

    #: Settings paths that can be modified in a PUT.
    #:
    #: Version Added:
    #:     7.1
    _MUTABLE_PROFILE_SETTING_PATHS: set[tuple[str, ...]] = {
        ('confirm_ship_it',),
        ('quick_access_action_ids',),
    }

    def serialize_object(
        self,
        obj: None,
        request: (HttpRequest | None) = None,
        *args,
        **kwargs,
    ) -> WebAPIResponsePayload:
        """Serialize the session resource.

        This specially serializes some state and links for the session
        based on the login state.

        Args:
            obj (object):
                The object to serialize.

                This will always be ``None`` for this resource.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments passed to the view.

        Returns:
            djblets.webapi.responses.WebAPIResponsePayload:
            The serialized payload.
        """
        assert request is not None

        expanded_resources = (
            request.GET.get('expand', '') or
            request.POST.get('expand', '')
        ).split(',')

        user = request.user
        authenticated = user.is_authenticated

        data: WebAPIResponsePayload = {
            'authenticated': authenticated,
            'links': self.get_links(request=request, *args, **kwargs),
        }

        if authenticated and 'user' in expanded_resources:
            data['user'] = user
            del data['links']['user']

        return data

    @webapi_check_local_site
    @webapi_check_login_required
    def get(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> WebAPIResourceHandlerResult:
        """Returns information on the client's session.

        This currently just contains information on the currently logged-in
        user (if any).
        """
        return 200, {
            self.name: self.serialize_object(obj=None,
                                             request=request,
                                             *args, **kwargs),
        }

    @webapi_check_local_site
    @webapi_login_required
    def delete(self, request, *args, **kwargs):
        """Clears the user's client session and the session cookie.

        This is equivalent to logging out a user. The existing session cookie
        will be invalidated and will no longer be accepted.

        This will return a :http:`204`.
        """
        logout(request)

        return 204, {}

    @webapi_login_required
    @webapi_check_local_site
    @webapi_request_fields(
        optional={
            'settings:json': {
                'type': str,
                'description': (
                    'A JSON Merge Patch of settings change to make. These '
                    'will be persisted across sessions. This is considered '
                    'internal API and is subject to change.'
                ),
            },
        },
    )
    def update(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> WebAPIResourceHandlerResult:
        """Update information about the session.

        This is only used internally to manage Review Board session state.
        This operation is not considered public API.

        Version Added:
            7.1
        """
        settings_json = request.POST.get('settings:json')

        if settings_json:
            try:
                patch = json.loads(settings_json)
            except ValueError as e:
                return INVALID_FORM_DATA, {
                    'fields': {
                        'settings': [
                            # Use %-based formatting to share translations
                            # with ImportExtraDataError.error_payload.
                            _('Could not parse JSON data: %s') % e,
                        ],
                    },
                }

            user = request.user
            assert isinstance(user, User)

            profile = user.get_profile(create_if_missing=True)

            MUTABLE_SETTING_PATHS = self._MUTABLE_PROFILE_SETTING_PATHS

            new_settings = json_merge_patch(
                profile.settings,
                patch,
                can_write_key_func=lambda *, path, **kwargs:
                    path in MUTABLE_SETTING_PATHS)

            # Save extra_data only if it remains a dictionary, so callers
            # can't replace the entire contents.
            if not isinstance(new_settings, dict):
                return INVALID_FORM_DATA, {
                    'fields': {
                        'settings': [
                            _('settings:json cannot replace the settings '
                              'with a non-dictionary type'),
                        ],
                    },
                }

            profile.settings.clear()
            profile.settings.update(new_settings)
            profile.save(update_fields=('settings',))

        return 200, {
            self.name: self.serialize_object(obj=None,
                                             request=request,
                                             *args, **kwargs),
        }

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        links = {}

        if request and request.user.is_authenticated:
            user_resource = get_resource_for_object(request.user)
            href = user_resource.get_href(request.user, request,
                                          *args, **kwargs)

            # Since there's no object, DELETE won't be populated automatically.
            clean_href = request.build_absolute_uri()
            i = clean_href.find('?')

            if i != -1:
                clean_href = clean_href[:i]

            links['delete'] = {
                'method': 'DELETE',
                'href': clean_href,
            }

            links['user'] = {
                'method': 'GET',
                'href': href,
                'title': str(request.user),
                'resource': user_resource,
                'list-resource': False,
            }

        return links


session_resource = SessionResource()
