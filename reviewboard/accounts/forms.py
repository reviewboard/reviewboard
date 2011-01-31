import re
import sre_constants

from django import forms
from django.forms import widgets
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from djblets.auth.forms import RegistrationForm as DjbletsRegistrationForm
from djblets.siteconfig.forms import SiteSettingsForm
from djblets.siteconfig.models import SiteConfiguration
from recaptcha.client import captcha

from reviewboard.admin.checks import get_can_enable_dns, \
                                     get_can_enable_ldap
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

    def __init__(self, user, *args, **kwargs):
        from reviewboard.accounts.backends import get_auth_backends

        super(forms.Form, self).__init__(*args, **kwargs)

        siteconfig = SiteConfiguration.objects.get_current()
        auth_backends = get_auth_backends()


        choices = []
        for g in Group.objects.accessible(user=user).order_by('display_name'):
            choices.append((g.id, g.display_name))

        for site in user.local_site.all().order_by('name'):
            for g in Group.objects.accessible(
                user=user, local_site=site).order_by('display_name'):
                display_name = '%s / %s' % (g.local_site.name, g.display_name)
                choices.append((g.id, display_name))

        self.fields['groups'].choices = choices
        self.fields['email'].required = auth_backends[0].supports_change_email

    def save(self, user):
        from reviewboard.accounts.backends import get_auth_backends

        auth_backends = get_auth_backends()
        primary_backend = auth_backends[0]

        password = self.cleaned_data['password1']

        if primary_backend.supports_change_password and password:
            primary_backend.update_password(user, password)

        if primary_backend.supports_change_name:
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            primary_backend.update_name(user)

        if primary_backend.supports_change_email:
            user.email = self.cleaned_data['email']
            primary_backend.update_email(user)

        user.review_groups = self.cleaned_data['groups']
        user.save()

        profile = user.get_profile()
        profile.first_time_setup_done = True
        profile.syntax_highlighting = self.cleaned_data['syntax_highlighting']
        profile.save()

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
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
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

    def save(self):
        user = DjbletsRegistrationForm.save(self)

        if user:
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.save()

        return user


class ActiveDirectorySettingsForm(SiteSettingsForm):
    auth_ad_domain_name = forms.CharField(
        label=_("Domain name"),
        help_text=_("Enter the domain name to use, (ie. example.com). This will be "
                    "used to query for LDAP servers and to bind to the domain."),
        required=True)

    auth_ad_use_tls = forms.BooleanField(
        label=_("Use TLS for authentication"),
        required=False)

    auth_ad_find_dc_from_dns = forms.BooleanField(
        label=_("Find DC from DNS"),
        help_text=_("Query DNS to find which domain controller to use"),
        required=False)

    auth_ad_domain_controller = forms.CharField(
        label=_("Domain controller"),
        help_text=_("If not using DNS to find the DC specify the domain "
                    "controller here"),
        required=False)

    auth_ad_ou_name = forms.CharField(
        label=_("OU name"),
        help_text=_("Optionally restrict users to specified OU."),
        required=False)

    auth_ad_group_name = forms.CharField(
        label=_("Group name"),
        help_text=_("Optionally restrict users to specified group."),
        required=False)

    auth_ad_search_root = forms.CharField(
        label=_("Custom search root"),
        help_text=_("Optionally specify a custom search root, overriding "
                    "the built-in computed search root. If set, \"OU name\" "
                    "is ignored."),
        required=False)

    auth_ad_recursion_depth = forms.IntegerField(
        label=_("Recursion Depth"),
        help_text=_('Depth to recurse when checking group membership. '
                    '0 to turn off, -1 for unlimited.'),
        required=False)

    def load(self):
        can_enable_dns, reason = get_can_enable_dns()

        if not can_enable_dns:
            self.disabled_fields['auth_ad_find_dc_from_dns'] = reason

        can_enable_ldap, reason = get_can_enable_ldap()

        if not can_enable_ldap:
            self.disabled_fields['auth_ad_use_tls'] = True
            self.disabled_fields['auth_ad_group_name'] = True
            self.disabled_fields['auth_ad_recursion_depth'] = True
            self.disabled_fields['auth_ad_ou_name'] = True
            self.disabled_fields['auth_ad_search_root'] = True
            self.disabled_fields['auth_ad_find_dc_from_dns'] = True
            self.disabled_fields['auth_ad_domain_controller'] = True

            self.disabled_reasons['auth_ad_domain_name'] = reason

        super(ActiveDirectorySettingsForm, self).load()

    class Meta:
        title = _('Active Directory Authentication Settings')


