from django import forms
from django.forms import widgets
from django.utils.translation import ugettext as _
from djblets.auth.forms import RegistrationForm as DjbletsRegistrationForm
from djblets.siteconfig.models import SiteConfiguration
from recaptcha.client import captcha

from reviewboard.reviews.models import Group


class PreferencesForm(forms.Form):
    redirect_to = forms.CharField(required=False, widget=forms.HiddenInput)
    groups = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple,
                                       required=False)
    syntax_highlighting = forms.BooleanField(required=False,
        label=_("Enable syntax highlighting in the diff viewer"))
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField()
    password1 = forms.CharField(required=False, widget=widgets.PasswordInput())
    password2 = forms.CharField(required=False, widget=widgets.PasswordInput())

    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)

        siteconfig = SiteConfiguration.objects.get_current()
        auth_backend = siteconfig.get("auth_backend")

        self.fields['groups'].choices = \
            [(g.id, g.display_name) for g in Group.objects.all()]
        self.fields['email'].required = (auth_backend == "builtin")

    def clean_password2(self):
        p1 = self.cleaned_data['password1']
        p2 = self.cleaned_data['password2']
        if p1 != p2:
            raise forms.ValidationError('passwords do not match')
        return p2


class RegistrationForm(DjbletsRegistrationForm):
    """A registration form with reCAPTCHA support.

    This is a version of the Djblets RegistrationForm which knows how to
    validate a reCAPTCHA widget. Any error received is stored in the form
    for use when generating the widget so that the widget can properly display
    the error.
    """
    recaptcha_challenge_field = forms.CharField(required=False)
    recaptcha_response_field = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.captcha_error_query_str = ""

        siteconfig = SiteConfiguration.objects.get_current()

        if siteconfig.get('site_domain_method') == 'https':
            self.recaptcha_url = 'https://api-secure.recaptcha.net'
        else:
            self.recaptcha_url = 'http://api.recaptcha.net'

    def clean(self):
        siteconfig = SiteConfiguration.objects.get_current()

        if siteconfig.get('auth_registration_show_captcha'):
            challenge = self.cleaned_data.get('recaptcha_challenge_field', None)
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
                    raise forms.ValidationError(
                        _("The text you entered didn't match what was "
                          "displayed"))
            else:
                self.captcha_error_query_str = '&error=incorrect-captcha-sol'

                raise forms.ValidationError(
                    _('You need to respond to the captcha'))

        return super(RegistrationForm, self).clean()
