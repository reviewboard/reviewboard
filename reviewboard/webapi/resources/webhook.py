from __future__ import unicode_literals

import re

from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_request_fields
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)
from djblets.webapi.fields import (BooleanFieldType,
                                   ChoiceFieldType,
                                   DictFieldType,
                                   IntFieldType,
                                   ListFieldType,
                                   ResourceListFieldType,
                                   StringFieldType)

from reviewboard.notifications.forms import WebHookTargetForm
from reviewboard.notifications.models import WebHookTarget
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_login_required,
                                           webapi_check_local_site,
                                           webapi_response_errors)
from reviewboard.webapi.mixins import UpdateFormMixin
from reviewboard.webapi.resources.repository import RepositoryResource


class WebHookResource(UpdateFormMixin, WebAPIResource):
    """A resource for managing webhooks.

    Webhooks are HTTP-based callbacks. When events are triggered on Review
    Board (such as a review request being published), a webhook can be
    configured to make a request to a URL with a payload.

    Webhooks can be triggered by the following events:

    * Review requests being published (``review_request_published``).
    * Review requests being closed (``review_request_closed``).
    * Reviews being published (``review_published``).
    * Review replies being published (``reply_published``).
    * All of the above (``*``).

    The payload that is sent depends on the type of event. Review Board will
    generate a default payload for each event, or it can be overridden by
    providing your payload as the ``custom_content`` field.

    By default, the generated payload will be a JSON payload. This can be
    changed by setting the ``encoding`` field to the appropriate value. Valid
    encodings are:

    * ``application/json``
    * ``application/xml``
    * ``application/x-www-form-encoded``

    Payloads can also be signed with a 128-byte secret given in the ``secret``
    field. If provided, the payload will be signed with the HMAC algorithm.

    Webhooks can apply to all repositories, a select number of repositories, or
    to no repositories. In the latter case, they will only trigger with
    attachment-only review requests.

    Webhooks are :term:`Local Site`-dependant. They will only trigger for
    repositories in the configured local site. If no Local Site is configured,
    they will apply to review requests without a Local Site. If a webhook is
    configured to trigger for a specific set of repositories, the webhook and
    all repositories must be in the same Local Site.
    """

    added_in = '2.5'

    name = 'webhook'
    verbose_name = 'WebHook'
    model = WebHookTarget
    uri_object_key = 'webhook_id'
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    form_class = WebHookTargetForm

    APPLY_TO_ALL_REPOS = 'all'
    APPLY_TO_NO_REPOS = 'none'
    APPLY_TO_CUSTOM_REPOS = 'custom'

    ALL_APPLY_TO_OPTIONS = (
        APPLY_TO_ALL_REPOS,
        APPLY_TO_NO_REPOS,
        APPLY_TO_CUSTOM_REPOS,
    )

    COMMA_SPLIT_RE = re.compile(r'\s*,\s*')

    fields = {
        'apply_to': {
            'type': ChoiceFieldType,
            'choices': ALL_APPLY_TO_OPTIONS,
            'description': 'What review requests the webhook applies to. This '
                           'is one of the strings ``all``, ``none``, or '
                           '``custom``. In the case of ``custom``, the '
                           'repositories are specified in the '
                           '``repositories`` field.',
        },
        'custom_content': {
            'type': StringFieldType,
            'description': 'An optional custom payload.',
        },
        'enabled': {
            'type': BooleanFieldType,
            'description': 'Whether or not the webhook is enabled.',
        },
        'encoding': {
            'type': ChoiceFieldType,
            'choices': WebHookTarget.ALL_ENCODINGS,
            'description': 'The encoding for the payload. This is one of '
                           '``application/json``, ``application/xml`` or '
                           '``application/x-www-form-data``.',
        },
        'events': {
            'type': ListFieldType,
            'items': {
                'type': StringFieldType,
            },
            'description': 'A list of events that will cause the webhook to '
                           'trigger.',
        },
        'extra_data': {
            'type': DictFieldType,
            'description': 'Extra data as part of the webhook. '
                           'This can be set by the API or extensions.',
        },
        'id': {
            'type': IntFieldType,
            'description': 'The numeric ID of the webhook.',
        },
        'secret': {
            'type': StringFieldType,
            'description': 'An optional HMAC digest for the webhook payload. '
                           'If this is specified, the payload will be signed '
                           'with it.',
        },
        'repositories': {
            'type': ResourceListFieldType,
            'resource': RepositoryResource,
            'description': 'The list of repositories this applies to.',
        },
        'url': {
            'type': StringFieldType,
            'description': 'The URL to make HTTP requests against.',
        },
    }

    def has_list_access_permissions(self, request, local_site=None, *args,
                                    **kwargs):
        """Determine if the user has list access permissions for the resource.

        Only superusers and local site admins have access to this resource.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            local_site (reviewboard.site.models.LocalSite):
                The current local site if it exists.

            *args (list):
                Extra arguments.

            **kwargs (dict):
                Extra keyword arguments.

        Returns:
            bool: Whether or not the user has list access permissions.
        """
        return WebHookTarget.objects.can_create(request.user, local_site)

    def has_access_permissions(self, request, obj, local_site=None, *args,
                               **kwargs):
        """Determine if the user has access permissions for the resource.

        Only superusers and local site admins have access to the resource.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            local_site (reviewboard.site.models.LocalSite):
                The current local site if it exists.

            *args (list):
                Extra arguments.

            **kwargs (dict):
                Extra keyword arguments.

        Returns:
            bool: Whether or not the user has access permissions.
        """
        return obj.is_accessible_by(request.user, local_site=local_site)

    def has_modify_permissions(self, *args, **kwargs):
        """Determine if the user has modify permissions for the resource.

        Only admins have access to this resource.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            local_site (reviewboard.site.models.LocalSite):
                The current local site if it exists.

            *args (list):
                Extra arguments.

            **kwargs (dict):
                Extra keyword arguments.

        Returns:
            bool: Whether or not the user has modify permissions.
        """
        return self.has_access_permissions(*args, **kwargs)

    def has_delete_permissions(self, *args, **kwargs):
        """Determine if the user has modification permissions for the resource.

        Only superusers and local site admins have modification permissions.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            local_site (reviewboard.site.models.LocalSite):
                The current local site if it exists.

            *args (list):
                Extra arguments.

            **kwargs (dict):
                Extra keyword arguments.

        Returns:
            bool: Whether or not the user has delete permissions.
        """
        return self.has_access_permissions(*args, **kwargs)

    def get_queryset(self, request, local_site=None, *args, **kwargs):
        """Return the queryset for all objects that match the given request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            local_site (reviewboard.site.models.LocalSite):
                The current local site if it exists.

            *args (list):
                Extra arguments.

            **kwargs (dict):
                Extra keyword arguments.

        Returns:
            django.db.models.query.QuerySet:
            The queryset for all objects matching the given request.
        """
        return WebHookTarget.objects.for_local_site(local_site)

    def serialize_apply_to_field(self, obj, *args, **kwargs):
        """Serialize the ``apply_to`` field into a human-readable value.

        Args:
            value (unicode):
                The value to parse.

            request (django.http.HttpRequest):
                The HTTP request.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            unicode: A human readable value for the field.
        """
        if obj.apply_to == WebHookTarget.APPLY_TO_ALL:
            return 'all'
        elif obj.apply_to == WebHookTarget.APPLY_TO_NO_REPOS:
            return 'none'
        elif obj.apply_to == WebHookTarget.APPLY_TO_SELECTED_REPOS:
            return 'custom'
        else:
            assert False

    def parse_apply_to_field(self, value, request, **kwargs):
        """Parse the apply_to field from a human-readable value.

        Args:
            value (unicode):
                The value to parse.

            request (django.http.HttpRequest):
                The HTTP request.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            unicode:
            A value that the ``WebHookTarget`` model expects for its
            ``apply_to`` field.
        """
        value = value.lower()

        if value == 'all':
            return WebHookTarget.APPLY_TO_ALL
        elif value == 'custom':
            return WebHookTarget.APPLY_TO_SELECTED_REPOS
        elif value == 'none':
            return WebHookTarget.APPLY_TO_NO_REPOS
        else:
            assert False

    def parse_repositories_field(self, value, request, **kwargs):
        """Parse the comma-separated repository IDs.

        Args:
            value (unicode):
                Comma-separated integers representing repository IDs.

            request (django.http.HttpRequest):
                The HTTP request.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            list: A list of repository IDs as strings.
        """
        return self._parse_comma_list(value)

    def parse_events_field(self, value, request, **kwargs):
        """Parse the comma-separated event names.

        Args:
            value (unicode):
                Comma-separated event names.

            request (django.http.HttpRequest):
                The HTTP request.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            list: A list of event names as strings.
        """
        return self._parse_comma_list(value)

    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Retrieves information about a webhook.

        This endpoint will retrieve all information pertaining to the requested
        webhook.
        """
        pass

    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Retrieves the list of webhooks."""
        pass

    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def delete(self, *args, **kwargs):
        """Deletes a webhook."""
        pass

    @webapi_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA, NOT_LOGGED_IN,
                            PERMISSION_DENIED)
    @webapi_request_fields(
        required={
            'apply_to': {
                'type': ChoiceFieldType,
                'choices': ALL_APPLY_TO_OPTIONS,
                'description': 'What review requests the webhook applies to. '
                               'This is one of the strings ``all``, ``none``, '
                               'or ``custom``. In the case of ``custom``, the '
                               'repositories should be specified in the '
                               '``repositories`` field.',
            },
            'enabled': {
                'type': BooleanFieldType,
                'description': 'Whether or not the webhook is enabled.',
            },
            'encoding': {
                'type': ChoiceFieldType,
                'choices': WebHookTarget.ALL_ENCODINGS,
                'description': 'The encoding for the payload. This is one of '
                               '``application/json``, ``application/xml`` or '
                               '``application/x-www-form-encoded``.',
            },
            'events': {
                'type': StringFieldType,
                'description': 'The type of events that trigger the webhook. '
                               'This should be a list of values separated by '
                               'commas.',
            },
            'url': {
                'type': StringFieldType,
                'description': 'The URL to make HTTP requests against.',
            },
        },
        optional={
            'custom_content': {
                'type': StringFieldType,
                'description': 'An optional custom payload.',
            },
            'secret': {
                'type': StringFieldType,
                'description': 'An optional HMAC digest for the webhook '
                               'payload. If this is specified, the payload '
                               'will be signed with it.',
            },
            'repositories': {
                'type': StringFieldType,
                'description': 'If ``apply_to`` is ``selected repositories``, '
                               'this is a comma-separated list of repository '
                               'IDs that the webhook applies to.',
            },
        },
        allow_unknown=True
    )
    def create(self, request, parsed_request_fields, local_site=None,
               extra_fields=None, *args, **kwargs):
        """Creates a new webhook.

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.

        Extra data values supplied will not be used when building the payload
        of the webhook.
        """
        if not WebHookTarget.objects.can_create(request.user, local_site):
            return self.get_no_access_error(request)

        return self._create_or_update(form_data=parsed_request_fields,
                                      extra_fields=extra_fields,
                                      request=request,
                                      local_site=local_site)

    @webapi_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA, NOT_LOGGED_IN,
                            PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'apply_to': {
                'type': ChoiceFieldType,
                'choices': ALL_APPLY_TO_OPTIONS,
                'description': 'What review requests the webhook applies to. '
                               'This is one of the strings ``all``, ``none``, '
                               'or ``custom``. In the case of ``custom``, the '
                               'repositories should be specified in the '
                               '``repositories`` field.',
            },
            'custom_content': {
                'type': StringFieldType,
                'description': 'An optional custom payload.',
            },
            'enabled': {
                'type': BooleanFieldType,
                'description': 'Whether or not the webhook is enabled.',
            },
            'encoding': {
                'type': ChoiceFieldType,
                'choices': WebHookTarget.ALL_ENCODINGS,
                'description': 'The encoding for the payload. This is one of '
                               '``application/json``, ``application/xml`` or '
                               '``application/x-www-form-encoded``.',
            },
            'events': {
                'type': StringFieldType,
                'description': 'The type of events that trigger the webhook. '
                               'This should be a list of values separated by '
                               'commas.',
            },
            'url': {
                'type': StringFieldType,
                'description': 'The URL to make HTTP requests against.',
            },
            'secret': {
                'type': StringFieldType,
                'description': 'An optional HMAC digest for the webhook '
                               'payload. If this is specified, the payload '
                               'will be signed with it.',
            },
            'repositories': {
                'type': StringFieldType,
                'description': 'If ``apply_to`` is ``selected repositories``, '
                               'this is a comma-separated list of repository '
                               'IDs that the webhook applies to.',
            },
        },
        allow_unknown=True
    )
    def update(self, request, parsed_request_fields, local_site=None,
               extra_fields=None, *args, **kwargs):
        """Updates a webhook.

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.

        Extra data values supplied will not be used when building the payload
        of the webhook.
        """
        try:
            webhook = self.get_object(request, local_site=local_site, *args,
                                      **kwargs)
        except WebHookTarget.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_modify_permissions(request, webhook,
                                           local_site=local_site):
            return self.get_no_access_error(request)

        return self._create_or_update(form_data=parsed_request_fields,
                                      extra_fields=extra_fields,
                                      request=request,
                                      local_site=local_site,
                                      webhook=webhook)

    def _create_or_update(self, form_data, extra_fields, request,
                          local_site, webhook=None):
        """Create or update a webhook.

        Args:
            form_data (dict):
                The webhook data to pass to the form.

            extra_fields (dict):
                Extra fields provided by the caller.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            local_site (reviewboard.site.models.LocalSite):
                The Local Site being operated on.

            webhook (reviewboard.notifications.models.WebHookTarget):
                An existing webhook instance to update, if responding to
                a HTTP PUT request.
        """
        if 'custom_content' in form_data:
            # We only explicitly set use_custom_content if the user has
            # provided the custom_content field. We don't want to unset it
            # when the user is updating other fields and does not intend to
            # update this one.
            form_data['use_custom_content'] = \
                (form_data['custom_content'] != '')

        return self.handle_form_request(
            data=form_data,
            request=request,
            instance=webhook,
            extra_fields=extra_fields,
            form_kwargs={
                'limit_to_local_site': local_site,
                'request': request,
            })

    def _parse_comma_list(self, value):
        """Split a comma-separated string.

        Args:
            value (unicode):
                The comma-separated list of values.

        Returns:
            list:
            A list of :py:class:`unicode` objects. If the given value is empty,
            then the empty list is returned instead of a list containing the
            empty string.
        """
        value = value.strip()

        if not value:
            return []

        return self.COMMA_SPLIT_RE.split(value)


webhook_resource = WebHookResource()
