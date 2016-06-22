from __future__ import unicode_literals

import copy

from django.utils import six
from django.utils.encoding import force_unicode
from django.utils.six.moves.urllib.parse import quote as urllib_quote
from django.utils.translation import ugettext_lazy as _
from djblets.registries.errors import RegistrationError
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (SPECIAL_PARAMS,
                                       webapi_login_required,
                                       webapi_request_fields)
from djblets.webapi.resources.base import \
    WebAPIResource as DjbletsWebAPIResource
from djblets.webapi.resources.mixins.api_tokens import ResourceAPITokenMixin
from djblets.webapi.resources.mixins.queries import APIQueryUtilsMixin

from reviewboard.registries.registry import Registry
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required)
from reviewboard.webapi.models import WebAPIToken


CUSTOM_MIMETYPE_BASE = 'application/vnd.reviewboard.org'
EXTRA_DATA_LEN = len('extra_data.')
PRIVATE_KEY_PREFIX = '__'


class ExtraDataAccessLevel(object):
    """Various access levels for ``extra_data`` fields.

    This class consists of constants describing the various access levels for
    ``extra_data`` keys on :py:class:`~reviewboard.webapi.base.WebAPIResource`
    subclasses.
    """

    #: The associated extra_data key can be retrieved and updated via the API.
    ACCESS_STATE_PUBLIC = 1

    #: The associated extra_data key can only be retrieved via the API.
    ACCESS_STATE_PUBLIC_READONLY = 2

    #: The associated extra_data key cannot be accessed via the API.
    ACCESS_STATE_PRIVATE = 3


NOT_CALLABLE = 'not_callable'


class CallbackRegistry(Registry):
    item_name = 'callback'

    errors = {
        NOT_CALLABLE: _(
            'Could not register %(item)s: it is not callable.'
        ),
    }

    def register(self, item):
        """Register a callback.

        Args:
            item (callable):
                The item to register.

        Raises:
            djblets.registries.errors.RegistrationError:
                Raised if the item is not a callable.

            djblets.registries.errors.AlreadyRegisteredError:
                Raised if the item is already registered.
        """
        self.populate()

        if not callable(item):
            raise RegistrationError(self.format_error(NOT_CALLABLE,
                                                      item=item))

        super(CallbackRegistry, self).register(item)


