#
# reviewboard/admin/forms.py -- Form classes for the admin UI
#
# Copyright (c) 2008-2010  Christian Hammond
# Copyright (c) 2008-2010  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

import logging
import os
import re

from django import forms
from django.contrib.sites.models import Site
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils import six
from django.utils.six.moves.urllib.parse import urlparse
from django.utils.translation import ugettext as _
from djblets.cache.backend_compat import normalize_cache_backend
from djblets.cache.forwarding_backend import DEFAULT_FORWARD_CACHE_ALIAS
from djblets.forms.fields import TimeZoneField
from djblets.siteconfig.forms import SiteSettingsForm
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.forms.auth import LegacyAuthModuleSettingsForm
from reviewboard.admin.checks import (get_can_use_amazon_s3,
                                      get_can_use_openstack_swift,
                                      get_can_use_couchdb)
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.admin.support import get_install_key
from reviewboard.ssh.client import SSHClient


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

    company = forms.CharField(
        label=_("Company/Organization"),
        help_text=_("The optional name of your company or organization. "
                    "This will be displayed on your support page."),
        required=False,
        widget=forms.TextInput(attrs={'size': '30'}))

    server = forms.CharField(
        label=_("Server"),
        help_text=_("The URL of this Review Board server. This should not "
                    "contain the subdirectory Review Board is installed in."),
        widget=forms.TextInput(attrs={'size': '30'}))

    site_media_url = forms.CharField(
        label=_("Media URL"),
        help_text=_("The URL to the media files. Leave blank to use the "
                    "default media path on this server."),
        required=False,
        widget=forms.TextInput(attrs={'size': '30'}))

    site_static_url = forms.CharField(
        label=_('Static URL'),
        help_text=_('The URL to the static files, such as JavaScript files, '
                    'CSS files, and images that are bundled with Review Board '
                    'or third-party extensions. Leave blank to use the '
                    'default static path on this server.'),
        required=False,
        widget=forms.TextInput(attrs={'size': '30'}))

    site_admin_name = forms.CharField(
        label=_("Administrator Name"),
        required=True,
        widget=forms.TextInput(attrs={'size': '30'}))
    site_admin_email = forms.EmailField(
        label=_("Administrator E-Mail"),
        required=True,
        widget=forms.TextInput(attrs={'size': '30'}))

    locale_timezone = TimeZoneField(
        label=_("Time Zone"),
        required=True,
        help_text=_("The time zone used for all dates on this server."))

    search_enable = forms.BooleanField(
        label=_("Enable search"),
        help_text=_("Provides a search field for quickly searching through "
                    "review requests."),
        required=False)

    search_results_per_page = forms.IntegerField(
        label=_("Search results per page"),
        help_text=_("Number of search results to show per page."),
        min_value=1,
        required=False)

    search_index_file = forms.CharField(
        label=_("Search index directory"),
        help_text=_("The directory that search index data should be stored "
                    "in."),
        required=False,
        widget=forms.TextInput(attrs={'size': '50'}))

    cache_type = forms.ChoiceField(
        label=_("Cache Backend"),
        choices=CACHE_TYPE_CHOICES,
        help_text=_('The type of server-side caching to use.'),
        required=True)

    cache_path = forms.CharField(
        label=_("Cache Path"),
        help_text=_('The file location for the cache.'),
        required=True,
        widget=forms.TextInput(attrs={'size': '50'}))

    cache_host = forms.CharField(
        label=_("Cache Hosts"),
        help_text=_('The host or hosts used for the cache, in hostname:port '
                    'form. Multiple hosts can be specified by separating '
                    'them with a semicolon (;).'),
        required=True,
        widget=forms.TextInput(attrs={'size': '50'}))

    integration_gravatars = forms.BooleanField(
        label=_("Use Gravatar images"),
        help_text=_("Use gravatar.com for user avatars"),
        required=False)

    def load(self):
        """Load the form."""
        domain_method = self.siteconfig.get("site_domain_method")
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
                ('locmem', _('Local memory cache')),
            )

        if cache_type == 'custom':
            self.fields['cache_type'].choices += (
                ('custom', _('Custom')),
            )
            cache_locations = []
        elif cache_type != 'locmem':
            cache_locations = cache_backend['LOCATION']

            if not isinstance(cache_locations, list):
                cache_locations = [cache_locations]

            location_field = self.CACHE_LOCATION_FIELD_MAP[cache_type]
            self.fields[location_field].initial = ';'.join(cache_locations)

        # This must come after we've loaded the general settings.
        self.fields['server'].initial = "%s://%s" % (domain_method,
                                                     site.domain)

    def save(self):
        """Save the form."""
        server = self.cleaned_data['server']

        if "://" not in server:
            # urlparse doesn't properly handle URLs without a scheme. It
            # believes the domain is actually the path. So we apply a prefix.
            server = "http://" + server

        url_parts = urlparse(server)
        domain_method = url_parts[0]
        domain_name = url_parts[1]

        if domain_name.endswith("/"):
            domain_name = domain_name[:-1]

        site = Site.objects.get_current()
        site.domain = domain_name
        site.save()

        self.siteconfig.set("site_domain_method", domain_method)

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
        """Clean and validate all form fields."""
        cache_type = self['cache_type'].data or self['cache_type'].initial

        for iter_cache_type, field in six.iteritems(
                self.CACHE_LOCATION_FIELD_MAP):
            self.fields[field].required = (cache_type == iter_cache_type)

        return super(GeneralSettingsForm, self).full_clean()

    def clean_cache_host(self):
        """Validate that the cache_host field is provided if required."""
        cache_host = self.cleaned_data['cache_host'].strip()

        if self.fields['cache_host'].required and not cache_host:
            raise ValidationError(
                _('A valid cache host must be provided.'))

        return cache_host

    def clean_cache_path(self):
        """Validate that the cache_path field is provided if required."""
        cache_path = self.cleaned_data['cache_path'].strip()

        if self.fields['cache_path'].required and not cache_path:
            raise ValidationError(
                _('A valid cache path must be provided.'))

        return cache_path

    def clean_search_index_file(self):
        """Validate that the specified index file is valid.

        This checks to make sure that the provided file path is an absolute
        path, and that the directory is writable by the web server.
        """
        index_file = self.cleaned_data['search_index_file'].strip()

        if index_file:
            if not os.path.isabs(index_file):
                raise ValidationError(
                    _("The search index path must be absolute."))

            if (os.path.exists(index_file) and
                    not os.access(index_file, os.W_OK)):
                raise ValidationError(
                    _('The search index path is not writable. Make sure the '
                      'web server has write access to it and its parent '
                      'directory.'))

        return index_file

    class Meta:
        title = _("General Settings")
        save_blacklist = ('server', 'cache_type', 'cache_host', 'cache_path')

        fieldsets = (
            {
                'classes': ('wide',),
                'title': _("Site Settings"),
                'fields': ('company', 'server', 'site_media_url',
                           'site_static_url', 'site_admin_name',
                           'site_admin_email', 'locale_timezone'),
            },
            {
                'classes': ('wide',),
                'title': _('Cache Settings'),
                'fields': ('cache_type', 'cache_path', 'cache_host'),
            },
            {
                'classes': ('wide',),
                'title': _("Search"),
                'fields': ('search_enable', 'search_results_per_page',
                           'search_index_file'),
            },
            {
                'classes': ('wide',),
                'title': _("Third-party Integrations"),
                'fields': ('integration_gravatars',),
            },
        )


