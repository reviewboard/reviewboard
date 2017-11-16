"""Forms for OAuth2 applications."""

from __future__ import unicode_literals

from django import forms
from django.core.exceptions import ValidationError
from django.forms import widgets
from django.utils.translation import ugettext, ugettext_lazy as _
from djblets.forms.widgets import CopyableTextInput, ListEditWidget
from oauth2_provider.generators import (generate_client_id,
                                        generate_client_secret)
from oauth2_provider.validators import URIValidator

from reviewboard.admin.form_widgets import RelatedUserWidget
from reviewboard.oauth.models import Application
from reviewboard.oauth.widgets import OAuthSecretInputWidget
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse


class ApplicationChangeForm(forms.ModelForm):
    """A form for updating an Application.

    This form is intended to be used by the admin site.
    """

    DISABLED_FOR_SECURITY_ERROR = _(
        'This Application has been disabled to keep your server secure. '
        'It cannot be re-enabled until its client secret changes.'
    )

    client_id = forms.CharField(
        label=_('Client ID'),
        help_text=_(
            'The client ID. Your application will use this in OAuth2 '
            'authentication to identify itself.',
        ),
        widget=CopyableTextInput(attrs={
            'readonly': True,
            'size': 100,
        }),
        required=False,
    )

    def __init__(self, data=None, initial=None, instance=None):
        """Initialize the form:

        Args:
            data (dict, optional):
                The provided form data.

            initial (dict, optional):
                The initial form values.

            instance (Application, optional):
                The application to edit.
        """
        super(ApplicationChangeForm, self).__init__(data=data,
                                                    initial=initial,
                                                    instance=instance)

        if instance and instance.pk:
            # If we are creating an application (as the
            # ApplicationCreationForm is a subclass of this class), the
            # client_secret wont be present so we don't have to initialize the
            # widget.
            client_secret = self.fields['client_secret']
            client_secret.widget = OAuthSecretInputWidget(
                attrs=client_secret.widget.attrs,
                api_url=local_site_reverse('oauth-app-resource',
                                           local_site=instance.local_site,
                                           kwargs={'app_id': instance.pk}),
            )

    def clean_extra_data(self):
        """Prevent ``extra_data`` from being an empty string.

        Returns:
            unicode:
            Either a non-zero length string of JSON-encoded data or ``None``.
        """
        return self.cleaned_data['extra_data'] or None

    def clean_redirect_uris(self):
        """Clean the ``redirect_uris`` field.

        This method will ensure that all the URIs are valid by validating
        each of them, as well as removing unnecessary whitespace.

        Returns:
            unicode:
            A space-separated list of URIs.

        Raises:
            django.core.exceptions.ValidationError:
                Raised when one or more URIs are invalid.
        """
        validator = URIValidator()
        redirect_uris = self.cleaned_data.get('redirect_uris', '').split()
        errors = []

        for uri in redirect_uris:
            try:
                validator(uri)
            except ValidationError as e:
                errors.append(e)

        if errors:
            raise ValidationError(errors)

        # We join the list instead of returning the initial value because the
        # the original value may have had multiple adjacent whitespace
        # characters.
        return ' '.join(redirect_uris)

    def clean(self):
        """Validate the form.

        This will validate the relationship between the
        ``authorization_grant_type`` and ``redirect_uris`` fields to ensure the
        values are compatible.

        This method is very similar to
        :py:func:`Application.clean
        <oauth2_provider.models.AbstractApplication.clean>`, but the data will
        be verified by the form instead of the model to allow error messages to
        be usable by consumers of the form.

        This method does not raise an exception upon failing validation.
        Instead, it sets errors internally so that they are related to the
        pertinent field instead of the form as a whole.

        Returns:
            dict:
            The cleaned form data.
        """
        super(ApplicationChangeForm, self).clean()

        grant_type = self.cleaned_data.get('authorization_grant_type')

        # redirect_uris will not be present in cleaned_data if validation
        # failed.
        redirect_uris = self.cleaned_data.get('redirect_uris')

        if (redirect_uris is not None and
            len(redirect_uris) == 0 and
            grant_type in (Application.GRANT_AUTHORIZATION_CODE,
                           Application.GRANT_IMPLICIT)):
            # This is unfortunately not publicly exposed in Django 1.6, but it
            # is exposed in later versions (as add_error).
            self._errors['redirect_uris'] = self.error_class([
                ugettext(
                    'The "redirect_uris" field may not be blank when '
                    '"authorization_grant_type" is "%s"'
                )
                % grant_type
            ])

            self.cleaned_data.pop('redirect_uris')

        if (self.instance and
            self.instance.pk and
            self.instance.is_disabled_for_security and
            self.cleaned_data['enabled']):
            raise ValidationError(self.DISABLED_FOR_SECURITY_ERROR)

        if 'client_id' in self.cleaned_data:
            del self.cleaned_data['client_id']

        if 'client_secret' in self.cleaned_data:
            del self.cleaned_data['client_secret']

        return self.cleaned_data

    class Meta:
        model = Application
        fields = '__all__'
        help_texts = {
            'authorization_grant_type': _(
                'How the authorization is granted to the application.'
            ),
            'client_secret': _(
                'The client secret. This should only be known to Review Board '
                'and your application.'
            ),
            'client_type': _(
                "The type of client. Confidential clients must be able to "
                "keep users' passwords secure."
            ),
            'name': _(
                'The application name.'
            ),
            'redirect_uris': _(
                'A list of allowed URIs to redirect to.',
            ),
            'skip_authorization': _(
                'Whether or not users will be prompted for authentication. '
                'This should most likely be unchecked.'
            ),
            'user': _(
                'The user who created the application. The selected user will '
                'be able to change these settings from their account settings.'
            ),
        }

        widgets = {
            'client_secret': CopyableTextInput(attrs={
                'readonly': True,
                'size': 100,
            }),
            'name': widgets.TextInput(attrs={'size': 60}),
            'redirect_uris': ListEditWidget(attrs={'size': 60}, sep=' '),
            'user': RelatedUserWidget(multivalued=False),
            'original_user': RelatedUserWidget(multivalued=False),
        }

        labels = {
            'authorization_grant_type': _('Authorization Grant Type'),
            'client_secret': _('Client Secret'),
            'client_type': _('Client Type'),
            'name': _('Name'),
            'redirect_uris': _('Redirect URIs'),
            'skip_authorization': _('Skip Authorization'),
            'user': _('User'),
        }


