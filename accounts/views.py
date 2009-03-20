import time
from sha import sha

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from djblets.auth.util import login_required
from djblets.auth.views import register
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.forms import PreferencesForm
from reviewboard.accounts.models import Profile


def account_register(request):
    """
    Handles redirection to the appropriate registration page, depending
    on the authentication type the user has configured.
    """
    siteconfig = SiteConfiguration.objects.get_current()
    auth_backend = siteconfig.get("auth_backend")

    if (auth_backend == "builtin" and
        siteconfig.settings.get(auth_enable_registration)):
        return register(request, next_page=settings.SITE_ROOT + 'dashboard/')

    return HttpResponseRedirect(reverse("login"))


@login_required
def user_preferences(request, template_name='accounts/prefs.html'):
    redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME,
                                      reverse("dashboard"))

    profile, profile_is_new = \
        Profile.objects.get_or_create(user=request.user)
    must_configure = not profile.first_time_setup_done
    profile.save()

    if request.POST:
        form = PreferencesForm(request.POST)

        if form.is_valid():
            siteconfig = SiteConfiguration.objects.get_current()
            auth_backend = siteconfig.get("auth_backend")

            if auth_backend == "builtin":
                if form.cleaned_data['password1']:
                    salt = sha(str(time.time())).hexdigest()[:5]
                    hash = sha(salt + form.cleaned_data['password1'])
                    newpassword = 'sha1$%s$%s' % (salt, hash.hexdigest())
                    request.user.password = newpassword

                request.user.first_name = form.cleaned_data['first_name']
                request.user.last_name = form.cleaned_data['last_name']
                request.user.email = form.cleaned_data['email']

            request.user.review_groups = form.cleaned_data['groups']
            request.user.save()

            profile.first_time_setup_done = True
            profile.syntax_highlighting = \
                form.cleaned_data['syntax_highlighting']
            profile.save()

            return HttpResponseRedirect(redirect_to)
    else:
        form = PreferencesForm({
            'settings': settings,
            'redirect_to': redirect_to,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'syntax_highlighting': profile.syntax_highlighting,
            'groups': [g.id for g in request.user.review_groups.all()],
        })

    return render_to_response(template_name, RequestContext(request, {
        'form': form,
        'settings': settings,
        'must_configure': must_configure,
    }))