class WebAPIResource(ResourceAPITokenMixin, APIQueryUtilsMixin,
                     DjbletsWebAPIResource):
    """A specialization of the Djblets WebAPIResource for Review Board."""

    autogenerate_etags = True
    mimetype_vendor = 'reviewboard.org'
    api_token_model = WebAPIToken

    def __init__(self, *args, **kwargs):
        super(WebAPIResource, self).__init__(*args, **kwargs)

        self.extra_data_access_callbacks = CallbackRegistry()

    def has_access_permissions(self, *args, **kwargs):
        # By default, raise an exception if this is called. Specific resources
        # will have to explicitly override this and opt-in to access.
        raise NotImplementedError(
            '%s must provide a has_access_permissions method'
            % self.__class__.__name__)

    def serialize_extra_data_field(self, obj, request=None):
        """Serialize a resource's ``extra_data`` field.

        Args:
            obj (django.db.models.Model):
                The model of a given resource.

            request (HttpRequest):
                The HTTP request from the client.

        Returns:
            dict:
                A serialized ``extra_data`` field or, ``None``.
        """
        if obj.extra_data is not None:
            return self._strip_private_data(obj.extra_data)

        return None

    @webapi_check_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsWebAPIResource)
    def get(self, *args, **kwargs):
        """Returns the serialized object for the resource.

        This will require login if anonymous access isn't enabled on the
        site.
        """
        pass

    @webapi_check_login_required
    @webapi_check_local_site
    @webapi_request_fields(
        optional=dict({
            'counts-only': {
                'type': bool,
                'description': 'If specified, a single ``count`` field is '
                               'returned with the number of results, instead '
                               'of the results themselves.',
            },
        }, **DjbletsWebAPIResource.get_list.optional_fields),
        required=DjbletsWebAPIResource.get_list.required_fields,
        allow_unknown=True
    )
    def get_list(self, request, *args, **kwargs):
        """Returns a list of objects.

        This will require login if anonymous access isn't enabled on the
        site.

        If ``?counts-only=1`` is passed on the URL, then this will return
        only a ``count`` field with the number of entries, instead of the
        serialized objects.
        """
        if self.model and request.GET.get('counts-only', False):
            return 200, {
                'count': self.get_queryset(request, is_list=True,
                                           *args, **kwargs).count()
            }
        else:
            return self._get_list_impl(request, *args, **kwargs)

    @webapi_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsWebAPIResource)
    def delete(self, *args, **kwargs):
        pass

    def _get_list_impl(self, request, *args, **kwargs):
        """Actual implementation to return the list of results.

        This by default calls the parent WebAPIResource.get_list, but this
        can be overridden by subclasses to provide a more custom
        implementation while still retaining the ?counts-only=1 functionality.
        """
        return super(WebAPIResource, self).get_list(request, *args, **kwargs)

    def can_import_extra_data_field(self, obj, field):
        """Returns whether a particular field in extra_data can be imported.

        Subclasses can use this to limit which fields are imported by
        import_extra_data. By default, all fields can be imported.
        """
        return True

    def build_resource_url(self, name, local_site_name=None, request=None,
                           **kwargs):
        """Build the URL to a resource, factoring in Local Sites.

        Args:
            name (unicode):
                The resource name.

            local_site_name (unicode):
                The LocalSite name.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            kwargs (dict):
                The keyword arguments needed for URL resolution.

        Returns:
            unicode: The resulting absolute URL to the resource.
        """
        url = local_site_reverse(
            self._build_named_url(name),
            local_site_name=local_site_name,
            request=request,
            kwargs=kwargs)

        if request:
            return request.build_absolute_uri(url)

        return url

    def _get_local_site(self, local_site_name):
        if local_site_name:
            return LocalSite.objects.get(name=local_site_name)
        else:
            return None

    def _get_form_errors(self, form):
        fields = {}

        for field in form.errors:
            fields[field] = [force_unicode(e) for e in form.errors[field]]

        return fields

    def import_extra_data(self, obj, extra_data, fields):
        for key, value in six.iteritems(fields):
            if key.startswith('extra_data.'):
                key = key[EXTRA_DATA_LEN:]

                if self._should_process_extra_data(key, obj):
                    if value != '':
                        if value in ('true', 'True', 'TRUE'):
                            value = True
                        elif value in ('false', 'False', 'FALSE'):
                            value = False
                        else:
                            try:
                                value = int(value)
                            except ValueError:
                                try:
                                    value = float(value)
                                except ValueError:
                                    pass

                        extra_data[key] = value
                    elif key in extra_data:
                        del extra_data[key]

    def _should_process_extra_data(self, key, obj):
        """Check if an ``extra_data`` field should be processed.

        Args:
            key (unicode):
                A key for an extra_data field.

            obj (django.db.models.Model):
                The model of a given resource.

        Returns:
            bool:
                Whether the extra_data field should be processed or not.
        """
        return (self.can_import_extra_data_field(obj, key) and
                not key.startswith(PRIVATE_KEY_PREFIX) and
                self.get_extra_data_field_state((key,)) ==
                ExtraDataAccessLevel.ACCESS_STATE_PUBLIC)

    def _build_redirect_with_args(self, request, new_url):
        """Builds a redirect URL with existing query string arguments.

        This will construct a URL that contains all the query string arguments
        provided in this request.

        This will not include the special arguments handled by the base
        WebAPIResource in Djblets. Those will be specially added
        automatically, so there's no need to do this twice here.
        """
        query_str = '&'.join([
            '%s=%s' % (urllib_quote(key), urllib_quote(value))
            for key, value in six.iteritems(request.GET)
            if key not in SPECIAL_PARAMS
        ])

        if '?' in new_url:
            new_url += '&' + query_str
        else:
            new_url += '?' + query_str

        return new_url

    def get_extra_data_field_state(self, key_path):
        """Return the state of a registered ``extra_data`` key path.

        Example:
        .. code-block:: python

           resource.extra_data = {
               'public': 'foo',
               'private': 'secret',
               'data': {
                   'secret_key': 'secret_data',
               },
               'readonly': 'bar',
           }

           key_path = ('data', 'secret_key',)
           resource.get_extra_data_field_state(key_path)

        Args:
            key_path (tuple):
                The path of the ``extra_data`` key as a :py:class`tuple` of
                :py:class:`unicode` strings.

        Returns:
            int:
            The access state of the provided key.
        """
        for callback in self.extra_data_access_callbacks:
            value = callback(key_path)

            if value is not None:
                return value

        return ExtraDataAccessLevel.ACCESS_STATE_PUBLIC

    def _strip_private_data(self, extra_data, parent_path=None):
        """Strip private fields from an extra data object.

        This function creates a clone of the provided object and traverses it
        and any nested dictionaries to remove any private fields.

        Args:
            extra_data (dict):
                The object from which to strip private fields.

            parent_path (tuple):
                Parent key path leading to provided ``extra_data``
                dictionary.

        Returns:
            dict:
            A clone of the ``extra_data`` stripped of its private fields.
        """
        clone = copy.copy(extra_data)

        for field_name, value in six.iteritems(extra_data):
            if parent_path:
                path = parent_path + (field_name,)
            else:
                path = (field_name,)

            if (field_name.startswith(PRIVATE_KEY_PREFIX) or
                self.get_extra_data_field_state(path) ==
                ExtraDataAccessLevel.ACCESS_STATE_PRIVATE):
                del clone[field_name]
            elif isinstance(value, dict):
                clone[field_name] = self._strip_private_data(value, path)

        return clone
