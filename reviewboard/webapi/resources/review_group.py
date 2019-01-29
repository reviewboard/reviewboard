from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)
from djblets.webapi.fields import (BooleanFieldType,
                                   DictFieldType,
                                   IntFieldType,
                                   StringFieldType)

from reviewboard.reviews.models import Group
from reviewboard.webapi.base import ImportExtraDataError, WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.errors import (GROUP_ALREADY_EXISTS,
                                       INVALID_USER)
from reviewboard.webapi.resources import resources


class ReviewGroupResource(WebAPIResource):
    """Provides information on review groups.

    Review groups are groups of users that can be listed as an intended
    reviewer on a review request.
    """
    model = Group
    fields = {
        'id': {
            'type': IntFieldType,
            'description': 'The numeric ID of the review group.',
        },
        'name': {
            'type': StringFieldType,
            'description': 'The short name of the group, used in the '
                           'reviewer list and the Dashboard.',
        },
        'display_name': {
            'type': StringFieldType,
            'description': 'The human-readable name of the group, sometimes '
                           'used as a short description.',
        },
        'invite_only': {
            'type': BooleanFieldType,
            'description': 'Whether or not the group is invite-only. An '
                           'invite-only group is only accessible by members '
                           'of the group.',
            'added_in': '1.6',
        },
        'mailing_list': {
            'type': StringFieldType,
            'description': 'The e-mail address that all posts on a review '
                           'group are sent to.',
        },
        'url': {
            'type': StringFieldType,
            'description': "The URL to the user's page on the site. "
                           "This is deprecated and will be removed in a "
                           "future version.",
            'deprecated_in': '2.0',
        },
        'absolute_url': {
            'type': StringFieldType,
            'description': "The absolute URL to the user's page on the site.",
            'added_in': '2.0',
        },
        'visible': {
            'type': BooleanFieldType,
            'description': 'Whether or not the group is visible to users '
                           'who are not members. This does not prevent users '
                           'from accessing the group if they know it, though.',
            'added_in': '1.6',
        },
        'extra_data': {
            'type': DictFieldType,
            'description': 'Extra data as part of the review group. '
                           'This can be set by the API or extensions.',
            'added_in': '2.0',
        },
    }

    item_child_resources = [
        resources.review_group_user,
    ]

    uri_object_key = 'group_name'
    uri_object_key_regex = '[A-Za-z0-9_-]+'
    model_object_key = 'name'
    mimetype_list_resource_name = 'review-groups'
    mimetype_item_resource_name = 'review-group'

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def has_delete_permissions(self, request, group, *args, **kwargs):
        return group.is_mutable_by(request.user)

    def has_modify_permissions(self, request, group):
        return group.is_mutable_by(request.user)

    def get_queryset(self, request, is_list=False, local_site_name=None,
                     *args, **kwargs):
        search_q = request.GET.get('q', None)
        local_site = self._get_local_site(local_site_name)

        if is_list:
            query = self.model.objects.accessible(request.user,
                                                  local_site=local_site)
        else:
            query = self.model.objects.filter(local_site=local_site)

        if search_q:
            q = Q(name__istartswith=search_q)

            if request.GET.get('displayname', None):
                q = q | Q(display_name__istartswith=search_q)

            query = query.filter(q)

        return query

    def serialize_url_field(self, group, **kwargs):
        return group.get_absolute_url()

    def serialize_absolute_url_field(self, obj, request, **kwargs):
        return request.build_absolute_uri(obj.get_absolute_url())

    def has_access_permissions(self, request, group, *args, **kwargs):
        return group.is_accessible_by(request.user)

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Retrieve information on a review group.

        Some basic information on the review group is provided, including
        the name, description, and mailing list (if any) that e-mails to
        the group are sent to.

        The group links to the list of users that are members of the group.
        """
        pass

    @webapi_check_local_site
    @webapi_request_fields(
        optional={
            'q': {
                'type': StringFieldType,
                'description': 'The string that the group name (or the  '
                               'display name when using ``displayname``) '
                               'must start with in order to be included in '
                               'the list. This is case-insensitive.',
            },
            'displayname': {
                'type': BooleanFieldType,
                'description': 'Specifies whether ``q`` should also match '
                               'the beginning of the display name.',
            },
        },
        allow_unknown=True
    )
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Retrieves the list of review groups on the site.

        The list of review groups can be filtered down using the ``q`` and
        ``displayname`` parameters.

        Setting ``q`` to a value will by default limit the results to
        group names starting with that value. This is a case-insensitive
        comparison.

        If ``displayname`` is set to ``1``, the display names will also be
        checked along with the username. ``displayname`` is ignored if ``q``
        is not set.

        For example, accessing ``/api/groups/?q=dev&displayname=1`` will list
        any groups with a name or display name starting with ``dev``.
        """
        pass

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(GROUP_ALREADY_EXISTS, INVALID_FORM_DATA,
                            INVALID_USER, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required={
            'name': {
                'type': StringFieldType,
                'description': 'The name of the group.',
                'added_in': '1.6.14',
            },
            'display_name': {
                'type': StringFieldType,
                'description': 'The human-readable name of the group.',
                'added_in': '1.6.14',
            },
        },
        optional={
            'mailing_list': {
                'type': StringFieldType,
                'description': 'The e-mail address that all posts on a review '
                               'group are sent to.',
                'added_in': '1.6.14',
            },
            'visible': {
                'type': BooleanFieldType,
                'description': 'Whether or not the group is visible to users '
                               'who are not members. The default is true.',
                'added_in': '1.6.14',
            },
            'invite_only': {
                'type': BooleanFieldType,
                'description': 'Whether or not the group is invite-only. '
                               'The default is false.',
                'added_in': '1.6.14',
            },
        },
        allow_unknown=True
    )
    def create(self, request, name, display_name, mailing_list=None,
               visible=True, invite_only=False, local_site_name=None,
               extra_fields={}, *args, **kargs):
        """Creates a new review group.

        This will create a brand new review group with the given name
        and display name. The group will be public by default, unless
        specified otherwise.

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        local_site = self._get_local_site(local_site_name)

        if not self.model.objects.can_create(request.user, local_site):
            return self.get_no_access_error(request)

        group, is_new = self.model.objects.get_or_create(
            name=name,
            local_site=local_site,
            defaults={
                'display_name': display_name,
                'mailing_list': mailing_list or '',
                'visible': bool(visible),
                'invite_only': bool(invite_only),
            })

        if not is_new:
            return GROUP_ALREADY_EXISTS

        if extra_fields:
            try:
                self.import_extra_data(group, group.extra_data, extra_fields)
            except ImportExtraDataError as e:
                return e.error_payload

            group.save(update_fields=['extra_data'])

        return 201, {
            self.item_result_key: group,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA,
                            GROUP_ALREADY_EXISTS, NOT_LOGGED_IN,
                            PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'name': {
                'type': StringFieldType,
                'description': 'The new name for the group.',
                'added_in': '1.6.14',
            },
            'display_name': {
                'type': StringFieldType,
                'description': 'The human-readable name of the group.',
                'added_in': '1.6.14',
            },
            'mailing_list': {
                'type': StringFieldType,
                'description': 'The e-mail address that all posts on a review '
                               'group are sent to.',
                'added_in': '1.6.14',
            },
            'visible': {
                'type': BooleanFieldType,
                'description': 'Whether or not the group is visible to users '
                               'who are not members.',
                'added_in': '1.6.14',
            },
            'invite_only': {
                'type': BooleanFieldType,
                'description': 'Whether or not the group is invite-only.',
                'added_in': '1.6.14',
            },
        },
        allow_unknown=True
    )
    def update(self, request, name=None, extra_fields={}, *args, **kwargs):
        """Updates an existing review group.

        All the fields of a review group can be modified, including the
        name, so long as it doesn't conflict with another review group.

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        try:
            group = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_modify_permissions(request, group):
            return self.get_no_access_error(request)

        if name is not None and name != group.name:
            # If we're changing the group name, make sure that group doesn't
            # exist.
            local_site = self._get_local_site(kwargs.get('local_site_name'))

            if self.model.objects.filter(name=name,
                                         local_site=local_site).exists():
                return GROUP_ALREADY_EXISTS

            group.name = name

        for field in ("display_name", "mailing_list", "visible",
                      "invite_only"):
            val = kwargs.get(field, None)

            if val is not None:
                setattr(group, field, val)

        try:
            self.import_extra_data(group, group.extra_data, extra_fields)
        except ImportExtraDataError as e:
            return e.error_payload

        group.save()

        return 200, {
            self.item_result_key: group,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        """Deletes a review group.

        This will disassociate the group from all review requests previously
        targetting the group, and permanently delete the group.

        It is best to only delete empty, unused groups, and to instead
        change a group to not be visible if it's on longer needed.
        """
        try:
            group = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, group):
            return self.get_no_access_error(request)

        group.delete()

        return 204, {}


review_group_resource = ReviewGroupResource()
