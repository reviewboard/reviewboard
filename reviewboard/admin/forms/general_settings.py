"""Administration form for general Review Board settings."""

from __future__ import unicode_literals

from collections import OrderedDict

from django import forms
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.utils import six
from django.utils.module_loading import import_string
from django.utils.six.moves.urllib.parse import urlparse
from django.utils.translation import (ugettext,
                                      ugettext_lazy as _)
from djblets.cache.backend_compat import normalize_cache_backend
from djblets.cache.forwarding_backend import DEFAULT_FORWARD_CACHE_ALIAS
from djblets.forms.fields import TimeZoneField
from djblets.siteconfig.forms import SiteSettingsForm

from reviewboard.admin.siteconfig import load_site_config


class BaseCacheSettingsForm(forms.Form):
    """Base class for a cache backend settings form.

    Version Added:
        4.0
    """

    def load(self, cache_backend_settings):
        """Load the cache backend settings into the form.

        Args:
            cache_backend_settings (dict):
                Settings for the cache backend.
        """
        pass

    def build_cache_backend_settings(self):
        """Build new cache backend settings from the form data.

        Returns:
            dict:
            The new cache backend settings.
        """
        raise NotImplementedError


class FileCacheSettingsForm(BaseCacheSettingsForm):
    """Settings for the file-based cache backend.

    This backend is recommended only for simple test setups and development.
    """

    cache_path = forms.CharField(
        label=_('Cache Path'),
        help_text=_(
            'The file location for the cache. This must be writable by '
            'the web server.'
        ),
        required=True,
        widget=forms.TextInput(attrs={'size': '50'}),
        error_messages={
            'required': 'A valid cache path must be provided.'
        })

    def load(self, cache_backend_settings):
        """Load the cache backend settings into the form.

        Args:
            cache_backend_settings (dict):
                Settings for the cache backend.
        """
        cache_locations = cache_backend_settings['LOCATION']

        if not isinstance(cache_locations, list):
            cache_locations = [cache_locations]

        self.fields['cache_path'].initial = ';'.join(cache_locations)

    def build_cache_backend_settings(self):
        """Build new cache backend settings from the form data.

        Returns:
            dict:
            The new cache backend settings.
        """
        return {
            'LOCATION': self.cleaned_data['cache_path'],
        }

    def clean_cache_path(self):
        """Clean the cache_path field.

        This will strip whitespace around the value and return it.

        Returns:
            unicode:
            The cache path, with whitespace stripped.
        """
        return self.cleaned_data['cache_path'].strip()

    class Meta:
        title = _('Local File Cache Settings')


class LocalMemoryCacheSettingsForm(BaseCacheSettingsForm):
    """Settings for the local memory cache backend.

    This is only available for development setups and cannot be used in
    production.
    """

    def build_cache_backend_settings(self):
        """Build new cache backend settings from the form data.

        Returns:
            dict:
            The new cache backend settings.
        """
        # We want to specify a "reviewboard" location to keep items
        # separate from those in other caches.
        return {
            'LOCATION': 'reviewboard'
        }

    class Meta:
        title = _('Local Memory Cache Settings')


class MemcachedSettingsForm(BaseCacheSettingsForm):
    """Settings for the memcached backend.

    This is the recommended caching backend.
    """

    cache_host = forms.CharField(
        label=_('Cache Hosts'),
        help_text=_('The host or hosts used for the cache, in hostname:port '
                    'form. Multiple hosts can be specified by separating '
                    'them with a semicolon (;).'),
        required=True,
        widget=forms.TextInput(attrs={'size': '50'}),
        error_messages={
            'required': 'A valid cache host must be provided.'
        })

    def load(self, cache_backend_settings):
        """Load the cache backend settings into the form.

        Args:
            cache_backend_settings (dict):
                Settings for the cache backend.
        """
        cache_locations = cache_backend_settings['LOCATION']

        if not isinstance(cache_locations, list):
            cache_locations = [cache_locations]

        self.fields['cache_host'].initial = ';'.join(cache_locations)

    def build_cache_backend_settings(self):
        """Build new cache backend settings from the form data.

        Returns:
            dict:
            The new cache backend settings.
        """
        return {
            'LOCATION': self.cleaned_data['cache_host'].split(';'),
        }

    def clean_cache_host(self):
        """Clean the cache_host field.

        This will strip whitespace around the value and return it.

        Returns:
            unicode:
            The cache host, with whitespace stripped.
        """
        return self.cleaned_data['cache_host'].strip()

    class Meta:
        title = _('Memcached Settings')


