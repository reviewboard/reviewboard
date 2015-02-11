from __future__ import unicode_literals

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from djblets.auth.forms import RegistrationForm as DjbletsRegistrationForm
from djblets.siteconfig.models import SiteConfiguration
from recaptcha.client import captcha


class RegistrationForm(DjbletsRegistrationForm):
    """A registration form with reCAPTCHA support.

    This is a version of the Djblets RegistrationForm which knows how to
    validate a reCAPTCHA widget. Any error received is stored in the form
    for use when generating the widget so that the widget can properly display
    the error.
    """

    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    recaptcha_challenge_field = forms.CharField(required=False)
    recaptcha_response_field = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        """Initialize the form."""
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.captcha_error_query_str = ""

        siteconfig = SiteConfiguration.objects.get_current()

        if siteconfig.get('site_domain_method') == 'https':
            self.recaptcha_url = 'https://www.google.com/recaptcha/api'
        else:
            self.recaptcha_url = 'http://www.google.com/recaptcha/api'

    def clean(self):
        """Validate all form fields."""
        siteconfig = SiteConfiguration.objects.get_current()

        if siteconfig.get('auth_registration_show_captcha'):
            challenge = self.cleaned_data.get('recaptcha_challenge_field',
                                              None)
            response = self.cleaned_data.get('recaptcha_response_field', None)

            if challenge and response:
                captcha_response = \
                    captcha.submit(
                        challenge,
                        response,
                        siteconfig.get('recaptcha_private_key'),
                        self.request.META.get('REMOTE_ADDR', None))

                if not captcha_response.is_valid:
                    self.captcha_error_query_str = '&error=%s' % \
                        captcha_response.error_code

                    # This isn't actually seen in the Review Board UI,
                    # as the reCAPTCHA widget itself displays the error
                    # message. However, this may be useful for testing or
                    # debugging.
                    raise ValidationError(
                        _("The text you entered didn't match what was "
                          "displayed"))
            else:
                self.captcha_error_query_str = '&error=incorrect-captcha-sol'

                raise ValidationError(
                    _('You need to respond to the captcha'))

        return super(RegistrationForm, self).clean()

    def save(self):
        """Save the form."""
        user = DjbletsRegistrationForm.save(self)

        if user:
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.save()

        return user
