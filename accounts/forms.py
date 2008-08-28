from django import forms
from django.conf import settings
from django.forms import widgets
from django.utils.translation import ugettext as _

from djblets.siteconfig.models import SiteConfiguration

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
