from django import forms
from django.utils.translation import ugettext_lazy as _

from reviewboard.scmtools.models import Repository, Tool


class RepositoryForm(forms.ModelForm):
    """
    A specialized form for RepositoryAdmin that makes the "password"
    field use a PasswordInput widget.
    """
    name = forms.CharField(
        label=_("Name"),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '30'}))

    path = forms.CharField(
        label=_("Path"),
        max_length=128,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))

    mirror_path = forms.CharField(
        label=_("Mirror path"),
        max_length=128,
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}))

    tool = forms.ModelChoiceField(
        label=_("Repository Type"),
        required=True,
        empty_label=None,
        queryset=Tool.objects.all())

    bug_tracker = forms.CharField(
        label=_("Bug tracker URL"),
        max_length=256,
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_("This should be the path to the bug tracker for this "
                    "repository. You must include '%s' in place of the "
                    "bug number."))

    username = forms.CharField(
        label=_("Username"),
        max_length=32,
        required=False)

    password = forms.CharField(
        label=_("Password"),
        required=False,
        widget=forms.PasswordInput)

    encoding = forms.CharField(
        label=_("Encoding"),
        max_length=32,
        required=False,
        help_text=_("The encoding used for files in this repository. This is "
                    "an advanced setting and should only be used if you're "
                    "sure you need it."))



