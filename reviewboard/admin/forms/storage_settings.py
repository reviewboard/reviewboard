"""Administration form for file attachment storage settings."""

from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _
from djblets.siteconfig.forms import SiteSettingsForm

from reviewboard.admin.checks import (get_can_use_amazon_s3,
                                      get_can_use_openstack_swift,
                                      get_can_use_couchdb)
from reviewboard.admin.siteconfig import load_site_config


class S3StorageSettingsForm(SiteSettingsForm):
    """Settings subform for S3-based file storage."""

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

    def __init__(self, *args, **kwargs):
        """Initialize the subform.

        If Amazon S3 support isn't available, the form's fields will be
        disabled.

        Args:
            *args (tuple):
                Additional positional arguments for the parent class.

            **kwargs (dict):
                Additional keyword arguments for the parent class.
        """
        super(S3StorageSettingsForm, self).__init__(*args, **kwargs)

        can_use_amazon_s3, reason = get_can_use_amazon_s3()

        if not can_use_amazon_s3:
            self.disabled_fields['aws_access_key_id'] = True
            self.disabled_fields['aws_secret_access_key'] = True
            self.disabled_fields['aws_s3_bucket_name'] = True
            self.disabled_fields['aws_calling_format'] = True
            self.disabled_reasons['aws_access_key_id'] = reason

    class Meta:
        title = _('Amazon S3 Settings')
        fieldsets = (
            (None, {
                'classes': ('wide', 'hidden'),
                'fields': ('aws_access_key_id',
                           'aws_secret_access_key',
                           'aws_s3_bucket_name',
                           'aws_calling_format'),
            }),
         )


class CouchDBStorageSettingsForm(SiteSettingsForm):
    """Settings subform for CouchDB-based file storage.

    Note that this is currently unused. It's here for legacy reasons and
    future support.
    """

    couchdb_default_server = forms.CharField(
        label=_('Default server'),
        help_text=_('For example, "http://couchdb.local:5984"'),
        required=True)

    # TODO: this is consumed in the CouchDBStorage backend, but I'm not sure
    # how to let users set it via siteconfig, since it's a dictionary. Since I
    # haven't tested the CouchDB backend at all, it'll just sit here for now.
    #
    # 'couchdb_storage_options': 'COUCHDB_STORAGE_OPTIONS',

    def __init__(self, *args, **kwargs):
        """Initialize the subform.

        If CouchDB support isn't available, the form's fields will be
        disabled.

        Args:
            *args (tuple):
                Additional positional arguments for the parent class.

            **kwargs (dict):
                Additional keyword arguments for the parent class.
        """
        super(CouchDBStorageSettingsForm, self).__init__(*args, **kwargs)

        can_use_couchdb, reason = get_can_use_couchdb()

        if not can_use_couchdb:
            self.disabled_fields['couchdb_default_server'] = True
            self.disabled_reasons['couchdb_default_server'] = reason

    class Meta:
        title = _('CouchDB Settings')
        fieldsets = (
            (None, {
                'classes': ('wide', 'hidden'),
                'fields': ('couchdb_default_server',),
            }),
        )


class SwiftStorageSettingsForm(SiteSettingsForm):
    """Settings subform for OpenStack Swift-based file storage."""

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

    def __init__(self, *args, **kwargs):
        """Initialize the subform.

        If OpenStack Swift support isn't available, the form's fields will be
        disabled.

        Args:
            *args (tuple):
                Additional positional arguments for the parent class.

            **kwargs (dict):
                Additional keyword arguments for the parent class.
        """
        super(SwiftStorageSettingsForm, self).__init__(*args, **kwargs)

        can_use_openstack_swift, reason = get_can_use_openstack_swift()

        if not can_use_openstack_swift:
            self.disabled_fields['swift_auth_url'] = True
            self.disabled_fields['swift_username'] = True
            self.disabled_fields['swift_key'] = True
            self.disabled_fields['swift_auth_version'] = True
            self.disabled_fields['swift_container_name'] = True
            self.disabled_reasons['swift_auth_url'] = reason

    class Meta:
        title = _('OpenStack Swift Settings')
        fieldsets = (
            (None, {
                'classes': ('wide', 'hidden'),
                'fields': ('swift_auth_url',
                           'swift_username',
                           'swift_key',
                           'swift_auth_version',
                           'swift_container_name'),
            }),
        )


class StorageSettingsForm(SiteSettingsForm):
    """File storage backend settings for Review Board."""

    storage_backend_id = forms.ChoiceField(
        label=_('File storage method'),
        choices=(
            ('filesystem', _('Host file system')),
            ('s3', _('Amazon S3')),
            ('swift', _('OpenStack Swift')),
        ),
        help_text=_('Storage method and location for uploaded files, such as '
                    'screenshots and file attachments.'),
        required=True,
        widget=forms.Select(attrs={
            'data-subform-group': 'storage-backend',
        }))

    def __init__(self, *args, **kwargs):
        """Initialize the storage settings form.

        This will set up the list of available storage backend settings forms,
        allowing the browser to show the appropriate settings form based on the
        selected backend.

        Args:
            *args (tuple):
                Additional positional arguments for the parent class.

            **kwargs (dict):
                Additional keyword arguments for the parent class.
        """
        super(StorageSettingsForm, self).__init__(*args, **kwargs)

        self.storage_backend_forms = {
            's3': S3StorageSettingsForm(*args, **kwargs),
            'swift': SwiftStorageSettingsForm(*args, **kwargs),
        }

    def is_valid(self):
        """Return whether the form is valid.

        This will check the validity of the fields on this form and on the
        selected storage backend's settings form.

        Returns:
            bool:
            ``True`` if the main settings form and storage backend's settings
            form is valid. ``False`` if either form is invalid.
        """
        if not super(StorageSettingsForm, self).is_valid():
            return False

        backend_id = self.cleaned_data['storage_backend_id']
        backend_form = self.storage_backend_forms.get(backend_id)

        return backend_form is None or backend_form.is_valid()

    def save(self):
        """Save the form.

        This will write the new configuration to the database. It will then
        force a site configuration reload.
        """
        super(StorageSettingsForm, self).save()

        backend_id = self.cleaned_data['storage_backend_id']

        if backend_id in self.storage_backend_forms:
            backend_form = self.storage_backend_forms[backend_id]
            backend_form.save()

        load_site_config()

    class Meta:
        title = _('File Storage Settings')
        subforms = (
            {
                'subforms_attr': 'storage_backend_forms',
                'controller_field': 'storage_backend_id',
            },
        )