class AuthenticationSettingsForm(SiteSettingsForm):
    """Authentication settings for Review Board."""

    CUSTOM_AUTH_ID = 'custom'
    CUSTOM_AUTH_CHOICE = (CUSTOM_AUTH_ID, _('Legacy Authentication Module'))

    auth_anonymous_access = forms.BooleanField(
        label=_("Allow anonymous read-only access"),
        help_text=_("If checked, users will be able to view review requests "
                    "and diffs without logging in."),
        required=False)

    auth_backend = forms.ChoiceField(
        label=_("Authentication Method"),
        choices=(),
        help_text=_("The method Review Board should use for authenticating "
                    "users."),
        required=True)

    def __init__(self, siteconfig, *args, **kwargs):
        """Initialize the form."""
        from reviewboard.accounts.backends import get_registered_auth_backends

        super(AuthenticationSettingsForm, self).__init__(siteconfig,
                                                         *args, **kwargs)

        self.auth_backend_forms = {}

        cur_auth_backend = (self['auth_backend'].data or
                            self.fields['auth_backend'].initial)

        if cur_auth_backend == self.CUSTOM_AUTH_ID:
            custom_auth_form = LegacyAuthModuleSettingsForm(siteconfig,
                                                            *args, **kwargs)
        else:
            custom_auth_form = LegacyAuthModuleSettingsForm(siteconfig)

        self.auth_backend_forms[self.CUSTOM_AUTH_ID] = custom_auth_form

        backend_choices = []
        builtin_auth_choice = None

        for backend in get_registered_auth_backends():
            backend_id = backend.backend_id

            try:
                if backend.settings_form:
                    if cur_auth_backend == backend_id:
                        backend_form = backend.settings_form(siteconfig,
                                                             *args, **kwargs)
                    else:
                        backend_form = backend.settings_form(siteconfig)

                    self.auth_backend_forms[backend_id] = backend_form
                    backend_form.load()

                choice = (backend_id, backend.name)

                if backend_id == 'builtin':
                    builtin_auth_choice = choice
                else:
                    backend_choices.append(choice)
            except Exception as e:
                logging.error('Error loading authentication backend %s: %s'
                              % (backend_id, e),
                              exc_info=1)

        backend_choices.sort(key=lambda x: x[1])
        backend_choices.insert(0, builtin_auth_choice)
        backend_choices.append(self.CUSTOM_AUTH_CHOICE)
        self.fields['auth_backend'].choices = backend_choices

    def load(self):
        """Load the form."""
        super(AuthenticationSettingsForm, self).load()

        self.fields['auth_anonymous_access'].initial = \
            not self.siteconfig.get("auth_require_sitewide_login")

    def save(self):
        """Save the form."""
        self.siteconfig.set("auth_require_sitewide_login",
                            not self.cleaned_data['auth_anonymous_access'])

        auth_backend = self.cleaned_data['auth_backend']

        if auth_backend in self.auth_backend_forms:
            self.auth_backend_forms[auth_backend].save()

        super(AuthenticationSettingsForm, self).save()

        # Reload any important changes into the Django settings.
        load_site_config()

    def is_valid(self):
        """Check whether the form is valid."""
        valid = super(AuthenticationSettingsForm, self).is_valid()

        if valid:
            auth_backend = self.cleaned_data['auth_backend']

            if auth_backend in self.auth_backend_forms:
                valid = self.auth_backend_forms[auth_backend].is_valid()

        return valid

    def full_clean(self):
        """Clean and validate all form fields."""
        super(AuthenticationSettingsForm, self).full_clean()

        if self.data:
            # Note that this isn't validated yet, but that's okay given our
            # usage. It's a bit of a hack though.
            auth_backend = (self['auth_backend'].data or
                            self.fields['auth_backend'].initial)

            if auth_backend in self.auth_backend_forms:
                self.auth_backend_forms[auth_backend].full_clean()
        else:
            for form in six.itervalues(self.auth_backend_forms):
                form.full_clean()

    class Meta:
        title = _('Authentication Settings')
        save_blacklist = ('auth_anonymous_access',)

        fieldsets = (
            {
                'classes': ('wide',),
                'fields': ('auth_anonymous_access', 'auth_backend'),
            },
        )


