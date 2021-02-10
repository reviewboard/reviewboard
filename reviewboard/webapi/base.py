from __future__ import unicode_literals

import copy
import json
import logging

from django.utils import six
from django.utils.encoding import force_text
from django.utils.six.moves.urllib.parse import quote as urllib_quote
from django.utils.translation import ugettext_lazy as _
from djblets.registries.errors import RegistrationError
from djblets.util.decorators import augment_method_from
from djblets.util.json_utils import (JSONPatchError, json_merge_patch,
                                     json_patch)
from djblets.webapi.decorators import (SPECIAL_PARAMS,
                                       webapi_login_required,
                                       webapi_request_fields)
from djblets.webapi.errors import INVALID_FORM_DATA, PERMISSION_DENIED
from djblets.webapi.fields import BooleanFieldType
from djblets.webapi.resources.base import \
    WebAPIResource as DjbletsWebAPIResource
from djblets.webapi.resources.mixins.api_tokens import ResourceAPITokenMixin
from djblets.webapi.resources.mixins.oauth2_tokens import (
    ResourceOAuth2TokenMixin)
from djblets.webapi.resources.mixins.queries import APIQueryUtilsMixin

from reviewboard.admin.read_only import is_site_read_only_for
from reviewboard.registries.registry import Registry
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required)
from reviewboard.webapi.errors import READ_ONLY_ERROR
from reviewboard.webapi.models import WebAPIToken


CUSTOM_MIMETYPE_BASE = 'application/vnd.reviewboard.org'
EXTRA_DATA_LEN = len('extra_data.')
PRIVATE_KEY_PREFIX = '__'
NOT_CALLABLE = 'not_callable'


logger = logging.getLogger(__name__)


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


class ImportExtraDataError(ValueError):
    """Error importing extra_data from a client request.

    This often represents a JSON parse error or format error with a patch.
    Details are available in the message, and a suitable API error payload
    is provided.
    """

    @property
    def error_payload(self):
        """The error payload to send to the client."""
        return INVALID_FORM_DATA, {
            'fields': {
                'extra_data': [six.text_type(self)],
            },
        }


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


class RBResourceMixin(APIQueryUtilsMixin, ResourceAPITokenMixin,
                      ResourceOAuth2TokenMixin):
    """A mixin for Review Board resources.

    This mixin is intended to be used by the base Review Board
    :py:class:`WebAPIResource` and in subclasses of resources from other
    packages (e.g., Djblets) to specialize them for Review Board.
    """

    autogenerate_etags = True
    mimetype_vendor = 'reviewboard.org'
    api_token_model = WebAPIToken

    #: An optional set of required features to communicate with this resource.
    #:
    #: If no features are listed here, the resource will behave normally.
    #: However, if one or more features are listed here and are **not**
    #: enabled, the resource will return a 403 Forbidden error.
    required_features = []


