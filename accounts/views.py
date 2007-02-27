from django import newforms as forms
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from djblets.auth.util import login_required


class PreferencesForm(forms.Form):
    collapsed_diffs = forms.BooleanField()
    wordwrapped_diffs = forms.BooleanField()


@login_required
def user_preferences(request, template_name='accounts/prefs.html'):
    if request.POST:
        form = PreferencesForm(request.POST)
    else:
        form = PreferencesForm()

    return render_to_response(template_name, RequestContext(request, {
        'form': form,
    }))
