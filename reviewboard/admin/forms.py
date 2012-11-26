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


import logging
import os
import re
import urlparse

from django import forms
from django.contrib.sites.models import Site
from django.core.cache import parse_backend_uri, InvalidCacheBackendError
from django.utils.translation import ugettext as _
from djblets.log import restart_logging
from djblets.siteconfig.forms import SiteSettingsForm
from djblets.util.forms import TimeZoneField

from reviewboard.accounts.forms import LegacyAuthModuleSettingsForm
from reviewboard.admin.checks import get_can_enable_search, \
                                     get_can_enable_syntax_highlighting, \
                                     get_can_use_amazon_s3, \
                                     get_can_use_couchdb
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.ssh.client import SSHClient


class GeneralSettingsForm(SiteSettingsForm):
    """General settings for Review Board."""
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

    search_index_file = forms.CharField(
        label=_("Search index directory"),
        help_text=_("The directory that search index data should be stored "
                    "in."),
        required=False,
        widget=forms.TextInput(attrs={'size': '50'}))

    cache_backend = forms.CharField(
        label=_("Cache Backend"),
        help_text=_("The path to the cache backend."
                    "Example: 'memcached://127.0.0.1:11211/'"),
        required=False,
        widget=forms.TextInput(attrs={'size': '50'}))

    def load(self):
        domain_method = self.siteconfig.get("site_domain_method")
        site = Site.objects.get_current()

        can_enable_search, reason = get_can_enable_search()
        if not can_enable_search:
            self.disabled_fields['search_enable'] = True
            self.disabled_fields['search_index_file'] = True
            self.disabled_reasons['search_enable'] = reason

        super(GeneralSettingsForm, self).load()

        # This must come after we've loaded the general settings.
        self.fields['server'].initial = "%s://%s" % (domain_method,
                                                     site.domain)

    def save(self):
        server = self.cleaned_data['server']

        if "://" not in server:
            # urlparse doesn't properly handle URLs without a scheme. It
            # believes the domain is actually the path. So we apply a prefix.
            server = "http://" + server

        url_parts = urlparse.urlparse(server)
        domain_method = url_parts[0]
        domain_name = url_parts[1]

        if domain_name.endswith("/"):
            domain_name = domain_name[:-1]

        site = Site.objects.get_current()
        site.domain = domain_name
        site.save()

        self.siteconfig.set("site_domain_method", domain_method)

        super(GeneralSettingsForm, self).save()

        # Reload any important changes into the Django settings.
        load_site_config()

    def clean_cache_backend(self):
        """Validates that the specified cache backend is parseable by Django."""
        backend = self.cleaned_data['cache_backend'].strip()
        if backend:
            try:
                parse_backend_uri(backend)
            except InvalidCacheBackendError, e:
                raise forms.ValidationError(e)

        return backend

    def clean_search_index_file(self):
        """Validates that the specified index file is valid."""
        index_file = self.cleaned_data['search_index_file'].strip()

        if index_file:
            if not os.path.isabs(index_file):
                raise forms.ValidationError(
                    _("The search index path must be absolute."))

            if (os.path.exists(index_file) and
                not os.access(index_file, os.W_OK)):
                raise forms.ValidationError(
                    _('The search index path is not writable. Make sure the '
                      'web server has write access to it and its parent '
                      'directory.'))

        return index_file


    class Meta:
        title = _("General Settings")
        save_blacklist = ('server',)

        fieldsets = (
            {
                'classes': ('wide',),
                'title':   _("Site Settings"),
                'fields':  ('server', 'site_media_url',
                            'site_admin_name',
                            'site_admin_email',
                            'locale_timezone',
                            'cache_backend'),
            },
            {
                'classes': ('wide',),
                'title':   _("Search"),
                'fields':  ('search_enable', 'search_index_file'),
            },
        )