class GeneralSettingsForm(SiteSettingsForm):
    """General settings for Review Board."""

    _cache_backends = OrderedDict([
        ('locmem', {
            'name': _('Local memory cache (developer-only)'),
            'available': not settings.PRODUCTION,
            'backend_cls_path':
                'django.core.cache.backends.locmem.LocMemCache',
            'form_cls': LocalMemoryCacheSettingsForm,
        }),
        ('memcached', {
            'name': _('Memcached (recommended)'),
            'backend_cls_path':
                'django.core.cache.backends.memcached.MemcachedCache',
            'legacy_backend_cls_paths': [
                'django.core.cache.backends.memcached.CacheClass',
            ],
            'form_cls': MemcachedSettingsForm,

        }),
        ('file', {
            'name': _('Local file cache'),
            'backend_cls_path':
                'django.core.cache.backends.filebased.FileBasedCache',
            'form_cls': FileCacheSettingsForm,
        }),
    ])

    CACHE_VALIDATION_KEY = '__rb-cache-validation__'
    CACHE_VALIDATION_VALUE = 12345

    company = forms.CharField(
        label=_('Company/Organization'),
        help_text=_('The optional name of your company or organization. '
                    'This will be displayed on your support page.'),
        required=False,
        widget=forms.TextInput(attrs={'size': '30'}))

    server = forms.CharField(
        label=_('Server'),
        help_text=_('The URL of this Review Board server. This should not '
                    'contain the subdirectory Review Board is installed in.'),
        widget=forms.TextInput(attrs={'size': '30'}))

    site_read_only = forms.BooleanField(
        label=_('Enable read-only mode'),
        help_text=_('Prevent non-superusers from making any changes to '
                    'Review Board.'),
        required=False)

    read_only_message = forms.CharField(
        label=_('Read-only message'),
        help_text=_('A custom message displayed when the site is in '
                    'read-only mode.'),
        required=False,
        widget=forms.TextInput(attrs={'size': '30'}))

    site_media_url = forms.CharField(
        label=_('Media URL'),
        help_text=(_('The URL to the media files. Set to '
                     '<code>%smedia/</code> to use the default media path on '
                     'this server.')
                   % settings.SITE_ROOT),
        required=True,
        widget=forms.TextInput(attrs={'size': '30'}))

    site_static_url = forms.CharField(
        label=_('Static URL'),
        help_text=(_('The URL to the static files, such as JavaScript files, '
                     'CSS files, and images that are bundled with Review '
                     'Board or third-party extensions. Set to '
                     '<code>%sstatic/</code> to use the default static path '
                     'on this server.')
                   % settings.SITE_ROOT),
        required=True,
        widget=forms.TextInput(attrs={'size': '30'}))

    site_admin_name = forms.CharField(
        label=_('Administrator Name'),
        required=True,
        widget=forms.TextInput(attrs={'size': '30'}))
    site_admin_email = forms.EmailField(
        label=_('Administrator E-Mail'),
        required=True,
        widget=forms.TextInput(attrs={'size': '30'}))

    locale_timezone = TimeZoneField(
        label=_('Time Zone'),
        required=True,
        help_text=_('The time zone used for all dates on this server.'))

    cache_type = forms.ChoiceField(
        label=_('Cache Backend'),
        help_text=_('The type of server-side caching to use.'),
        required=True,
        widget=forms.Select(attrs={
            'data-subform-group': 'cache-backend',
        }))

    def __init__(self, siteconfig, data=None, files=None, *args, **kwargs):
        """Initialize the settings form.

        Args:
            siteconfig (djblets.siteconfig.models.SiteConfiguration):
                The site configuration being changed.

            data (dict, optional):
                The submitted form data.

            files (dict, optional):
                The uploaded file data.

            *args (tuple):
                Additional positional arguments for the form.

            **kwargs (dict):
                Additional keyword arguments for the form.
        """
        self.cache_backend_forms = {
            backend_id: backend_info['form_cls'](data=data, files=files)
            for backend_id, backend_info in six.iteritems(self._cache_backends)
            if backend_info.get('available', True)
        }

        super(GeneralSettingsForm, self).__init__(siteconfig,
                                                  data=data,
                                                  files=files,
                                                  *args, **kwargs)

    def load(self):
        """Load settings from the form.

        This will populate initial fields based on the site configuration.
        It takes care to transition legacy (<= Review Board 1.7) cache
        backends, if still used in production, to a modern configuration.
        """
        domain_method = self.siteconfig.get('site_domain_method')
        site = Site.objects.get_current()

        # Load the rest of the settings from the form.
        super(GeneralSettingsForm, self).load()

        # Load the cache settings.
        cache_backend_info = self.siteconfig.get('cache_backend')
        cache_backend = (
            normalize_cache_backend(cache_backend_info,
                                    DEFAULT_FORWARD_CACHE_ALIAS) or
            normalize_cache_backend(cache_backend_info))

        cache_backend_path = cache_backend['BACKEND']
        cache_type = 'custom'

        for _cache_type, backend_info in six.iteritems(self._cache_backends):
            if (cache_backend_path == backend_info['backend_cls_path'] or
                cache_backend_path in backend_info.get(
                    'legacy_backend_cls_paths', [])):
                cache_type = _cache_type
                break

        cache_type_choices = [
            (backend_id, backend_info['name'])
            for backend_id, backend_info in six.iteritems(self._cache_backends)
            if backend_info.get('available', True)
        ]

        if cache_type == 'custom':
            cache_type_choices.append(('custom', ugettext('Custom')))

        cache_type_field = self.fields['cache_type']
        cache_type_field.choices = tuple(cache_type_choices)
        cache_type_field.initial = cache_type

        if cache_type in self.cache_backend_forms:
            self.cache_backend_forms[cache_type].load(cache_backend)

        # This must come after we've loaded the general settings.
        self.fields['server'].initial = '%s://%s' % (domain_method,
                                                     site.domain)

    def save(self):
        """Save the form.

        This will write the new configuration to the database. It will then
        force a site configuration reload.
        """
        server = self.cleaned_data['server']

        if '://' not in server:
            # urlparse doesn't properly handle URLs without a scheme. It
            # believes the domain is actually the path. So we apply a prefix.
            server = 'http://' + server

        url_parts = urlparse(server)
        domain_method = url_parts[0]
        domain_name = url_parts[1]

        if domain_name.endswith('/'):
            domain_name = domain_name[:-1]

        site = Site.objects.get_current()

        if site.domain != domain_name:
            site.domain = domain_name
            site.save(update_fields=['domain'])

        self.siteconfig.set('site_domain_method', domain_method)

        cache_type = self.cleaned_data['cache_type']

        if cache_type != 'custom':
            cache_backend_info = self._cache_backends[cache_type]
            cache_form = self.cache_backend_forms[cache_type]
            cache_backend_settings = cache_form.build_cache_backend_settings()

            self.siteconfig.set('cache_backend', {
                DEFAULT_FORWARD_CACHE_ALIAS: dict({
                    'BACKEND': cache_backend_info['backend_cls_path'],
                }, **cache_backend_settings),
            })

        super(GeneralSettingsForm, self).save()

        # Reload any important changes into the Django settings.
        load_site_config()

    def is_valid(self):
        """Return whether the form is valid.

        This will check that this form, and the form for any selected cache
        backend, is valid.

        Returns:
            bool:
            ``True`` if all form fields are valid. ``False`` if any are
            invalid.
        """
        if not super(GeneralSettingsForm, self).is_valid():
            return False

        cache_form = self.cache_backend_forms.get(
            self.cleaned_data['cache_type'])

        return cache_form is None or cache_form.is_valid()

    def clean(self):
        """Clean and validate the form fields.

        This is called after all individual fields are validated. It does
        the remaining work of checking to make sure the resulting configuration
        is valid.

        Returns:
            dict:
            The cleaned form data.
        """
        cleaned_data = super(GeneralSettingsForm, self).clean()

        if 'cache_type' not in self.errors:
            cache_type = cleaned_data['cache_type']
            cache_backend_info = self._cache_backends.get(cache_type)
            cache_form = self.cache_backend_forms.get(cache_type)

            if (cache_backend_info is not None and
                cache_form is not None and
                cache_form.is_valid()):
                cache_backend = None

                try:
                    cache_backend_settings = \
                        cache_form.build_cache_backend_settings()

                    cache_cls = import_string(
                        cache_backend_info['backend_cls_path'])
                    cache_backend = cache_cls(
                        cache_backend_settings.get('LOCATION'),
                        {})

                    cache_backend.set(self.CACHE_VALIDATION_KEY,
                                      self.CACHE_VALIDATION_VALUE)
                    value = cache_backend.get(self.CACHE_VALIDATION_KEY)
                    cache_backend.delete(self.CACHE_VALIDATION_KEY)

                    if value != self.CACHE_VALIDATION_VALUE:
                        self.errors['cache_type'] = self.error_class([
                            _('Unable to store and retrieve values from this '
                              'caching backend. There may be a problem '
                              'connecting.')
                        ])
                except Exception as e:
                    self.errors['cache_type'] = self.error_class([
                        _('Error with this caching configuration: %s')
                        % e
                    ])

                # If the cache backend is open, try closing it. This may fail,
                # so we want to ignore any failures.
                if cache_backend is not None:
                    try:
                        cache_backend.close()
                    except Exception:
                        pass

        return cleaned_data

    class Meta:
        title = _('General Settings')
        save_blacklist = ('server', 'cache_type')

        subforms = (
            {
                'subforms_attr': 'cache_backend_forms',
                'controller_field': 'cache_type',
            },
        )

        fieldsets = (
            {
                'title': _('Site Settings'),
                'classes': ('wide',),
                'fields': ('company', 'server', 'site_media_url',
                           'site_static_url', 'site_admin_name',
                           'site_admin_email', 'locale_timezone',
                           'site_read_only', 'read_only_message'),
            },
            {
                'title': _('Cache Settings'),
                'classes': ('wide',),
                'fields': ('cache_type',),
            },
        )
