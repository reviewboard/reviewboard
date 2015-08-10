from __future__ import unicode_literals

from django.conf.urls import patterns, include
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.utils import six

from djblets.extensions.errors import (DisablingExtensionError,
                                       EnablingExtensionError,
                                       InvalidExtensionError)
from djblets.extensions.models import RegisteredExtension
from djblets.urls.resolvers import DynamicURLResolver
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_permission_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST,
                                   ENABLE_EXTENSION_FAILED,
                                   DISABLE_EXTENSION_FAILED,
                                   PERMISSION_DENIED)
from djblets.webapi.resources import WebAPIResource


class ExtensionResource(WebAPIResource):
    """Provides information on installed extensions."""
    model = RegisteredExtension
    fields = {
        'author': {
            'type': str,
            'description': 'The author of the extension.',
        },
        'author_url': {
            'type': str,
            'description': "The author's website.",
        },
        'can_disable': {
            'type': bool,
            'description': 'Whether or not the extension can be disabled.',
        },
        'can_enable': {
            'type': bool,
            'description': 'Whether or not the extension can be enabled.',
        },
        'class_name': {
            'type': str,
            'description': 'The class name for the extension.',
        },
        'enabled': {
            'type': bool,
            'description': 'Whether or not the extension is enabled.',
        },
        'installed': {
            'type': bool,
            'description': 'Whether or not the extension is installed.',
        },
        'loadable': {
            'type': bool,
            'description': 'Whether or not the extension is currently '
                           'loadable. An extension may be installed but '
                           'missing or may be broken due to a bug.',
        },
        'load_error': {
            'type': str,
            'description': 'If the extension could not be loaded, this will '
                           'contain any errors captured while trying to load.',
        },
        'name': {
            'type': str,
            'description': 'The name of the extension.',
        },
        'summary': {
            'type': str,
            'description': "A summary of the extension's functionality.",
        },
        'version': {
            'type': str,
            'description': 'The installed version of the extension.',
        },
    }
    name = 'extension'
    plural_name = 'extensions'
    uri_object_key = 'extension_name'
    uri_object_key_regex = r'[.A-Za-z0-9_-]+'
    model_object_key = 'class_name'

    allowed_methods = ('GET', 'PUT')

    def __init__(self, extension_manager):
        super(ExtensionResource, self).__init__()
        self._extension_manager = extension_manager
        self._dynamic_patterns = DynamicURLResolver()
        self._resource_url_patterns_map = {}

        # We want ExtensionResource to notice when extensions are
        # initialized or uninitialized, so connect some methods to
        # those signals.
        from djblets.extensions.signals import (extension_initialized,
                                                extension_uninitialized)
        extension_initialized.connect(self._on_extension_initialized)
        extension_uninitialized.connect(self._on_extension_uninitialized)

    def serialize_author_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return None

        return extension.extension_class.info.author

    def serialize_author_url_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return None

        return extension.extension_class.info.author_url

    def serialize_can_disable_field(self, extension, *args, **kwargs):
        return self._extension_manager.get_can_disable_extension(extension)

    def serialize_can_enable_field(self, extension, *args, **kwargs):
        return self._extension_manager.get_can_enable_extension(extension)

    def serialize_loadable_field(self, ext, *args, **kwargs):
        return (ext.extension_class is not None and
                ext.class_name not in self._extension_manager._load_errors)

    def serialize_load_error_field(self, extension, *args, **kwargs):
        return self._extension_manager._load_errors.get(extension.class_name)

    def serialize_name_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return extension.name
        else:
            return extension.extension_class.info.name

    def serialize_summary_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return None

        return extension.extension_class.info.summary

    def serialize_version_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return None

        return extension.extension_class.info.version

    @webapi_response_errors(DOES_NOT_EXIST, PERMISSION_DENIED)
    @webapi_login_required
    def get_list(self, request, *args, **kwargs):
        """Returns the list of known extensions.

        Each extension in the list has been installed, but may not be
        enabled.
        """
        return WebAPIResource.get_list(self, request, *args, **kwargs)

    def get_links(self, resources=[], obj=None, request=None, *args, **kwargs):
        links = super(ExtensionResource, self).get_links(
            resources, obj, request=request, *args, **kwargs)

        if request and obj:
            admin_base_href = '%s%s' % (
                request.build_absolute_uri(reverse('extension-list')),
                obj.class_name)

            extension_cls = obj.extension_class

            if extension_cls:
                extension_info = extension_cls.info

                if extension_info.is_configurable:
                    links['admin-configure'] = {
                        'method': 'GET',
                        'href': '%s/config/' % admin_base_href,
                    }

                if extension_info.has_admin_site:
                    links['admin-database'] = {
                        'method': 'GET',
                        'href': '%s/db/' % admin_base_href,
                    }

        return links

    @webapi_login_required
    @webapi_permission_required('extensions.change_registeredextension')
    @webapi_response_errors(PERMISSION_DENIED, DOES_NOT_EXIST,
                            ENABLE_EXTENSION_FAILED, DISABLE_EXTENSION_FAILED)
    @webapi_request_fields(
        required={
            'enabled': {
                'type': bool,
                'description': 'Whether or not to make the extension active.'
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates the state of the extension.

        If ``enabled`` is true, then the extension will be enabled, if it is
        not already. If false, it will be disabled.
        """
        # Try to find the registered extension
        try:
            registered_extension = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        extension_id = registered_extension.class_name

        if kwargs.get('enabled'):
            try:
                self._extension_manager.enable_extension(extension_id)
            except EnablingExtensionError as e:
                err = ENABLE_EXTENSION_FAILED.with_message(six.text_type(e))

                return err, {
                    'load_error': e.load_error,
                    'needs_reload': e.needs_reload,
                }
            except InvalidExtensionError as e:
                raise
                return ENABLE_EXTENSION_FAILED.with_message(six.text_type(e))
        else:
            try:
                self._extension_manager.disable_extension(extension_id)
            except (DisablingExtensionError, InvalidExtensionError) as e:
                return DISABLE_EXTENSION_FAILED.with_message(six.text_type(e))

        # Refetch extension, since the ExtensionManager may have changed
        # the model.
        registered_extension = \
            RegisteredExtension.objects.get(pk=registered_extension.pk)

        return 200, {
            self.item_result_key: registered_extension
        }

    def get_url_patterns(self):
        # We want extension resource URLs to be dynamically modifiable,
        # so we override get_url_patterns in order to capture and store
        # a reference to the url_patterns at /api/extensions/.
        url_patterns = super(ExtensionResource, self).get_url_patterns()
        url_patterns += patterns('', self._dynamic_patterns)

        return url_patterns

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        """Returns links to the resources provided by the extension.

        The result should be a dictionary of link names to a dictionary of
        information. The information should contain:

        * 'method' - The HTTP method
        * 'href' - The URL
        * 'title' - The title of the link (optional)
        * 'resource' - The WebAPIResource instance
        * 'list-resource' - True if this links to a list resource (optional)
        """
        links = {}

        if obj and obj.enabled:
            extension = obj.get_extension_class()

            if not extension:
                return links

            for resource in extension.resources:
                links[resource.name_plural] = {
                    'method': 'GET',
                    'href': "%s%s/" % (
                        self.get_href(obj, request, *args, **kwargs),
                        resource.uri_name),
                    'resource': resource,
                    'list-resource': not resource.singleton,
                }

        return links

    def _attach_extension_resources(self, extension):
        """
        Attaches an extension's resources to /api/extensions/{extension.id}/.
        """

        # Bail out if there are no resources to attach
        if not extension.resources:
            return

        if extension in self._resource_url_patterns_map:
            # This extension already had its urlpatterns
            # mapped and attached.  Nothing to do here.
            return

        # We're going to store references to the URL patterns
        # that are generated for this extension's resources.
        self._resource_url_patterns_map[extension] = []

        # For each resource, generate the URLs
        for resource in extension.resources:
            self._resource_url_patterns_map[extension].extend(patterns(
                '',
                (r'^%s/%s/' % (extension.id, resource.uri_name),
                 include(resource.get_url_patterns()))))

        self._dynamic_patterns.add_patterns(
            self._resource_url_patterns_map[extension])

    def _unattach_extension_resources(self, extension):
        """
        Unattaches an extension's resources from
        /api/extensions/{extension.id}/.
        """

        # Bail out if there are no resources for this extension
        if not extension.resources:
            return

        # If this extension has never had its resource URLs
        # generated, then we don't have anything to worry
        # about.
        if extension not in self._resource_url_patterns_map:
            return

        # Remove the URL patterns
        self._dynamic_patterns.remove_patterns(
            self._resource_url_patterns_map[extension])

        # Delete the URL patterns so that we can regenerate
        # them when the extension is re-enabled.  This is to
        # avoid caching incorrect URL patterns during extension
        # development, when extension resources are likely to
        # change.
        del self._resource_url_patterns_map[extension]

    def _on_extension_initialized(self, sender, ext_class=None, **kwargs):
        """
        Signal handler that notices when an extension has been initialized.
        """
        self._attach_extension_resources(ext_class)

    def _on_extension_uninitialized(self, sender, ext_class=None, **kwargs):
        """
        Signal handler that notices and reacts when an extension
        has been uninitialized.
        """
        self._unattach_extension_resources(ext_class)