class ApplicationCreationForm(ApplicationChangeForm):
    """A form for creating an Application.

    This is meant to be used by the admin site.
    """

    def save(self, commit=True):
        """Save the form.

        This method will generate the ``client_id`` and ``client_secret``
        fields.

        Args:
            commit (bool, optional):
                Whether or not the Application should be saved to the database.

        Returns:
            reviewboard.oauth.models.Application:
            The created Application.
        """
        instance = super(ApplicationCreationForm, self).save(commit=False)

        instance.client_id = generate_client_id()
        instance.client_secret = generate_client_secret()

        if commit:
            instance.save()

        return instance

    class Meta(ApplicationChangeForm.Meta):
        exclude = (
            'client_id',
            'client_secret',
        )


class UserApplicationChangeForm(ApplicationChangeForm):
    """A form for an end user to change an Application."""

    def __init__(self, user, data=None, initial=None, instance=None):
        """Initialize the form.

        Args:
            user (django.contrib.auth.models.User):
                The user changing the form. Ignored, but included to match
                :py:meth:`UserApplicationCreationForm.__init__`.

            data (dict):
                The provided data.

            initial (dict, optional):
                The initial form values.

            instance (reviewboard.oauth.models.Application):
                The Application that is to be edited.
        """
        super(UserApplicationChangeForm, self).__init__(data=data,
                                                        initial=initial,
                                                        instance=instance)

        local_site_field = self.fields['local_site']
        local_site_field.queryset = LocalSite.objects.filter(users=user)
        local_site_field.widget.attrs['disabled'] = True

    def clean(self):
        """Clean the form data.

        This method will ensure that the ``local_site`` field cannot be changed
        via form submission.

        Returns:
            dict:
            A dictionary of the cleaned form data.
        """
        super(UserApplicationChangeForm, self).clean()

        if 'local_site' in self.cleaned_data:
            self.cleaned_data.pop('local_site')

        return self.cleaned_data

    class Meta(ApplicationChangeForm.Meta):
        exclude = (
            'extra_data',
            'original_user',
            'skip_authorization',
            'user',
        )

        labels = dict(
            ApplicationChangeForm.Meta.labels,
            local_site=_('Restrict To'),
        )

        help_texts = dict(
            ApplicationChangeForm.Meta.help_texts,
            local_site=_('If this application is not restricted, it will be '
                         'available to all users.<br><br>This cannot be '
                         'changed once set.'),
        )


class UserApplicationCreationForm(ApplicationCreationForm):
    """A form for an end user to update an Application."""

    def __init__(self, user, data, initial=None, instance=None):
        """Initialize the form.

        Args:
            user (django.contrib.auth.models.User):
                The user changing the form. Ignored, but included to match
                :py:meth:`UserApplicationCreationForm.__init__`.

            data (dict):
                The provided data.

            initial (dict, optional):
                The initial form values.

            instance (reviewboard.oauth.models.Application, optional):
                The Application that is to be edited.

                This should always be ``None``.
        """
        assert instance is None
        super(UserApplicationCreationForm, self).__init__(data=data,
                                                          initial=initial,
                                                          instance=instance)

        self.user = user
        self.fields['local_site'].queryset = LocalSite.objects.filter(
            users=user)

    def save(self, commit=True):
        """Save the form.

        This method will associate the user creating the application as its
        owner.

        Args:
            commit (bool, optional):
                Whether or not the Application should be saved to the database.

        Returns:
            reviewboard.oauth.models.Application:
            The created Application.
        """
        instance = super(UserApplicationCreationForm, self).save(commit=False)
        instance.user = self.user

        if commit:
            instance.save()

        return instance

    class Meta(ApplicationCreationForm.Meta):
        exclude = (ApplicationCreationForm.Meta.exclude +
                   UserApplicationChangeForm.Meta.exclude)

        labels = dict(
            ApplicationCreationForm.Meta.labels,
            local_site=UserApplicationChangeForm.Meta.labels['local_site'],
        )

        help_texts = dict(
            ApplicationCreationForm.Meta.help_texts,
            local_site=UserApplicationChangeForm.Meta.help_texts['local_site'],
        )
