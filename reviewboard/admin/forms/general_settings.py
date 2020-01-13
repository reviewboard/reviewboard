"""Administration form for general Review Board settings."""

from __future__ import unicode_literals

from django import forms
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.utils import six
from django.utils.six.moves.urllib.parse import urlparse
from django.utils.translation import (ugettext,
                                      ugettext_lazy as _)
from djblets.cache.backend_compat import normalize_cache_backend
from djblets.cache.forwarding_backend import DEFAULT_FORWARD_CACHE_ALIAS
from djblets.forms.fields import TimeZoneField
from djblets.siteconfig.forms import SiteSettingsForm

try:
    # Django >= 1.7
    from django.utils.module_loading import import_string
except ImportError:
    # Django < 1.7
    from django.utils.module_loading import import_by_path as import_string

from reviewboard.admin.siteconfig import load_site_config


class GeneralSettingsForm(SiteSettingsForm):
    """General settings for Review Board."""

    CACHE_TYPE_CHOICES = (
        ('memcached', _('Memcached')),
        ('file', _('File cache')),
    )

    CACHE_BACKENDS_MAP = {
        'file': 'django.core.cache.backends.filebased.FileBasedCache',
        'memcached': 'django.core.cache.backends.memcached.MemcachedCache',
        'locmem': 'django.core.cache.backends.locmem.LocMemCache',
    }

    CACHE_TYPES_MAP = {
        'django.core.cache.backends.filebased.FileBasedCache': 'file',
        'django.core.cache.backends.memcached.CacheClass': 'memcached',
        'django.core.cache.backends.memcached.MemcachedCache': 'memcached',
        'django.core.cache.backends.locmem.LocMemCache': 'locmem',
    }

    CACHE_LOCATION_FIELD_MAP = {
        'file': 'cache_path',
        'memcached': 'cache_host',
    }

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
        choices=CACHE_TYPE_CHOICES,
        help_text=_('The type of server-side caching to use.'),
        required=True)

    cache_path = forms.CharField(
        label=_('Cache Path'),
        help_text=_('The file location for the cache.'),
        required=True,
        widget=forms.TextInput(attrs={'size': '50'}),
        error_messages={
            'required': 'A valid cache path must be provided.'
        })

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

        cache_type = self.CACHE_TYPES_MAP.get(cache_backend['BACKEND'],
                                              'custom')
        self.fields['cache_type'].initial = cache_type

        if settings.DEBUG:
            self.fields['cache_type'].choices += (
                ('locmem', ugettext('Local memory cache')),
            )

        if cache_type == 'custom':
            self.fields['cache_type'].choices += (
                ('custom', ugettext('Custom')),
            )
            cache_locations = []
        elif cache_type != 'locmem':
            cache_locations = cache_backend['LOCATION']

            if not isinstance(cache_locations, list):
                cache_locations = [cache_locations]

            location_field = self.CACHE_LOCATION_FIELD_MAP[cache_type]
            self.fields[location_field].initial = ';'.join(cache_locations)

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
            if cache_type == 'locmem':
                # We want to specify a "reviewboard" location to keep items
                # separate from those in other caches.
                location = 'reviewboard'
            else:
                location_field = self.CACHE_LOCATION_FIELD_MAP[cache_type]
                location = self.cleaned_data[location_field]

                if cache_type == 'memcached':
                    # memcached allows a list of servers, rather than just a
                    # string representing one.
                    location = location.split(';')

            self.siteconfig.set('cache_backend', {
                DEFAULT_FORWARD_CACHE_ALIAS: {
                    'BACKEND': self.CACHE_BACKENDS_MAP[cache_type],
                    'LOCATION': location,
                }
            })

        super(GeneralSettingsForm, self).save()

        # Reload any important changes into the Django settings.
        load_site_config()

    def full_clean(self):
        """Begin cleaning and validating all form fields.

        This is the beginning of the form validation process. Before cleaning
        the fields, this will set the "required" states for the caching
        fields, based on the chosen caching type. This will enable or disable
        validation for those particular fields.

        Returns:
            dict:
            The cleaned form data.
        """
        orig_required = {}
        cache_type = (self['cache_type'].data or
                      self.fields['cache_type'].initial)

        for iter_cache_type, field in six.iteritems(
                self.CACHE_LOCATION_FIELD_MAP):
            orig_required[field] = self.fields[field].required
            self.fields[field].required = (cache_type == iter_cache_type)

        cleaned_data = super(GeneralSettingsForm, self).full_clean()

        # Reset the required flags for any modified field.
        for field, required in six.iteritems(orig_required):
            self.fields[field].required = required

        return cleaned_data

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
            cache_location_field = \
                self.CACHE_LOCATION_FIELD_MAP.get(cache_type)

            if cache_location_field not in self.errors:
                cache_backend = None

                try:
                    cache_cls = import_string(
                        self.CACHE_BACKENDS_MAP[cache_type])
                    cache_backend = cache_cls(
                        cleaned_data.get(cache_location_field),
                        {})

                    cache_backend.set(self.CACHE_VALIDATION_KEY,
                                      self.CACHE_VALIDATION_VALUE)
                    value = cache_backend.get(self.CACHE_VALIDATION_KEY)
                    cache_backend.delete(self.CACHE_VALIDATION_KEY)

                    if value != self.CACHE_VALIDATION_VALUE:
                        self.errors[cache_location_field] = self.error_class([
                            _('Unable to store and retrieve values from this '
                              'caching backend. There may be a problem '
                              'connecting.')
                        ])
                except Exception as e:
                    self.errors[cache_location_field] = self.error_class([
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

    def clean_cache_host(self):
        """Validate that the cache_host field is provided if required.

        If valid, this will strip whitespace around the ``cache_host`` field
        and return it.

        Returns:
            unicode:
            The cache host, with whitespace stripped.

        Raises:
            django.core.exceptions.ValidationError:
                A cache host was not provided, and is required by the backend.
        """
        cache_host = self.cleaned_data['cache_host'].strip()

        if self.fields['cache_host'].required and not cache_host:
            raise ValidationError(
                ugettext('A valid cache host must be provided.'))

        return cache_host

    def clean_cache_path(self):
        """Validate that the cache_path field is provided if required.

        If valid, this will strip whitespace around the ``cache_path`` field
        and return it.

        Returns:
            unicode:
            The cache path, with whitespace stripped.

        Raises:
            django.core.exceptions.ValidationError:
                A cache path was not provided, and is required by the backend.
        """
        cache_path = self.cleaned_data['cache_path'].strip()

        if self.fields['cache_path'].required and not cache_path:
            raise ValidationError(
                ugettext('A valid cache path must be provided.'))

        return cache_path

    class Meta:
        title = _('General Settings')
        save_blacklist = ('server', 'cache_type', 'cache_host', 'cache_path')

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
                'fields': ('cache_type', 'cache_path', 'cache_host'),
            },
        )
