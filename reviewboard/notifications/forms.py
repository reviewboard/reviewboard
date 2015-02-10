from __future__ import unicode_literals

from django import forms

from reviewboard.notifications.models import WebHookTarget


class WebHookTargetForm(forms.ModelForm):
    class Meta:
        model = WebHookTarget
        widgets = {
            'url': forms.widgets.TextInput(attrs={'size': 100}),
            'apply_to': forms.widgets.RadioSelect(),
        }
