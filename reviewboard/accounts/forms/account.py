from __future__ import unicode_literals

from django import forms
from django.core.exceptions import ValidationError
from django.forms import widgets
from django.utils.translation import ugettext_lazy as _
from djblets.forms.fields import TimeZoneField

from reviewboard.accounts.backends import get_auth_backends
from reviewboard.accounts.models import Profile
from reviewboard.reviews.models import Group


class PreferencesForm(forms.Form):
    redirect_to = forms.CharField(required=False, widget=forms.HiddenInput)
    groups = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple,
                                       required=False)
    syntax_highlighting = forms.BooleanField(
        required=False,
        label=_("Enable syntax highlighting in the diff viewer"))
    profile_private = forms.BooleanField(
        required=False,
        label=_("Keep your user profile private"))
    open_an_issue = forms.BooleanField(
        required=False,
        label=_("Always open an issue when comment box opens"))
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField()
    password1 = forms.CharField(required=False, widget=widgets.PasswordInput())
    password2 = forms.CharField(required=False, widget=widgets.PasswordInput())
    timezone = TimeZoneField(
        label=_("Time Zone"),
        required=True,
        help_text=_("The time zone used for this account."))

    def __init__(self, user, *args, **kwargs):
        super(PreferencesForm, self).__init__(*args, **kwargs)

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

        profile, is_new = Profile.objects.get_or_create(user=user)
        profile.first_time_setup_done = True
        profile.syntax_highlighting = self.cleaned_data['syntax_highlighting']
        profile.is_private = self.cleaned_data['profile_private']
        profile.open_an_issue = self.cleaned_data['open_an_issue']
        profile.timezone = self.cleaned_data['timezone']
        profile.save()

    def clean_password2(self):
        p1 = self.cleaned_data['password1']
        p2 = self.cleaned_data['password2']

        if p1 != p2:
            raise ValidationError(_('Passwords do not match'))

        return p2