class AuthenticationSettingsForm(SiteSettingsForm):
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

        for backend_id, backend in get_registered_auth_backends():
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
            except Exception, e:
                logging.error('Error loading authentication backend %s: %s'
                              % (backend_id, e),
                              exc_info=1)

        backend_choices.sort(key=lambda x: x[1])
        backend_choices.insert(0, builtin_auth_choice)
        backend_choices.append(self.CUSTOM_AUTH_CHOICE)
        self.fields['auth_backend'].choices = backend_choices

    def load(self):
        self.fields['auth_anonymous_access'].initial = \
            not self.siteconfig.get("auth_require_sitewide_login")

        super(AuthenticationSettingsForm, self).load()

    def save(self):
        self.siteconfig.set("auth_require_sitewide_login",
                            not self.cleaned_data['auth_anonymous_access'])

        auth_backend = self.cleaned_data['auth_backend']

        if auth_backend in self.auth_backend_forms:
            self.auth_backend_forms[auth_backend].save()

        super(AuthenticationSettingsForm, self).save()

        # Reload any important changes into the Django settings.
        load_site_config()

    def is_valid(self):
        valid = super(AuthenticationSettingsForm, self).is_valid()

        if valid:
            auth_backend = self.cleaned_data['auth_backend']

            if auth_backend in self.auth_backend_forms:
                valid = self.auth_backend_forms[auth_backend].is_valid()

        return valid

    def full_clean(self):
        super(AuthenticationSettingsForm, self).full_clean()

        if self.data:
            # Note that this isn't validated yet, but that's okay given our
            # usage. It's a bit of a hack though.
            auth_backend = self['auth_backend'].data or \
                           self.fields['auth_backend'].initial

            if auth_backend in self.auth_backend_forms:
                self.auth_backend_forms[auth_backend].full_clean()
        else:
            for form in self.auth_backend_forms.values():
                form.full_clean()

    class Meta:
        title = _('Authentication Settings')
        save_blacklist = ('auth_anonymous_access',)

        fieldsets = (
            {
                'classes': ('wide',),
                'title':   _('General'),
                'fields':  ('auth_anonymous_access',
                            'auth_backend'),
            },
        )


class EMailSettingsForm(SiteSettingsForm):
    """
    E-mail settings for Review Board.
    """
    mail_send_review_mail = forms.BooleanField(
        label=_("Send e-mails for review requests and reviews"),
        required=False)
    mail_send_shipit_mail = forms.BooleanField(
        label=_("Send e-mails for ship-its"),
        required=False)
    mail_send_new_user_mail = forms.BooleanField(
        label=_("Send e-mails when new users register an account"),
        required=False)
    mail_default_from = forms.CharField(
        label=_("Sender e-mail address"),
        help_text=_('The e-mail address that all e-mails will be sent from. '
                    'The "Sender" header will be used to make e-mails appear '
                    'to come from the user triggering the e-mail.'),
        required=False)
    mail_host = forms.CharField(
        label=_("Mail Server"),
        required=False)
    mail_port = forms.IntegerField(
        label=_("Port"),
        required=False)
    mail_host_user = forms.CharField(
        label=_("Username"),
        required=False)
    mail_host_password = forms.CharField(
        widget=forms.PasswordInput,
        label=_("Password"),
        required=False)
    mail_use_tls = forms.BooleanField(
        label=_("Use TLS for authentication"),
        required=False)

    def save(self):
        super(EMailSettingsForm, self).save()

        # Reload any important changes into the Django settings.
        load_site_config()


    class Meta:
        title = _("E-Mail Settings")


