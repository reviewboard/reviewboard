from __future__ import unicode_literals

import logging

from django import forms
from django.utils import six
from django.utils.translation import ugettext_lazy as _, ugettext

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            TwoFactorAuthCodeRequiredError)
from reviewboard.hostingsvcs.models import HostingServiceAccount


class HostingServiceAuthForm(forms.Form):
    """Form for handling authentication information for a hosting account.

    This takes care of collecting additional details needed for authenticating
    an account, including that information with the account credentials (if
    needed by the hosting service).

    By default, this will retain the existing username, password, and
    two-factor auth fields. Those can be replaced, but the field names should
    remain the same.

    Unlike :py:class:`HostingServiceForm`, field names on this class do not
    need to include a service-specific prefix, as they will not conflict with
    other forms. The field names will be used for the data storage. How a
    subclass chooses to name these fields is up to them.

    Subclasses can define a ``Meta`` class on the form containing
    ``help_texts`` and ``labels`` attributes, mapping field names to custom
    help text or labels. This is useful for providing more specific
    instructions for setting authentication data for a given service without
    having to override the built-in fields. For example:

    .. code-block:: python

        from django.utils.translation import ugettext_lazy as _
        from reviewboard.hostingsvcs.forms import HostingServiceAuthForm


        class MyAuthForm(HostingServiceAuthForm):
            class Meta:
                labels = {
                    'hosting_account_username': 'API Access ID',
                    'hosting_account_password': 'API Secret Key',
                }

                help_texts = {
                    'hosting_account_username': _(
                        'Access ID used for the API. This can be found in '
                        'your FooService account settings.'
                    ),
                    'hosting_account_password': _(
                        'Secret key used for the API. This can be found in '
                        'your FooService account settings.'
                    ),
                }
    """

    hosting_url = forms.CharField(
        label=_('Service URL'),
        required=True,
        widget=forms.TextInput(attrs={'size': 30}))

    hosting_account_username = forms.CharField(
        label=_('Account username'),
        required=True,
        widget=forms.TextInput(attrs={
            'size': 30,
            'autocomplete': 'off',
        }))

    hosting_account_password = forms.CharField(
        label=_('Account password'),
        required=True,
        widget=forms.PasswordInput(
            attrs={
                'size': 30,
                'autocomplete': 'off',
            },
            render_value=True))

    hosting_account_two_factor_auth_code = forms.CharField(
        label=_('Two-factor auth code'),
        required=False,
        widget=forms.TextInput(attrs={
            'size': 30,
            'autocomplete': 'off',
            'data-required-for-2fa': 'true',
        }))

    def __init__(self, data=None, hosting_service_cls=None,
                 hosting_account=None, local_site=None,
                 *args, **kwargs):
        """Initialize the authentication form.

        Args:
            data (dict, optional):
                Data posted for the form.

            hosting_service_cls (type):
                The hosting service class (subclass of
                :py:class:`~reviewboard.hostingsvcs.service.HostingService)
                that works with this form.

                This must be provided, or an assertion error will be raised.

            hosting_account (reviewboard.hostingsvcs.models.HostingServiceAccount,
                             optional):

                The hosting service account being updated, if any. If ``None``,
                a new one will be created.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site used for accounts on the service.

            *args (tuple):
                Extra positional arguments for the form.

            **kwargs (dict):
                Extra keyword arguments for the form.

        Raises:
            ValueError:
                One or more of the paramters are missing or not valid for the
                provided hosting account. Details are given in the error
                message.
        """
        if not hosting_service_cls:
            raise ValueError('hosting_service_cls cannot be None.')

        self.hosting_service_cls = hosting_service_cls
        self.hosting_account = hosting_account
        self.local_site = local_site
        hosting_service_id = hosting_service_cls.hosting_service_id

        # Make sure that the hosting account, if provided, is compatible with
        # the arguments provided.
        if (hosting_account and
            (hosting_account.local_site != local_site or
             hosting_account.service_name != hosting_service_id)):
            raise ValueError(
                ugettext('This account is not compatible with this '
                         'hosting service configuration.'))

        # Get initial data for fields based on the account.
        if hosting_account:
            initial = self.get_initial_data()
        else:
            initial = None

        super(HostingServiceAuthForm, self).__init__(data, initial=initial,
                                                     *args, **kwargs)

        # If the hosting service is not self-hosted, we don't want to include
        # the hosting_url form.
        if not hosting_service_cls.self_hosted:
            del self.fields['hosting_url']

        # If it doesn't support two-factor auth, get rid of that field.
        if not hosting_service_cls.supports_two_factor_auth:
            del self.fields['hosting_account_two_factor_auth_code']

        # Allow the subclass to override help text and field labels.
        meta = getattr(self, 'Meta', None)

        if meta:
            help_texts = getattr(meta, 'help_texts', {})
            labels = getattr(meta, 'labels', {})

            for field_name, help_text in six.iteritems(help_texts):
                self.fields[field_name].help_text = help_text

            for field_name, label in six.iteritems(labels):
                self.fields[field_name].label = label

    def get_initial_data(self):
        """Return initial data for the form, based on the hosting account.

        This will return initial data for the fields, generally pulled from
        the hosting account. This will be used when relinking a hosting
        account that's no longer authorized.

        Generally, sensitive information, like passwords, should not be
        provided.

        By default, the :py:attr:`username` and :py:attr:`hosting_url` fields
        will have data provided. Subclasses can override this to present more
        initial data.

        This is only called if the form was provided a hosting account during
        construction.

        Returns:
            dict:
            Initial data for the form.
        """
        initial = {
            'username': self.hosting_account.username,
        }

        if self.hosting_service_cls.self_hosted:
            initial['hosting_url'] = self.hosting_account.hosting_url

        return initial

    def get_credentials(self):
        """Return credentials from the form.

        This should return the data that will be stored along with the
        :py:class:`~reviewboard.hostingsvcs.models.HostingServiceAccount`.

        The ``username``, ``password``, and ``two_factor_auth_code`` values
        are treated specially during the creation and authentication of the
        account, and should be provided for most standard hosting services.

        All values will be provided to
        :py:attr:`HostingService.authenticate
        <reviewboard.hostingsvcs.service.HostingService.authenticate>`, which
        will be responsible for making use of these values and storing them
        on the account.

        Subclasses should call the parent method and use their results as
        a base, if they reuse any of the built-in fields.

        Returns:
            dict:
            A dictionary of credentials used to authenticate the account and
            talk to the API.
        """
        credentials = {
            'username': self.cleaned_data['hosting_account_username'],
            'password': self.cleaned_data['hosting_account_password'],
        }

        two_factor_auth_code = \
            self.cleaned_data.get('hosting_account_two_factor_auth_code')

        if two_factor_auth_code:
            credentials['two_factor_auth_code'] = two_factor_auth_code

        return credentials

    def save(self, allow_authorize=True, extra_authorize_kwargs={}):
        """Save the hosting account and authorize against the service.

        This will create or update a hosting account, based on the information
        provided in the form and to this method.

        :py:meth:`is_valid` must be called prior to saving.

        Args:
            allow_authorize (bool, optional):
                If ``True`` (the default), the account will be authorized
                against the hosting service. If ``False``, only the database
                entry for the account will be affected.

            extra_authorize_kwargs (dict, optional):
                Additional keyword arguments to provide for the
                :py:meth:`HostingService.authorize()
                <reviewboard.hostingsvcs.models.HostingService.authorize>`
                call.

        Returns:
            reviewboard.hostingsvcs.models.HostingServiceAccount:
            The updated or created hosting service account.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                Information needed to authorize was missing, or authorziation
                failed.

            reviewboard.hostingsvcs.errors.TwoFactorAuthCodeRequiredError:
                A two-factor authentication code is required to authorize the
                account. A code will need to be provided to the form.
        """
        credentials = self.get_credentials()

        # Grab the username from the credentials, sanity-checking that it's
        # been provided as part of the get_credentials() result.
        try:
            username = credentials['username']
        except KeyError:
            logging.exception('%s.get_credentials() must return a "username" '
                              'key.',
                              self.__class__.__name__)

            raise AuthorizationError(
                ugettext('Hosting service implementation error: '
                         '%s.get_credentials() must return a "username" key.')
                % self.__class__.__name__)

        hosting_account = self.hosting_account
        hosting_service_id = self.hosting_service_cls.hosting_service_id
        hosting_url = self.cleaned_data.get('hosting_url')

        if not self.hosting_service_cls.supports_two_factor_auth:
            assert hosting_url is None

        if hosting_account:
            # Update the username and hosting URL, if they've changed.
            hosting_account.username = username
            hosting_account.hosting_url = hosting_url
        else:
            # Fetch an existing hosting account based on the credentials and
            # parameters, if there is one. If not, we're going to create one,
            # but we won't save it until we've authorized.
            hosting_account_attrs = {
                'service_name': hosting_service_id,
                'username': username,
                'hosting_url': hosting_url,
                'local_site': self.local_site,
            }

            try:
                hosting_account = \
                    HostingServiceAccount.objects.get(**hosting_account_attrs)
            except HostingServiceAccount.DoesNotExist:
                # Create a new one, but don't save it yet.
                hosting_account = \
                    HostingServiceAccount(**hosting_account_attrs)

        if (allow_authorize and
            self.hosting_service_cls.needs_authorization and
            not hosting_account.is_authorized):
            # Attempt to authorize the account.
            if self.local_site:
                local_site_name = self.local_site.name
            else:
                local_site_name = None

            password = credentials.get('password')
            two_factor_auth_code = credentials.get('two_factor_auth_code')

            try:
                hosting_account.service.authorize(
                    username=username,
                    password=password,
                    hosting_url=hosting_url,
                    two_factor_auth_code=two_factor_auth_code,
                    local_site_name=local_site_name,
                    credentials=credentials,
                    **extra_authorize_kwargs)
            except TwoFactorAuthCodeRequiredError:
                # Mark this asrequired for the next form render.
                self.fields['hosting_account_two_factor_auth_code']\
                    .required = True

                # Re-raise the error.
                raise
            except AuthorizationError:
                logging.exception('Authorization error linking hosting '
                                  'account ID=%r for hosting service=%r, '
                                  'username=%r, LocalSite=%r',
                                  hosting_account.pk, hosting_service_id,
                                  username, local_site_name)

                # Re-raise the error.
                raise
            except Exception:
                logging.exception('Unknown error linking hosting account '
                                  'ID=%r for hosting service=%r, '
                                  'username=%r, LocalSite=%r',
                                  hosting_account.pk, hosting_service_id,
                                  username, local_site_name)

                # Re-raise the error.
                raise

        hosting_account.save()

        return hosting_account

    def clean_hosting_url(self):
        """Clean the hosting URL field.

        Returns:
            unicode:
            A string containing the hosting URL, or ``None``.
        """
        return self.cleaned_data['hosting_url'] or None


class HostingServiceForm(forms.Form):
    def load(self, repository):
        for field in self.fields:
            if self.prefix:
                key = self.prefix + '-' + field
            else:
                key = field

            value = repository.extra_data.get(key, None)

            if isinstance(value, bool) or value:
                self.fields[field].initial = value

    def save(self, repository, *args, **kwargs):
        if not self.errors:
            for key, value in six.iteritems(self.cleaned_data):
                if self.prefix:
                    key = self.prefix + '-' + key

                repository.extra_data[key] = value
