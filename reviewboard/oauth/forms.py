"""Forms for OAuth2 applications."""

from __future__ import unicode_literals

from django import forms
from django.forms import widgets
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import ugettext, ugettext_lazy as _

from reviewboard.oauth.models import Application


class ApplicationForm(forms.ModelForm):
    """The application configuration form.

    This form provides a more helpful user selection widget, as well as
    providing help text for all fields.
    """

    def clean_redirect_uris(self):
        """Clean the redirect_uris field.

        This method will ensure that all the URIs are valid by validating
        each of them, as well as removing unnecessary whitespace.

        Returns:
            unicode:
            A space-separated list of URIs.

        Raises:
            django.core.exceptions.ValidationError:
                Raised when one or more URIs are invalid.
        """
        validator = URLValidator()
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
        self.cleaned_data = super(ApplicationForm, self).clean()

        grant_type = self.cleaned_data.get('authorization_grant_type')

        if (not self.cleaned_data.get('redirect_uris') or
            grant_type in (Application.GRANT_AUTHORIZATION_CODE,
                           Application.GRANT_IMPLICIT)):
            # This is unfortunately not publicly exposed in Django 1.6, but it
            # is exposed in later versions (as add_error).
            error = ValidationError(
                ugettext(
                    'The "redirect_uris" field may not be blank when '
                    '"authorization_grant_type" is %s"'
                )
                % self.cleaned_data.get('authorization-grant_type')
            )
            self._errors.setdefault('redirect_uris', self.error_class)
            self._errors['redirect_uris'].append(error)

            self.cleaned_data.pop('redirect_uris')

        return self.cleaned_data

    class Meta:
        model = Application
        fields = '__all__'
        help_texts = {
            'authorization_grant_type': _(
                'How the authorization is granted to the application.'
            ),
            'client_id': _(
                'The client ID.'
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
                'A line-separated list of allowed URIs to redirect to.'
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
            'redirect_uris': widgets.Textarea(),
        }