class EMailSettingsForm(SiteSettingsForm):
    """E-mail settings for Review Board."""

    mail_send_review_mail = forms.BooleanField(
        label=_("Send e-mails for review requests and reviews"),
        required=False)
    mail_send_review_close_mail = forms.BooleanField(
        label=_("Send e-mails when review requests are closed"),
        required=False)
    mail_send_new_user_mail = forms.BooleanField(
        label=_("Send e-mails when new users register an account"),
        required=False)
    mail_enable_autogenerated_header = forms.BooleanField(
        label=_('Enable "Auto-Submitted: auto-generated" header'),
        help_text=_('Marks outgoing e-mails as "auto-generated" to avoid '
                    'auto-replies. Disable this if your mailing list rejects '
                    '"auto-generated" e-mails.'),
        required=False)
    mail_default_from = forms.CharField(
        label=_("Sender e-mail address"),
        help_text=_('The e-mail address that all e-mails will be sent from. '
                    'The "Sender" header will be used to make e-mails appear '
                    'to come from the user triggering the e-mail.'),
        required=False,
        widget=forms.TextInput(attrs={'size': '50'}))
    mail_host = forms.CharField(
        label=_("Mail Server"),
        required=False,
        widget=forms.TextInput(attrs={'size': '50'}))
    mail_port = forms.IntegerField(
        label=_("Port"),
        required=False,
        widget=forms.TextInput(attrs={'size': '5'}))
    mail_host_user = forms.CharField(
        label=_("Username"),
        required=False,
        widget=forms.TextInput(attrs={'size': '30', 'autocomplete': 'off'}))
    mail_host_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'size': '30', 'autocomplete': 'off'},
                                   render_value=True),
        label=_("Password"),
        required=False)
    mail_use_tls = forms.BooleanField(
        label=_("Use TLS for authentication"),
        required=False)

    send_test_mail = forms.BooleanField(
        label=_('Send a test e-mail after saving'),
        help_text=_('Send an e-mail to yourself using these server settings.'),
        required=False)

    def clean_mail_host(self):
        """Clean the mail_host field."""
        # Strip whitespaces from the SMTP address.
        return self.cleaned_data['mail_host'].strip()

    def save(self):
        """Save the form."""
        super(EMailSettingsForm, self).save()

        # Reload any important changes into the Django settings.
        load_site_config()

        if self.cleaned_data['send_test_mail']:
            site = Site.objects.get_current()
            siteconfig = SiteConfiguration.objects.get_current()

            site_url = '%s://%s' % (siteconfig.get('site_domain_method'),
                                    site.domain)

            if self.request and self.request.user.is_authenticated():
                to_user = self.request.user.email
            else:
                to_user = siteconfig.get('site_admin_email')

            send_mail(_('E-mail settings test'),
                      _('This is a test of the e-mail settings for the Review '
                        'Board server at %s.') % site_url,
                      siteconfig.get('mail_default_from'),
                      [to_user],
                      fail_silently=True)

    class Meta:
        title = _("E-Mail Settings")
        save_blacklist = ('send_test_mail',)

        fieldsets = (
            {
                'classes': ('wide',),
                'title': _('E-Mail Notification Settings'),
                'fields': ('mail_send_review_mail',
                           'mail_send_review_close_mail',
                           'mail_send_new_user_mail'),
            },
            {
                'classes': ('wide',),
                'title': _('E-Mail Delivery Settings'),
                'fields': ('mail_default_from',
                           'mail_enable_autogenerated_header'),
            },
            {
                'classes': ('wide',),
                'title': _('E-Mail Server Settings'),
                'fields': ('mail_host', 'mail_port', 'mail_host_user',
                           'mail_host_password', 'mail_use_tls',
                           'send_test_mail'),
            },
        )


