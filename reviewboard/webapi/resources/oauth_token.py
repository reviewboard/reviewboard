"""An API for managing OAuth2 tokens."""

from __future__ import unicode_literals

from django.db.models.query import Q
from django.utils.translation import ugettext_lazy as _
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.oauth2_scopes import get_scope_dictionary
from djblets.webapi.errors import DOES_NOT_EXIST, INVALID_FORM_DATA
from djblets.webapi.fields import ListFieldType, StringFieldType
from oauth2_provider.models import AccessToken

from reviewboard.oauth.features import oauth2_service_feature
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site


class OAuthTokenResource(WebAPIResource):
    """An API resource for managing OAuth2 tokens.

    This resource allows callers to list, update, or delete their existing
    tokens.
    """

    model = AccessToken
    name = 'oauth_token'
    verbose_name = _('OAuth2 Tokens')
    uri_object_key = 'oauth_token_id'
    item_result_key = 'oauth_token'
    required_features = [oauth2_service_feature]
    allowed_methods = ('GET', 'PUT', 'DELETE')

    api_token_access_allowed = False
    oauth2_token_access_allowed = False

    added_in = '3.0'

    fields = {
        'application': {
            'type': StringFieldType,
            'description': 'The name of the application this token is for.',
        },
        'expires': {
            'type': StringFieldType,
            'description': 'When this token is set to expire.',
        },
        'scope': {
            'type': ListFieldType,
            'items': {
                'type': StringFieldType,
            },
            'description': 'The scopes this token has access to.',
        },
        'token': {
            'type': StringFieldType,
            'description': 'The access token.',
        },
    }

    def serialize_application_field(self, obj, *args, **kwargs):
        """Serialize the application field.

        Args:
            obj (oauth2_provider.models.AccessToken):
                The token that is being serialized.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Returns:
            unicode:
            The name of the application the access token has access to.
        """
        return obj.application.name

    def serialize_expires_field(self, obj, *args, **kwargs):
        """Serialize the expires field.

        Args:
            obj (oauth2_provider.models.AccessToken):
                The token that is being serialized.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Returns:
            unicode:
            The expiry date of the token, in ISO-8601 format.
        """
        return obj.expires.isoformat()

    def serialize_scope_field(self, obj, *args, **kwargs):
        """Serialize the scope field.

        Args:
            obj (oauth2_provider.models.AccessToken):
                The token that is being serialized.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Returns:
            list of unicode:
            The list of scopes the token has.
        """
        return obj.scope.split()

    def get_queryset(self, request, *args, **kwargs):
        """Return the queryset for the request.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            local_site (reviewboard.site.models.LocalSite, optional):
                The current LocalSite, if any.

        Returns:
            django.db.models.query.QuerySet:
            The tokens the user has access to.
        """
        if not request.user.is_authenticated():
            return AccessToken.objects.none()

        q = Q(application__local_site=request.local_site)

        if not request.user.is_superuser:
            q &= Q(user=request.user)

        return (
            AccessToken.objects
            .filter(q)
            .select_related('application')
        )

    def has_access_permissions(self, request, obj, *args, **kwargs):
        """Return whether or not the user has access permissions.

        A user has this permission if they own the token or are a superuser.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            obj (oauth2_provider.models.AccessToken):
                The token in question.

        Returns:
            bool:
            Whether or not the user has permission.
        """
        return (request.user.is_authenticated() and
                (obj.user_id == request.user.pk or
                 request.user.is_superuser))

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        """Return whether or not the user has modification permissions.

        A user has this permission if they own the token or are a superuser.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            obj (oauth2_provider.models.AccessToken):
                The token in question.

        Returns:
            bool:
            Whether or not the user has permission.
        """
        return self.has_access_permissions(request, obj, *args, **kwargs)

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        """Return whether or not the user has deletion permissions.

        A user has this permission if they own the token or are a superuser.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            obj (oauth2_provider.models.AccessToken):
                The token in question.

        Returns:
            bool:
            Whether or not the user has permission.
        """
        return self.has_access_permissions(request, obj, *args, **kwargs)

    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Retrieves information on a particular OAuth2 token.

        This can only be accessed by the owner of the tokens or superusers
        """
        pass

    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Retrieve a list of information about an OAuth2 token.

        If accessing this API on a Local Site, the results will be limited
        to those associated with that site. Otherwise, it will be limited to
        those associated with no Local Site.

        This can only be accessed by the owner of the tokens or superusers.
        """
        pass

    @augment_method_from(WebAPIResource)
    def delete(self, *args, **kwargs):
        """Delete the OAuth2 token, invalidating all clients using it.

        The OAuth token will be removed from the user's account, and will no
        longer be usable for authentication.

        After deletion, this will return a :http:`204`.
        """
        pass

    @webapi_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST)
    @webapi_request_fields(
        optional={
            'add_scopes': {
                'type': StringFieldType,
                'description': 'A comma-separated list of scopes to add.',
            },
            'remove_scopes': {
                'type': StringFieldType,
                'description': 'A comma-separated list of scopes to remove.',
            },
            'scopes': {
                'type': StringFieldType,
                'description': 'A comma-separated list of scopes to override '
                               'the current set with.\n\n'
                               'This field cannot be provided if either '
                               'add_scopes or remove_scopes is provided.',
            },
        },
    )
    def update(self, request, local_site=None, add_scopes=None,
               remove_scopes=None, scopes=None, *args, **kwargs):
        """Update the scope of an OAuth2 token.

        This resource allows a user to either (1) add and remove scopes or (2)
        replace the set of scopes with a new set.
        """
        try:
            access_token = self.get_object(request, *args, **kwargs)
        except AccessToken.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_modify_permissions(request, access_token, *args,
                                           **kwargs):
            return self.get_no_access_error(request)

        if ((add_scopes is not None or remove_scopes is not None) and
            scopes is not None):
            return INVALID_FORM_DATA, {
                'fields': {
                    'scopes': [
                        'This field cannot be provided if either add_scopes '
                        'or remove_scopes is provided.',
                    ],
                },
            }

        field_errors = {}
        valid_scopes = get_scope_dictionary()

        if scopes is not None:
            scopes = self._validate_scopes(valid_scopes, scopes, 'scopes',
                                           field_errors)
        elif add_scopes is not None or remove_scopes is not None:
            add_scopes = self._validate_scopes(valid_scopes,
                                               add_scopes,
                                               'add_scopes',
                                               field_errors)
            remove_scopes = self._validate_scopes(valid_scopes,
                                                  remove_scopes,
                                                  'remove_scopes',
                                                  field_errors)

        if field_errors:
            return INVALID_FORM_DATA, {
                'fields': field_errors,
            }

        if scopes is not None:
            access_token.scope = ' '.join(scopes)
            access_token.save(update_fields=('scope',))
        elif add_scopes is not None or remove_scopes is not None:
            current_scopes = set(access_token.scope.split(' '))

            if add_scopes:
                current_scopes.update(add_scopes)

            if remove_scopes:
                current_scopes.difference_update(remove_scopes)

            access_token.scope = ' '.join(current_scopes)
            access_token.save(update_fields=('scope',))

        return 200, {
            self.item_result_key: access_token,
        }

    def _validate_scopes(self, valid_scopes, scopes, field, field_errors):
        """Validate the given set of scopes against known valid scopes.

        Args:
            valid_scopes (dict):
                The scope dictionary.

            scopes (unicode):
                The comma-separated list of scopes to validate.

            field (unicode):
                The name of the field that is being validated.

            field_errors (dict):
                A mapping of field names to errors.

                An error message will be added to ``field_errors[field]`` for
                each invalid scope.

        Returns:
            list:
            The list of scopes, if they are all valid, or ``None`` otherwise.
        """
        if scopes is None:
            return None

        scopes = scopes.split(',')
        invalid_scopes = {
            scope
            for scope in scopes
            if scope not in valid_scopes
        }

        if invalid_scopes:
            field_errors[field] = [
                'The scope "%s" is invalid.' % scope
                for scope in invalid_scopes
            ]

            return None

        return scopes


oauth_token_resource = OAuthTokenResource()
