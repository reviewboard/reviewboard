from django import newforms as forms
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from djblets.auth.util import login_required

from reviewboard.accounts.models import Profile
from reviewboard.reviews.models import Group


class PreferencesForm(forms.Form):
    redirect_to = forms.CharField(required=False, widget=forms.HiddenInput)
    groups = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.fields['groups'].choices = \
            [(g.id, g.display_name) for g in Group.objects.all()]


@login_required
def user_preferences(request, template_name='accounts/prefs.html'):
    redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, '/')

    if request.POST:
        form = PreferencesForm(request.POST)

        if form.is_valid():
            request.user.group_set = form.clean_data['groups']
            request.user.save()

            profile, profile_is_new = \
                Profile.objects.get_or_create(user=request.user)
            profile.first_time_setup_done = True
            profile.save()

            return HttpResponseRedirect(redirect_to)

    else:
        form = PreferencesForm({
            'redirect_to': redirect_to,
            'groups': [g.id for g in request.user.group_set.all()],
        })

    try:
        profile = request.user.get_profile()
        must_configure = not profile.first_time_setup_done
    except Profile.DoesNotExist:
        must_configure = True

    return render_to_response(template_name, RequestContext(request, {
        'form': form,
        'must_configure': must_configure,
    }))