class WebAPIResource(RBResourceMixin, DjbletsWebAPIResource):
    """A specialization of the Djblets WebAPIResource for Review Board."""

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
            A serialized ``extra_data`` field or ``None``.
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
                'type': BooleanFieldType,
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
        """Return whether a top-level field in extra_data can be imported.

        Subclasses can use this to limit which fields are imported by
        :py:meth:`import_extra_data`. By default, all fields can be imported.

        Note that this only supports top-level keys, and is mostly here for
        legacy reasons. Subclasses generally should override
        :py:meth:`get_extra_data_field_state` to provide more fine-grained
        access to content.

        Args:
            obj (object):
                The object being serialized for the resource.

            field (unicode):
                The field being considered for import.

        Returns:
            bool:
            ``True`` if the field can be imported. ``False`` if it should be
            ignored.
        """
        return True

    def get_extra_data_field_state(self, key_path):
        """Return the state of a registered ``extra_data`` key path.

        Args:
            key_path (tuple):
                The path of the ``extra_data`` key as a :py:class:`tuple` of
                :py:class:`unicode` strings.

        Returns:
            int:
            The access state of the provided key.

        Example:
            .. code-block:: python

               obj.extra_data = {
                   'public': 'foo',
                   'private': 'secret',
                   'data': {
                       'secret_key': 'secret_data',
                   },
                   'readonly': 'bar',
               }

               ...

               key_path = ('data', 'secret_key')
               resource.get_extra_data_field_state(key_path)
        """
        # Check each part of the key, making sure none is private.
        for key in key_path:
            if key.startswith(PRIVATE_KEY_PREFIX):
                return ExtraDataAccessLevel.ACCESS_STATE_PRIVATE

        # Now check for any registered callbacks used to compute access levels.
        for callback in self.extra_data_access_callbacks:
            value = callback(key_path)

            if value is not None:
                return value

        return ExtraDataAccessLevel.ACCESS_STATE_PUBLIC

    def call_method_view(self, request, method, view, *args, **kwargs):
        """Call the given method view.

        The default behaviour is to call the given ``view`` passing in all
        ``args`` and ``kwargs``. However, Review Board allows certain resources
        to be disabled by setting the :py:attr:`~required_features` attribute.
        If a feature specified in that list is disabled, this method will
        return a 403 Forbidden response instead of calling the method view.

        In addition, Review Board has token access policies. If the client is
        authenticated with an API token, the token's access policies will be
        checked before calling the view. If the operation is disallowed, a 403
        Forbidden response will be returned.

        If read-only mode is enabled, all PUT, POST, and DELETE requests will
        be rejected with a 503 Service Unavailable response, unless the user
        is a superuser.

        Only if all these conditions are met will the view actually be called.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            method (unicode):
                The HTTP method.

            view (callable):
                The view.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            WebAPIError or tuple:
            Either a 403 Forbidden error or the result of calling the method
            view, which will either be a
            :py:class:`~djblets.webapi.errors.WebAPIError` or a 2-tuple of the
            HTTP status code and a dict indicating the JSON response from the
            view.
        """
        for feature in self.required_features:
            if not feature.is_enabled(request=request):
                logger.warning('Disallowing %s for API resource %r because '
                               'feature %s is not enabled',
                               method, self, feature.feature_id,
                               request=request)
                return PERMISSION_DENIED

        if (is_site_read_only_for(request.user) and
            request.method not in ('GET', 'HEAD', 'OPTIONS')):
            return READ_ONLY_ERROR

        return super(WebAPIResource, self).call_method_view(
            request, method, view, *args, **kwargs)

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
            fields[field] = [force_text(e) for e in form.errors[field]]

        return fields

    def import_extra_data(self, obj, extra_data, fields):
        """Import new extra_data content from the client.

        There are three methods for injecting new content into the object's
        ``extra_data`` JSON field:

        1. Simple key/value forms through setting
           :samp:`extra_data.{key}={value}`. This will convert boolean-like
           strings to booleans, numeric strings to integers or floats, and the
           rest are stored as strings. It's only intended for very simple data.

        2. A JSON Merge Patch document through setting
           :samp:`extra_data:json={patch}`. This is a simple way of setting new
           structured JSON content.

        3. A more complex JSON Patch document through setting
           :samp:`extra_data:json-patch={patch}`. This is a more advanced way
           of manipulating JSON data, allowing for sanity-checking of existing
           content, adding new keys/array indices, replacing existing
           keys/indices, deleting data, or copying/moving data. If any
           operation (including the sanity-checking) fails, the whole patch is
           aborted.

        All methods respect any access states that apply to the resource, and
        forbid both writing to keys starting with ``__`` and replacing the
        entire root of ``extra_data``.

        .. versionchanged:: 3.0

           Added support for ``extra_data:json`` and ``extra_data:json-patch``.

        Args:
            obj (django.db.models.Model):
                The object containing an ``extra_data`` field.

            extra_data (dict):
                The existing contents of the ``extra_data`` field. This will
                be updated directly.

            fields (dict):
                The fields being set in the request. This will be checked for
                ``extra_data:json``, ``extra_data:json-patch``, and any
                beginning with ``extra_data.``.

        Returns:
            bool:
            ``True`` if ``extra_data`` was at all modified. ``False`` if it
            wasn't.

        Raises:
            ImportExtraDataError:
                There was an error importing content into ``extra_data``. There
                may be a parse error or access error. Details are in the
                message.
        """
        updated = False

        # Check for a JSON Merge Patch. This is the simplest way to update
        # extra_data with new structured JSON content.
        if 'extra_data:json' in fields:
            try:
                patch = json.loads(fields['extra_data:json'])
            except ValueError as e:
                raise ImportExtraDataError(_('Could not parse JSON data: %s')
                                           % e)

            new_extra_data = json_merge_patch(
                extra_data,
                patch,
                can_write_key_func=lambda path, **kwargs:
                    self._can_write_extra_data_key(obj, path))

            # Save extra_data only if it remains a dictionary, so callers
            # can't replace the entire contents.
            if not isinstance(new_extra_data, dict):
                raise ImportExtraDataError(
                    _('extra_data:json cannot replace extra_data with a '
                      'non-dictionary type'))

            extra_data.clear()
            extra_data.update(new_extra_data)
            updated = True

        # Check for a JSON Patch. This is more advanced, and can be used in
        # conjunction with the JSON Merge Patch.
        if 'extra_data:json-patch' in fields:
            try:
                patch = json.loads(fields['extra_data:json-patch'])
            except ValueError as e:
                raise ImportExtraDataError(_('Could not parse JSON data: %s')
                                           % e)

            try:
                new_extra_data = json_patch(
                    extra_data,
                    patch,
                    can_read_key_func=self._can_read_extra_data_key,
                    can_write_key_func=lambda path, **kwargs:
                        self._can_write_extra_data_key(obj, path))

                extra_data.clear()
                extra_data.update(new_extra_data)
                updated = True
            except JSONPatchError as e:
                raise ImportExtraDataError(_('Failed to patch JSON data: %s')
                                           % e)

        # Support setting individual keys to simple values. This is the older
        # method of setting JSON data, and is no longer recommended for new
        # clients.
        for key, value in six.iteritems(fields):
            if key.startswith('extra_data.'):
                key = key[EXTRA_DATA_LEN:]

                if self._can_write_extra_data_key(obj, (key,)):
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
                        updated = True
                    elif key in extra_data:
                        del extra_data[key]
                        updated = True

        return updated

    def _can_write_extra_data_key(self, obj, path):
        """Return whether a particular key can be written to in extra_data.

        This will ensure that the root of the object cannot be directly
        modified, and that any access states are applied to the path. It will
        also check top-level keys to make sure the resource allows them to be
        imported.

        Args:
            obj (django.db.models.Model):
                The object that contains ``extra_data``.

            path (tuple):
                The path components as a tuple. Each will be a Unicode string.
                This will consist of keys for dictionaries and string-encoded
                indices for arrays.

        Returns:
            bool:
            ``True`` if the path can be written to. ``False`` if it cannot.
        """
        return (path != () and
                self.can_import_extra_data_field(obj, path[0]) and
                (self.get_extra_data_field_state(path) ==
                 ExtraDataAccessLevel.ACCESS_STATE_PUBLIC))

    def _can_read_extra_data_key(self, path, **kargs):
        """Return whether a particular key can be read from in extra_data.

        This will check the path against any registered access restrictions
        to ensure that private data cannot be read from.

        Args:
            path (tuple):
                The path components as a tuple. Each will be a Unicode string.
                This will consist of keys for dictionaries and string-encoded
                indices for arrays.

            **kwargs (dict):
                Additional keyword arguments from the caller.

        Returns:
            bool:
            ``True`` if the path can be read from. ``False`` if it cannot.
        """
        return (self.get_extra_data_field_state(path) !=
                ExtraDataAccessLevel.ACCESS_STATE_PRIVATE)

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

            if (self.get_extra_data_field_state(path) ==
                ExtraDataAccessLevel.ACCESS_STATE_PRIVATE):
                del clone[field_name]
            elif isinstance(value, dict):
                clone[field_name] = self._strip_private_data(value, path)

        return clone