class StandardAuthSettingsForm(SiteSettingsForm):
    auth_enable_registration = forms.BooleanField(
        label=_("Enable registration"),
        help_text=_("Allow users to register new accounts."),
        required=False)

    auth_registration_show_captcha = forms.BooleanField(
        label=_('Show a captcha for registration'),
        help_text=mark_safe(
            _('Displays a captcha using <a href="%(recaptcha_url)s">'
              'reCAPTCHA</a> on the registration page. To enable this, you '
              'will need to go <a href="%(register_url)s">here</A> to register '
              'an account and type in your new keys below.') % {
                  'recaptcha_url': 'http://www.recaptcha.net/',
                  'register_url': 'https://admin.recaptcha.net/recaptcha'
                                  '/createsite/',
            }),
        required=False)

    recaptcha_public_key = forms.CharField(
        label=_('reCAPTCHA Public Key'),
        required=False,
        widget=forms.TextInput(attrs={'size': '40'}))

    recaptcha_private_key = forms.CharField(
        label=_('reCAPTCHA Private Key'),
        required=False,
        widget=forms.TextInput(attrs={'size': '40'}))

    def clean_recaptcha_public_key(self):
        """Validates that the reCAPTCHA public key is specified if needed."""
        key = self.cleaned_data['recaptcha_public_key'].strip()

        if self.cleaned_data['auth_registration_show_captcha'] and not key:
            raise forms.ValidationError(_('This field is required.'))

        return key

    def clean_recaptcha_private_key(self):
        """Validates that the reCAPTCHA private key is specified if needed."""
        key = self.cleaned_data['recaptcha_private_key'].strip()

        if self.cleaned_data['auth_registration_show_captcha'] and not key:
            raise forms.ValidationError(_('This field is required.'))

        return key

    class Meta:
        title = _('Basic Authentication Settings')


class LDAPSettingsForm(SiteSettingsForm):
    # TODO: Invent a URIField and use it.
    auth_ldap_uri = forms.CharField(
        label=_("LDAP Server"),
        help_text=_("The LDAP server to authenticate with. "
                    "For example: ldap://localhost:389"))

    auth_ldap_base_dn = forms.CharField(
        label=_("LDAP Base DN"),
        help_text=_("The LDAP Base DN for performing LDAP searches.  For "
                    "example: ou=users,dc=example,dc=com"),
        required=True)

    auth_ldap_email_domain = forms.CharField(
        label=_("E-Mail Domain"),
        help_text=_("The domain name appended to the username to construct "
                    "the user's e-mail address. This takes precedence over "
                    '"E-Mail LDAP Attribute."'),
        required=False)

    auth_ldap_email_attribute = forms.CharField(
        label=_("E-Mail LDAP Attribute"),
        help_text=_("The attribute in the LDAP server that stores the user's "
                    "e-mail address. For example: mail"),
        required=False)

    auth_ldap_tls = forms.BooleanField(
        label=_("Use TLS for authentication"),
        required=False)

    auth_ldap_uid_mask = forms.CharField(
        label=_("User Mask"),
        initial="uid=%s,ou=users,dc=example,dc=com",
        help_text=_("The string representing the user. Use \"%(varname)s\" "
                    "where the username would normally go. For example: "
                    "(uid=%(varname)s)") %
                  {'varname': '%s'})

    auth_ldap_anon_bind_uid = forms.CharField(
        label=_("Anonymous User Mask"),
        help_text=_("The user mask string for anonymous users. If specified, "
                    "this should be in the same format as User Mask."),
        required=False)

    auth_ldap_anon_bind_passwd = forms.CharField(
        label=_("Anonymous User Password"),
        widget=forms.PasswordInput,
        help_text=_("The optional password for the anonymous user."),
        required=False)

    def load(self):
        can_enable_ldap, reason = get_can_enable_ldap()

        if not can_enable_ldap:
            self.disabled_fields['auth_ldap_uri'] = True
            self.disabled_fields['auth_ldap_email_domain'] = True
            self.disabled_fields['auth_ldap_email_attribute'] = True
            self.disabled_fields['auth_ldap_tls'] = True
            self.disabled_fields['auth_ldap_base_dn'] = True
            self.disabled_fields['auth_ldap_uid_mask'] = True
            self.disabled_fields['auth_ldap_anon_bind_uid'] = True
            self.disabled_fields['auth_ldap_anon_bind_password'] = True

            self.disabled_reasons['auth_ldap_uri'] = reason

        super(LDAPSettingsForm, self).load()

    class Meta:
        title = _('LDAP Authentication Settings')