class DiffSettingsForm(SiteSettingsForm):
    """Diff settings for Review Board."""

    diffviewer_syntax_highlighting = forms.BooleanField(
        label=_("Show syntax highlighting"),
        required=False)

    diffviewer_syntax_highlighting_threshold = forms.IntegerField(
        label=_("Syntax highlighting threshold"),
        help_text=_("Files with lines greater than this number will not have "
                    "syntax highlighting.  Enter 0 for no limit."),
        required=False,
        widget=forms.TextInput(attrs={'size': '5'}))

    diffviewer_show_trailing_whitespace = forms.BooleanField(
        label=_("Show trailing whitespace"),
        help_text=_("Show excess trailing whitespace as red blocks. This "
                    "helps to visualize when a text editor added unwanted "
                    "whitespace to the end of a line."),
        required=False)

    include_space_patterns = forms.CharField(
        label=_("Show all whitespace for"),
        required=False,
        help_text=_("A comma-separated list of file patterns for which all "
                    "whitespace changes should be shown. "
                    "(e.g., \"*.py, *.txt\")"),
        widget=forms.TextInput(attrs={'size': '60'}))

    diffviewer_context_num_lines = forms.IntegerField(
        label=_("Lines of Context"),
        help_text=_("The number of unchanged lines shown above and below "
                    "changed lines."),
        initial=5,
        widget=forms.TextInput(attrs={'size': '5'}))

    diffviewer_paginate_by = forms.IntegerField(
        label=_("Paginate by"),
        help_text=_("The number of files to display per page in the diff "
                    "viewer."),
        initial=20,
        widget=forms.TextInput(attrs={'size': '5'}))

    diffviewer_paginate_orphans = forms.IntegerField(
        label=_("Paginate orphans"),
        help_text=_("The number of extra files required before adding another "
                    "page to the diff viewer."),
        initial=10,
        widget=forms.TextInput(attrs={'size': '5'}))

    diffviewer_max_diff_size = forms.IntegerField(
        label=_('Max diff size (bytes)'),
        help_text=_('The maximum size (in bytes) for any given diff. Enter 0 '
                    'to disable size restrictions.'),
        widget=forms.TextInput(attrs={'size': '15'}))

    def load(self):
        """Load the form."""
        super(DiffSettingsForm, self).load()
        self.fields['include_space_patterns'].initial = \
            ', '.join(self.siteconfig.get('diffviewer_include_space_patterns'))

    def save(self):
        """Save the form."""
        self.siteconfig.set(
            'diffviewer_include_space_patterns',
            re.split(r",\s*", self.cleaned_data['include_space_patterns']))

        super(DiffSettingsForm, self).save()

    class Meta:
        title = _("Diff Viewer Settings")
        save_blacklist = ('include_space_patterns',)
        fieldsets = (
            {
                'classes': ('wide',),
                'fields': ('diffviewer_syntax_highlighting',
                           'diffviewer_syntax_highlighting_threshold',
                           'diffviewer_show_trailing_whitespace',
                           'include_space_patterns'),
            },
            {
                'title': _("Advanced"),
                'description': _(
                    "These are advanced settings that control the behavior "
                    "and display of the diff viewer. In general, these "
                    "settings do not need to be changed."
                ),
                'classes': ('wide',),
                'fields': ('diffviewer_max_diff_size',
                           'diffviewer_context_num_lines',
                           'diffviewer_paginate_by',
                           'diffviewer_paginate_orphans')
            }
        )


