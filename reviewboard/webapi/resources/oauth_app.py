"""The OAuth2 application resource."""

from __future__ import unicode_literals

from collections import defaultdict
from itertools import chain

from django.contrib.auth.models import User
from django.db.models.query import Q
from django.utils import six
from django.utils.six.moves import filter
from django.utils.translation import ugettext_lazy as _
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA)
from djblets.webapi.fields import (BooleanFieldType,
                                   ChoiceFieldType,
                                   DictFieldType,
                                   IntFieldType,
                                   ListFieldType,
                                   ResourceFieldType,
                                   StringFieldType)
from oauth2_provider.generators import generate_client_secret

from reviewboard.oauth.forms import (ApplicationChangeForm,
                                     ApplicationCreationForm)
from reviewboard.oauth.models import Application
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.mixins import UpdateFormMixin


class OAuthApplicationResource(UpdateFormMixin, WebAPIResource):
    """Manage OAuth2 applications."""

    model = Application
    name = 'oauth_app'
    verbose_name = _('OAuth2 Applications')
    uri_object_key = 'app_id'

    form_class = ApplicationChangeForm
    add_form_class = ApplicationCreationForm

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    added_in = '3.0'
    fields = {
        'authorization_grant_type': {
            'type': ChoiceFieldType,
            'choices': (Application.GRANT_AUTHORIZATION_CODE,
                        Application.GRANT_CLIENT_CREDENTIALS,
                        Application.GRANT_IMPLICIT,
                        Application.GRANT_PASSWORD),
            'description':
                'How the authorization is granted to the application. This '
                'will be one of %s, %s, %s, or %s.'
                % (Application.GRANT_AUTHORIZATION_CODE,
                   Application.GRANT_CLIENT_CREDENTIALS,
                   Application.GRANT_IMPLICIT,
                   Application.GRANT_PASSWORD)
        },
        'client_id': {
            'type': StringFieldType,
            'description': 'The client ID. This will be used by your '
                           'application to identify itself to Review Board.',
        },
        'client_secret': {
            'type': StringFieldType,
            'description': 'The client secret. This should only be known to '
                           'Review Board and the application.',
        },
        'client_type': {
            'type': ChoiceFieldType,
            'choices': (Application.CLIENT_CONFIDENTIAL,
                        Application.CLIENT_PUBLIC),
            'description': 'The type of client. Confidential clients must be '
                           'able to keep user password secure.\n\n'
                           'This will be one of %s or %s.'
                           % (Application.CLIENT_CONFIDENTIAL,
                              Application.CLIENT_PUBLIC),
        },
        'enabled': {
            'type': BooleanFieldType,
            'description': 'Whether or not this application is enabled.\n\n'
                           'If disabled, authentication and API access will '
                           'not be available for clients using this '
                           'application.',
        },
        'extra_data': {
            'type': DictFieldType,
            'description': 'Extra information associated with the '
                           'application.',
        },
        'id': {
            'type': IntFieldType,
            'description': 'The application ID. This uniquely identifies the '
                           'application when communicating with the Web API.',
        },
        'name': {
            'type': StringFieldType,
            'description': 'The application name.',
        },
        'redirect_uris': {
            'type': ListFieldType,
            'items': {
                'type': StringFieldType,
            },
            'description': 'The list of allowed URIs to redirect to.',
        },
        'skip_authorization': {
            'type': BooleanFieldType,
            'description': 'Whether or not users will be prompted for '
                           'authentication.\n\n'
                           'This field is only editable by administrators.',
        },
        'user': {
            'type': ResourceFieldType,
            'resource': 'reviewboard.webapi.resources.user.UserResource',
            'description': 'The user who created the application.',
        },
    }

    CREATE_REQUIRED_FIELDS = {
        'authorization_grant_type': {
            'type': ChoiceFieldType,
            'choices': (Application.GRANT_AUTHORIZATION_CODE,
                        Application.GRANT_CLIENT_CREDENTIALS,
                        Application.GRANT_IMPLICIT,
                        Application.GRANT_PASSWORD),
            'description': 'How authorization is granted to the '
                           'application.',
        },
        'client_type': {
            'type': ChoiceFieldType,
            'choices': (Application.CLIENT_CONFIDENTIAL,
                        Application.CLIENT_PUBLIC),
            'description': 'The client type. Confidential clients must be '
                           'able to keep user passwords secure.',
        },
        'name': {
            'type': StringFieldType,
            'description': 'The application name.',
        },
    }

    CREATE_OPTIONAL_FIELDS = {
        'enabled': {
            'type': BooleanFieldType,
            'description': 'Whether or not the application will be enabled.'
                           '\n\n'
                           'If disabled, authentication and API access will '
                           'not be available for clients using this '
                           'application.\n\n'
                           'Defaults to true when creating a new Application.'
        },
        'redirect_uris': {
            'type': StringFieldType,
            'description': 'A comma-separated list of allowed URIs to '
                           'redirect to.',
        },
        'skip_authorization': {
            'type': BooleanFieldType,
            'description': 'Whether or not users will be prompted for '
                           'authentication.',
        },
        'user': {
            'type': StringFieldType,
            'description': 'The user who owns the application.\n\nThis field '
                           'is only available to super users.',
        },
    }

    UPDATE_OPTIONAL_FIELDS = {
        'regenerate_client_secret': {
            'type': BooleanFieldType,
            'description': 'The identifier of the LocalSite to re-assign this '
                           'Application to.\n\n'
                           'The Application will be limited to users '
                           'belonging to that Local Site and will only be '
                           'editable via the API for that LocalSite.\n\n'
                           'If this is set to the empty string, the '
                           'Application will become unassigned from all Local '
                           'Sites and will be available globally.',
        },
    }

    def serialize_redirect_uris_field(self, obj, **kwargs):
        """Serialize the ``redirect_uris`` field to a list.

        Args:
            obj (reviewboard.oauth.models.Application):
                The application being serialized.

            **kwargs (dict):
                Ignored keyword arguments

        Returns:
            list of unicode:
            The list of allowable redirect URIs.
        """
        return list(filter(len, obj.redirect_uris.split()))

    def has_access_permissions(self, request, obj, local_site=None, *args,
                               **kwargs):
        """Return whether or not the user has permission to access this object.

        See :py:meth:`Application.is_accessible_by()
        <reviewboard.oauth.models.Application.is_accessible_by>` for details of
        when a user has access permissions.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            obj (reviewboard.oauth.models.Application):
                The application to check for delete permission against.

            local_site (reviewboard.site.models.LocalSite, optional):
                The current Local Site, if any.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Returns:
            bool:
            Whether or not the user has delete permissions.
        """
        return obj.is_accessible_by(request.user, local_site=local_site)

    def has_modify_permissions(self, request, obj, local_site=None, *args,
                               **kwargs):
        """Return whether or not the user has modify permissions.

        See :py:meth:`Application.is_mutable_by()
        <reviewboard.oauth.models.Application.is_mutable_by>` for details of
        when a user has modify permissions.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            obj (reviewboard.oauth.models.Application):
                The application to check for delete permission against.

            local_site (reviewboard.site.models.LocalSite, optional):
                The current LocalSite, if any.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Returns:
            bool:
            Whether or not the user has modify permissions.
        """
        return obj.is_mutable_by(request.user, local_site=local_site)

    def has_delete_permissions(self, request, obj, local_site=None, *args,
                               **kwargs):
        """Return whether or not the user has delete permissions.

        See :py:meth:`Application.is_mutable_by()
        <reviewboard.oauth.models.Application.is_mutable_by>` for details of
        when a user has delete permissions.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            obj (reviewboard.oauth.models.Application):
                The application to check for delete permission against.

            local_site (reviewboard.site.models.LocalSite, optional):
                The current LocalSite, if any.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Ignored keyword arguments.

        Returns:
            bool:
            Whether or not the user has delete permissions.
        """
        return obj.is_mutable_by(request.user, local_site=local_site)

    def get_queryset(self, request, is_list=False, local_site=None,
                     *args, **kwargs):
        """Return the queryset for filtering responses.

        If the ``username`` GET field is set, the returned applications will be
        limited to the those owned by that user.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            is_list (bool, optional):
                Whether or not the list resource is being accessed.

            local_site (reviewboard.site.models.LocalSite, optional):
                The current LocalSite, if any.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            django.db.models.query.QuerySet:
            The applications the user has access to.
        """
        if not request.user.is_authenticated():
            return Application.objects.none()

        q = Q(local_site=local_site)

        # Unless the user is a super user or local site admin, the query will
        # be limited to that user's applications.
        if (not (request.user.is_superuser or
                 (local_site and
                  local_site.admins.filter(pk=request.user.pk).exists()))):
            q &= Q(user=request.user)

        username = request.GET.get('username')

        if username:
            q &= Q(user__username=username)

        return Application.objects.filter(q)

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Return information on a particular OAuth2 application.

        The client's logged in user must either own the app in question or
        be an administrator.
        """
        pass

    @webapi_check_local_site
    @webapi_login_required
    @webapi_request_fields(
        optional={
            'username': {
                'type': StringFieldType,
                'description': 'If present, the results will be filtered to '
                               'Applications owned by the specified user.\n\n'
                               'Only administrators have access to '
                               'Applications owned by other users.',
            },
        },
    )
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Return information about all OAuth2 applications.

        This will be limited to the client's logged in user's applications
        unless the user is an administrator.
        """
        pass

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST)
    @webapi_request_fields(required=CREATE_REQUIRED_FIELDS,
                           optional=CREATE_OPTIONAL_FIELDS,
                           allow_unknown=True)
    def create(self, request, parsed_request_fields, extra_fields,
               local_site=None, *args, **kwargs):
        """Create a new OAuth2 application.

        The ``client_secret`` and ``client_id`` fields will be auto-generated
        and returned in the response (providing the request is successful).

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        return self._create_or_update(request, parsed_request_fields,
                                      extra_fields, None, local_site)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(INVALID_FORM_DATA)
    @webapi_request_fields(
        optional=dict(chain(six.iteritems(CREATE_REQUIRED_FIELDS),
                            six.iteritems(CREATE_OPTIONAL_FIELDS),
                            six.iteritems(UPDATE_OPTIONAL_FIELDS))),
        allow_unknown=True,
    )
    def update(self, request, parsed_request_fields, extra_fields,
               local_site=None, *args, **kwargs):
        """Update an OAuth2 application.

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        try:
            app = self.get_object(request, local_site=local_site, *args,
                                  **kwargs)
        except Application.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_modify_permissions(request, app,
                                           local_site=local_site):
            return self.get_no_access_error(request)

        try:
            regenerate_secret = parsed_request_fields.pop(
                'regenerate_client_secret')
        except KeyError:
            regenerate_secret = False

        return self._create_or_update(request, parsed_request_fields,
                                      extra_fields, app, local_site,
                                      regenerate_secret=regenerate_secret)

    @webapi_login_required
    @webapi_check_local_site
    def delete(self, request, local_site=None, *args, **kwargs):
        """Delete the OAuth2 application.

        After a successful delete, this will return :http:`204`.
        """
        try:
            app = self.get_object(request, local_site=local_site, *args,
                                  **kwargs)
        except Application.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, app, local_site):
            return self.get_no_access_error(request)

        app.delete()

        return 204, {}

    def _create_or_update(self, request, parsed_request_fields, extra_fields,
                          instance, local_site, regenerate_secret=False):
        """Create or update an application.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            parsed_request_fields (dict):
                The parsed request fields.

            extra_fields (dict):
                Extra data fields.

            instance (reviewboard.oauth.models.Application):
                The current application to update or ``None`` if we are
                creating a new application.

            local_site (reviewboard.site.models.LocalSite):
                The LocalSite the API is being accessed through.

            regenerate_secret (bool, optional):
                Whether or not the secret on the

        Returns:
            tuple:
            A 2-tuple of:

            * The HTTP status (:py:class:`int` or
              :py:class:`djblets.webapi.error.WebAPIError`).
            * The response body to encode (:py:class:`dict`).
        """
        try:
            username = parsed_request_fields.pop('user')
        except KeyError:
            username = None

        skip_authorization = parsed_request_fields.get('skip_authorization',
                                                       False)
        change_owner = (username is not None and
                        username != request.user.username)
        errors = defaultdict(list)
        user_pk = None

        if skip_authorization or change_owner:
            # These fields are only available to administrators. We must check
            # for adequate permissions.
            if not (request.user.is_authenticated() and
                    (request.user.is_superuser or
                     (request.local_site is not None and
                      request.local_site.is_mutable_by(request.user)))):
                # The user does not have adequate permission to modify these
                # fields. We will return an error message for each field they
                # attempted to modify.
                err_msg = 'You do not have permission to set this field.'

                if skip_authorization:
                    errors['skip_authorization'].append(err_msg)

                if change_owner:
                    errors['user'].append(err_msg)
            elif change_owner:
                try:
                    if request.local_site:
                        qs = local_site.users
                    else:
                        qs = User.objects

                    user_pk = (
                        qs
                        .values_list('pk', flat=True)
                        .get(username=username)
                    )
                except User.DoesNotExist:
                    errors['user'].append('The user "%s" does not exist.'
                                          % username)

        if errors:
            return INVALID_FORM_DATA, {
                'fields': errors,
            }

        form_data = parsed_request_fields.copy()

        # When creating the application, if a user is not provided, set it to
        # the user making the request.
        #
        # Do not update the user field during an update when it is not
        # explicitly provided.
        if user_pk is None and instance is None:
            assert not change_owner
            user_pk = request.user.pk

        if user_pk is not None:
            form_data['user'] = user_pk

        if not instance:
            form_data.setdefault('enabled', True)

            if local_site:
                form_data['local_site'] = local_site.pk
        elif regenerate_secret:
            # We are setting these directly on the instance because the form
            # does not support updating the client_secret field.
            instance.client_secret = generate_client_secret()

            # Setting instance.original_user to be blank will make
            # instance.is_disabled_for_security False so that the form will
            # validate.
            instance.original_user = None

        return self.handle_form_request(
            data=form_data,
            request=request,
            instance=instance,
            extra_fields=extra_fields)


oauth_app_resource = OAuthApplicationResource()
