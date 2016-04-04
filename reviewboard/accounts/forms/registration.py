from __future__ import unicode_literals

from django import forms
from djblets.auth.forms import RegistrationForm as DjbletsRegistrationForm
from djblets.recaptcha.mixins import RecaptchaFormMixin


class RegistrationForm(RecaptchaFormMixin, DjbletsRegistrationForm):
    """A registration form with reCAPTCHA support.

    This is a version of the Djblets RegistrationForm which knows how to
    validate a reCAPTCHA widget. Any error received is stored in the form
    for use when generating the widget so that the widget can properly display
    the error.
    """

    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)

    def save(self):
        """Save the form."""
        user = DjbletsRegistrationForm.save(self)

        if user:
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.save()

        return user