class LoggingSettingsForm(SiteSettingsForm):
    """Logging settings for Review Board."""

    LOG_LEVELS = (
        ('DEBUG', _('Debug')),
        ('INFO', _('Info')),
        ('WARNING', _('Warning')),
        ('ERROR', _('Error')),
        ('CRITICAL', _('Critical')),
    )

    logging_enabled = forms.BooleanField(
        label=_("Enable logging"),
        help_text=_("Enables logging of Review Board operations. This is in "
                    "addition to your web server's logging and does not log "
                    "all page visits."),
        required=False)

    logging_directory = forms.CharField(
        label=_("Log directory"),
        help_text=_("The directory where log files will be stored. This must "
                    "be writable by the web server."),
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}))

    logging_level = forms.ChoiceField(
        label=_("Log level"),
        help_text=_("Indicates the logging threshold. Please note that this "
                    "may increase the size of the log files if a low "
                    "threshold is selected."),
        required=False,
        choices=LOG_LEVELS)

    logging_allow_profiling = forms.BooleanField(
        label=_("Allow code profiling"),
        help_text=_("Logs the time spent on certain operations. This is "
                    "useful for debugging but may greatly increase the "
                    "size of log files."),
        required=False)

    def clean_logging_directory(self):
        """Validate that the logging_directory path is valid.

        This checks that the directory path exists, and is writable by the web
        server.
        """
        logging_dir = self.cleaned_data['logging_directory']

        if not os.path.exists(logging_dir):
            raise ValidationError(_("This path does not exist."))

        if not os.path.isdir(logging_dir):
            raise ValidationError(_("This is not a directory."))

        if not os.access(logging_dir, os.W_OK):
            raise ValidationError(
                _("This path is not writable by the web server."))

        return logging_dir

    def save(self):
        """Save the form."""
        super(LoggingSettingsForm, self).save()

        # Reload any important changes into the Django settings.
        load_site_config()

    class Meta:
        title = _("Logging Settings")
        fieldsets = (
            {
                'classes': ('wide',),
                'fields': ('logging_enabled',
                           'logging_directory',
                           'logging_level'),
            },
            {
                'title': _('Advanced'),
                'classes': ('wide',),
                'fields': ('logging_allow_profiling',),
            }
        )


