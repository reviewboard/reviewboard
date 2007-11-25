from django import newforms as forms
from django.utils.translation import ugettext as _

from reviewboard.reviews.models import Group


class PreferencesForm(forms.Form):
    redirect_to = forms.CharField(required=False, widget=forms.HiddenInput)
    groups = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple,
                                       required=False)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    syntax_highlighting = forms.BooleanField(required=False,
        label=_("Enable syntax highlighting in the diff viewer"))

    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.fields['groups'].choices = \
            [(g.id, g.display_name) for g in Group.objects.all()]