class DiffSettingsForm(SiteSettingsForm):
    """Diff settings for Review Board."""
    diffviewer_syntax_highlighting = forms.BooleanField(
        label=_("Show syntax highlighting"),
        required=False)

    diffviewer_syntax_highlighting_threshold = forms.IntegerField(
        label=_("Syntax highlighting threshold"),
        help_text=_("Files with lines greater than this number will not have "
                    "syntax highlighting.  Enter 0 for no limit."),
        required=False)

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
                    "(e.g., \"*.py, *.txt\")"))

    diffviewer_context_num_lines = forms.IntegerField(
        label=_("Lines of Context"),
        help_text=_("The number of unchanged lines shown above and below "
                    "changed lines."),
        initial=5)

    diffviewer_paginate_by = forms.IntegerField(
        label=_("Paginate by"),
        help_text=_("The number of files to display per page in the diff "
                    "viewer."),
        initial=20)

    diffviewer_paginate_orphans = forms.IntegerField(
        label=_("Paginate orphans"),
        help_text=_("The number of extra files required before adding another "
                    "page to the diff viewer."),
        initial=10)

    diffviewer_max_diff_size = forms.IntegerField(
        label=_('Max diff size'),
        help_text=_('The maximum size (in bytes) for any given diff. Enter 0 '
                    'to disable size restrictions.'))

    def load(self):
        # TODO: Move this check into a dependencies module so we can catch it
        #       when the user starts up Review Board.
        can_syntax_highlight, reason = get_can_enable_syntax_highlighting()

        if not can_syntax_highlight:
            self.disabled_fields['diffviewer_syntax_highlighting'] = True
            self.disabled_reasons['diffviewer_syntax_highlighting'] = _(reason)
            self.disabled_fields['diffviewer_syntax_highlighting_threshold'] = True
            self.disabled_reasons['diffviewer_syntax_highlighting_threshold'] = _(reason)

        self.fields['include_space_patterns'].initial = \
            ', '.join(self.siteconfig.get('diffviewer_include_space_patterns'))

        super(DiffSettingsForm, self).load()

    def save(self):
        self.siteconfig.set('diffviewer_include_space_patterns',
            re.split(r",\s*", self.cleaned_data['include_space_patterns']))

        super(DiffSettingsForm, self).save()


    class Meta:
        title = _("Diff Viewer Settings")
        save_blacklist = ('include_space_patterns',)
        fieldsets = (
            {
                'title': _("General"),
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
        required=False)

    logging_allow_profiling = forms.BooleanField(
        label=_("Allow code profiling"),
        help_text=_("Logs the time spent on certain operations. This is "
                    "useful for debugging but may greatly increase the "
                    "size of log files."),
        required=False)

    def clean_logging_directory(self):
        """Validates that the logging_directory path is valid."""
        logging_dir = self.cleaned_data['logging_directory']

        if not os.path.exists(logging_dir):
            raise forms.ValidationError(_("This path does not exist."))

        if not os.path.isdir(logging_dir):
            raise forms.ValidationError(_("This is not a directory."))

        if not os.access(logging_dir, os.W_OK):
            raise forms.ValidationError(
                _("This path is not writable by the web server."))

        return logging_dir

    def save(self):
        super(LoggingSettingsForm, self).save()

        # Reload any important changes into the Django settings.
        load_site_config()
        restart_logging()


    class Meta:
        title = _("Logging Settings")
        fieldsets = (
            {
                'title':   _('General'),
                'classes': ('wide',),
                'fields':  ('logging_enabled',
                            'logging_directory'),
            },
            {
                'title':   _('Advanced'),
                'classes': ('wide',),
                'fields':  ('logging_allow_profiling',),
            }
        )


class SSHSettingsForm(forms.Form):
    generate_key = forms.BooleanField(required=False,
                                      initial=True,
                                      widget=forms.HiddenInput)
    keyfile = forms.FileField(label=_('Key file'),
                              required=False,
                              widget=forms.FileInput(attrs={'size': '35'}))

    def create(self, files):
        if self.cleaned_data['generate_key']:
            try:
                SSHClient().generate_user_key()
            except IOError, e:
                self.errors['generate_key'] = forms.util.ErrorList([
                    _('Unable to write SSH key file: %s') % e
                ])
                raise
            except Exception, e:
                self.errors['generate_key'] = forms.util.ErrorList([
                    _('Error generating SSH key: %s') % e
                ])
                raise
        elif self.cleaned_data['keyfile']:
            try:
                SSHClient().import_user_key(files['keyfile'])
            except IOError, e:
                self.errors['keyfile'] = forms.util.ErrorList([
                    _('Unable to write SSH key file: %s') % e
                ])
                raise
            except Exception, e:
                self.errors['keyfile'] = forms.util.ErrorList([
                    _('Error uploading SSH key: %s') % e
                ])
                raise


class StorageSettingsForm(SiteSettingsForm):
    """File storage backend settings for Review Board."""

    storage_backend = forms.ChoiceField(
        label=_('File storage method'),
        choices=(
            ('filesystem', _('Host file system')),
            ('s3',         _('Amazon S3')),
            # TODO: I haven't tested CouchDB at all, so it's turned off
            #('couchdb',    _('CouchDB')),
        ),
        help_text=_('Storage method and location for uploaded files, such as '
                    'screenshots and file attachments.'),
        required=True)

    aws_access_key_id = forms.CharField(
        label=_('Amazon AWS access key'),
        help_text=_('Your Amazon AWS access key ID. This can be found in '
                    'the "Security Credentials" section of the AWS site.'),
        required=True)

    aws_secret_access_key = forms.CharField(
        label=_('Amazon AWS secret access key'),
        help_text=_('Your Amazon AWS secret access ID. This can be found in '
                    'the "Security Credentials" section of the AWS site.'),
        required=True)

    aws_s3_bucket_name = forms.CharField(
        label=_('S3 bucket name'),
        help_text=_('Bucket name inside Amazon S3.'),
        required=True)

    aws_calling_format = forms.ChoiceField(
        label=_('Amazon AWS calling format'),
        choices=(
            (1, 'Path'),
            (2, 'Subdomain'),
            (3, 'Vanity'),
        ),
        help_text=_('Calling format for AWS requests.'), # FIXME: what do these mean?
        required=True)

    # TODO: these items are consumed in the S3Storage backend, but I'm not
    # totally sure what they mean, or how to let users set them via siteconfig
    # (especially AWS_HEADERS, which is a dictionary). For now, defaults will
    # suffice.
    #
    #'aws_headers':            'AWS_HEADERS',
    #'aws_default_acl':        'AWS_DEFAULT_ACL',
    #'aws_querystring_active': 'AWS_QUERYSTRING_ACTIVE',
    #'aws_querystring_expire': 'AWS_QUERYSTRING_EXPIRE',
    #'aws_s3_secure_urls':     'AWS_S3_SECURE_URLS',

    couchdb_default_server = forms.CharField(
        label=_('Default server'),
        help_text=_('For example, "http://couchdb.local:5984"'),
        required=True)

    # TODO: this is consumed in the CouchDBStorage backend, but I'm not sure how
    # to let users set it via siteconfig, since it's a dictionary. Since I
    # haven't tested the CouchDB backend at all, it'll just sit here for now.
    #
    #'couchdb_storage_options': 'COUCHDB_STORAGE_OPTIONS',

    def load(self):
        can_use_amazon_s3, reason = get_can_use_amazon_s3()
        if not can_use_amazon_s3:
            self.disabled_fields['aws_access_key_id'] = True
            self.disabled_fields['aws_secret_access_key'] = True
            self.disabled_fields['aws_s3_bucket_name'] = True
            self.disabled_fields['aws_calling_format'] = True
            self.disabled_reasons['aws_access_key_id'] = reason

        can_use_couchdb, reason = get_can_use_couchdb()
        if not can_use_couchdb:
            self.disabled_fields['couchdb_default_server'] = True
            self.disabled_reasons['couchdb_default_server'] = reason

        super(StorageSettingsForm, self).load()

    def save(self):
        super(StorageSettingsForm, self).save()
        load_site_config()

    def full_clean(self):
        def set_fieldset_required(fieldset_id, required):
            for fieldset in self.Meta.fieldsets:
                if 'id' in fieldset and fieldset['id'] == fieldset_id:
                    for field in fieldset['fields']:
                        self.fields[field].required = required

        if self.data:
            # Note that this isn't validated yet, but that's okay given our
            # usage. It's a bit of a hack though.
            storage_backend = self['storage_backend'].data or \
                              self.fields['storage_backend'].initial

            if storage_backend != 's3':
                set_fieldset_required('storage_s3', False)

            if storage_backend != 'couchdb':
                set_fieldset_required('storage_couchdb', False)

        super(StorageSettingsForm, self).full_clean()

    class Meta:
        title = _('File Storage Settings')

        fieldsets = (
            {
                'classes': ('wide',),
                'title':   _('File Storage Settings'),
                'fields':  ('storage_backend',),
            },
            {
                'id':      'storage_s3',
                'classes': ('wide', 'hidden'),
                'title':   _('Amazon S3 Settings'),
                'fields':  ('aws_access_key_id',
                            'aws_secret_access_key',
                            'aws_s3_bucket_name',
                            'aws_calling_format'),
            },
            {
                'id':      'storage_couchdb',
                'classes': ('wide' 'hidden'),
                'title':   _('CouchDB Settings'),
                'fields':  ('couchdb_default_server',),
            },
        )