class SSHSettingsForm(forms.Form):
    """SSH key settings for Review Board."""

    generate_key = forms.BooleanField(required=False,
                                      initial=True,
                                      widget=forms.HiddenInput)
    keyfile = forms.FileField(label=_('Key file'),
                              required=False,
                              widget=forms.FileInput(attrs={'size': '35'}))
    delete_key = forms.BooleanField(required=False,
                                    initial=True,
                                    widget=forms.HiddenInput)

    def create(self, files):
        """Generate or import an SSH key."""
        if self.cleaned_data['generate_key']:
            try:
                SSHClient().generate_user_key()
            except IOError as e:
                self.errors['generate_key'] = forms.util.ErrorList([
                    _('Unable to write SSH key file: %s') % e
                ])
                raise
            except Exception as e:
                self.errors['generate_key'] = forms.util.ErrorList([
                    _('Error generating SSH key: %s') % e
                ])
                raise
        elif self.cleaned_data['keyfile']:
            try:
                SSHClient().import_user_key(files['keyfile'])
            except IOError as e:
                self.errors['keyfile'] = forms.util.ErrorList([
                    _('Unable to write SSH key file: %s') % e
                ])
                raise
            except Exception as e:
                self.errors['keyfile'] = forms.util.ErrorList([
                    _('Error uploading SSH key: %s') % e
                ])
                raise

    def did_request_delete(self):
        """Return whether the user has requested to delete the user SSH key."""
        return 'delete_key' in self.cleaned_data

    def delete(self):
        """Try to delete the user SSH key upon request."""
        if self.cleaned_data['delete_key']:
            try:
                SSHClient().delete_user_key()
            except Exception as e:
                self.errors['delete_key'] = forms.util.ErrorList([
                    _('Unable to delete SSH key file: %s') % e
                ])
                raise

    class Meta:
        title = _('SSH Settings')