class LegacyAuthModuleSettingsForm(SiteSettingsForm):
    custom_backends = forms.CharField(
        label=_("Backends"),
        help_text=_('A comma-separated list of old-style custom auth '
                    'backends. These are represented as Python module paths.'))

    def load(self):
        self.fields['custom_backends'].initial = \
            ', '.join(self.siteconfig.get('auth_custom_backends'))

        super(LegacyAuthModuleSettingsForm, self).load()

    def save(self):
        self.siteconfig.set('auth_custom_backends',
            re.split(r',\s*', self.cleaned_data['custom_backends']))

        super(LegacyAuthModuleSettingsForm, self).save()

    class Meta:
        title = _('Legacy Authentication Module Settings')
        save_blacklist = ('custom_backends',)


class NISSettingsForm(SiteSettingsForm):
    auth_nis_email_domain = forms.CharField(label=_("E-Mail Domain"))

    class Meta:
        title = _('NIS Authentication Settings')


class X509SettingsForm(SiteSettingsForm):
    auth_x509_username_field = forms.ChoiceField(
        label=_("Username Field"),
        choices=(
            # Note: These names correspond to environment variables set by
            #       mod_ssl.
            ("SSL_CLIENT_S_DN",        _("DN (Distinguished Name)")),
            ("SSL_CLIENT_S_DN_CN",     _("CN (Common Name)")),
            ("SSL_CLIENT_S_DN_Email",  _("Email address")),
        ),
        help_text=_("The X.509 certificate field from which the Review Board "
                    "username will be extracted."),
        required=True)

    auth_x509_username_regex = forms.CharField(
        label=_("Username Regex"),
        help_text=_("Optional regex used to convert the selected X.509 "
                    "certificate field to a usable Review Board username. For "
                    "example, if using the email field to retrieve the "
                    "username, use this regex to get the username from an "
                    "e-mail address: '(\s+)@yoursite.com'. There must be only "
                    "one group in the regex."),
        required=False)

    auth_x509_autocreate_users = forms.BooleanField(
        label=_("Automatically create new user accounts."),
        help_text=_("Enabling this option will cause new user accounts to be "
                    "automatically created when a new user with an X.509 "
                    "certificate accesses Review Board."),
        required=False)

    def clean_auth_x509_username_regex(self):
        """Validates that the specified regular expression is valid."""
        regex = self.cleaned_data['auth_x509_username_regex']

        try:
            re.compile(regex)
        except sre_constants.error, e:
            raise forms.ValidationError(e)

        return regex

    class Meta:
        title = _('X.509 Client Certificate Authentication Settings')