class StorageSettingsForm(SiteSettingsForm):
    """File storage backend settings for Review Board."""

    storage_backend = forms.ChoiceField(
        label=_('File storage method'),
        choices=(
            ('filesystem', _('Host file system')),
            ('s3', _('Amazon S3')),
            ('swift', _('OpenStack Swift')),
            # TODO: I haven't tested CouchDB at all, so it's turned off
            # ('couchdb', _('CouchDB')),
        ),
        help_text=_('Storage method and location for uploaded files, such as '
                    'screenshots and file attachments.'),
        required=True)

    aws_access_key_id = forms.CharField(
        label=_('Amazon AWS access key'),
        help_text=_('Your Amazon AWS access key ID. This can be found in '
                    'the "Security Credentials" section of the AWS site.'),
        required=True,
        widget=forms.TextInput(attrs={'size': '40'}))

    aws_secret_access_key = forms.CharField(
        label=_('Amazon AWS secret access key'),
        help_text=_('Your Amazon AWS secret access ID. This can be found in '
                    'the "Security Credentials" section of the AWS site.'),
        required=True,
        widget=forms.TextInput(attrs={'size': '40'}))

    aws_s3_bucket_name = forms.CharField(
        label=_('S3 bucket name'),
        help_text=_('Bucket name inside Amazon S3.'),
        required=True,
        widget=forms.TextInput(attrs={'size': '40'}))

    aws_calling_format = forms.ChoiceField(
        label=_('Amazon AWS calling format'),
        choices=(
            (1, 'Path'),
            (2, 'Subdomain'),
            (3, 'Vanity'),
        ),
        help_text=_('Calling format for AWS requests.'),
        required=True)

    # TODO: these items are consumed in the S3Storage backend, but I'm not
    # totally sure what they mean, or how to let users set them via siteconfig
    # (especially AWS_HEADERS, which is a dictionary). For now, defaults will
    # suffice.
    #
    # 'aws_headers':            'AWS_HEADERS',
    # 'aws_default_acl':        'AWS_DEFAULT_ACL',
    # 'aws_querystring_active': 'AWS_QUERYSTRING_ACTIVE',
    # 'aws_querystring_expire': 'AWS_QUERYSTRING_EXPIRE',
    # 'aws_s3_secure_urls':     'AWS_S3_SECURE_URLS',

    swift_auth_url = forms.CharField(
        label=_('Swift auth URL'),
        help_text=_('The URL for the auth server, '
                    'e.g. http://127.0.0.1:5000/v2.0'),
        required=True,
        widget=forms.TextInput(attrs={'size': '40'}))

    swift_username = forms.CharField(
        label=_('Swift username'),
        help_text=_('The username to use to authenticate, '
                    'e.g. system:root'),
        required=True,
        widget=forms.TextInput(attrs={'size': '40'}))

    swift_key = forms.CharField(
        label=_('Swift key'),
        help_text=_('The key (password) to use to authenticate.'),
        required=True,
        widget=forms.TextInput(attrs={'size': '40'}))

    swift_auth_version = forms.ChoiceField(
        label=_('Swift auth version'),
        choices=(
            ('1', _('1.0')),
            ('2', _('2.0')),
        ),
        help_text=_('The version of the authentication protocol to use.'),
        required=True)

    swift_container_name = forms.CharField(
        label=_('Swift container name'),
        help_text=_('The container in which to store the files. '
                    'This container must be publicly readable.'),
        required=True,
        widget=forms.TextInput(attrs={'size': '40'}))

    couchdb_default_server = forms.CharField(
        label=_('Default server'),
        help_text=_('For example, "http://couchdb.local:5984"'),
        required=True)

    # TODO: this is consumed in the CouchDBStorage backend, but I'm not sure
    # how to let users set it via siteconfig, since it's a dictionary. Since I
    # haven't tested the CouchDB backend at all, it'll just sit here for now.
    #
    # 'couchdb_storage_options': 'COUCHDB_STORAGE_OPTIONS',

    def load(self):
        """Load the form."""
        can_use_amazon_s3, reason = get_can_use_amazon_s3()
        if not can_use_amazon_s3:
            self.disabled_fields['aws_access_key_id'] = True
            self.disabled_fields['aws_secret_access_key'] = True
            self.disabled_fields['aws_s3_bucket_name'] = True
            self.disabled_fields['aws_calling_format'] = True
            self.disabled_reasons['aws_access_key_id'] = reason

        can_use_openstack_swift, reason = get_can_use_openstack_swift()
        if not can_use_openstack_swift:
            self.disabled_fields['swift_auth_url'] = True
            self.disabled_fields['swift_username'] = True
            self.disabled_fields['swift_key'] = True
            self.disabled_fields['swift_auth_version'] = True
            self.disabled_fields['swift_container_name'] = True
            self.disabled_reasons['swift_auth_url'] = reason

        can_use_couchdb, reason = get_can_use_couchdb()
        if not can_use_couchdb:
            self.disabled_fields['couchdb_default_server'] = True
            self.disabled_reasons['couchdb_default_server'] = reason

        super(StorageSettingsForm, self).load()

    def save(self):
        """Save the form."""
        super(StorageSettingsForm, self).save()
        load_site_config()

    def full_clean(self):
        """Clean and validate all form fields."""
        def set_fieldset_required(fieldset_id, required):
            for fieldset in self.Meta.fieldsets:
                if 'id' in fieldset and fieldset['id'] == fieldset_id:
                    for field in fieldset['fields']:
                        self.fields[field].required = required

        if self.data:
            # Note that this isn't validated yet, but that's okay given our
            # usage. It's a bit of a hack though.
            storage_backend = (self['storage_backend'].data or
                               self.fields['storage_backend'].initial)

            if storage_backend != 's3':
                set_fieldset_required('storage_s3', False)

            if storage_backend != 'swift':
                set_fieldset_required('storage_swift', False)

            if storage_backend != 'couchdb':
                set_fieldset_required('storage_couchdb', False)

        super(StorageSettingsForm, self).full_clean()

    class Meta:
        title = _('File Storage Settings')

        fieldsets = (
            {
                'classes': ('wide',),
                'fields': ('storage_backend',),
            },
            {
                'id': 'storage_s3',
                'classes': ('wide', 'hidden'),
                'title': _('Amazon S3 Settings'),
                'fields': ('aws_access_key_id',
                           'aws_secret_access_key',
                           'aws_s3_bucket_name',
                           'aws_calling_format'),
            },
            {
                'id': 'storage_swift',
                'classes': ('wide', 'hidden'),
                'title': _('OpenStack Swift Settings'),
                'fields': ('swift_auth_url',
                           'swift_username',
                           'swift_key',
                           'swift_auth_version',
                           'swift_container_name'),
            },
            {
                'id': 'storage_couchdb',
                'classes': ('wide', 'hidden'),
                'title': _('CouchDB Settings'),
                'fields': ('couchdb_default_server',),
            },
        )


class SupportSettingsForm(SiteSettingsForm):
    """Support settings for Review Board."""

    install_key = forms.CharField(
        label=_('Install key'),
        help_text=_('The installation key to provide when purchasing a '
                    'support contract.'),
        required=False,
        widget=forms.TextInput(attrs={
            'size': '80',
            'readonly': 'readonly'
        }))

    support_url = forms.CharField(
        label=_('Custom Support URL'),
        help_text=_("The location of your organization's own Review Board "
                    "support page. Leave blank to use the default support "
                    "page."),
        required=False,
        widget=forms.TextInput(attrs={'size': '80'}))

    send_support_usage_stats = forms.BooleanField(
        label=_('Send support-related usage statistics'),
        help_text=_('Basic usage information will be sent to us at times to '
                    'help with some support issues and to provide a more '
                    'personalized support page for your users. '
                    '<i>No information is ever given to a third party.</i>'),
        required=False)

    def load(self):
        """Load the form."""
        super(SupportSettingsForm, self).load()
        self.fields['install_key'].initial = get_install_key()

    class Meta:
        title = _('Support Settings')
        save_blacklist = ('install_key',)
        fieldsets = ({
            'classes': ('wide',),
            'description': (
                '<p>For fast one-on-one support, plus other benefits, '
                'purchase a <a href="'
                'http://www.beanbaginc.com/support/contracts/">'
                'support contract</a>.</p>'
                '<p>You can also customize where your users will go for '
                'support by changing the Custom Support URL below. If left '
                'blank, they will be taken to our support channel.</p>'),
            'fields': ('install_key', 'support_url',
                       'send_support_usage_stats'),
        },)
