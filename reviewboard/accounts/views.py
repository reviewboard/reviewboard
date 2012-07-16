from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from djblets.auth.util import login_required
from djblets.auth.views import register
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.backends import get_auth_backends
from reviewboard.accounts.forms import PreferencesForm, RegistrationForm
from reviewboard.accounts.models import Profile
from reviewboard.accounts.signals import user_registered


def account_register(request, next_url='dashboard'):
    """
    Handles redirection to the appropriate registration page, depending
    on the authentication type the user has configured.
    """
    siteconfig = SiteConfiguration.objects.get_current()
    auth_backends = get_auth_backends()

    if (auth_backends[0].supports_registration and
        siteconfig.get("auth_enable_registration")):
        response = register(request, next_page=reverse(next_url),
                            form_class=RegistrationForm)

        if request.user.is_authenticated():
            # This will trigger sending an e-mail notification for
            # user registration, if enabled.
            user_registered.send(sender=None, user=request.user)

        return response

    return HttpResponseRedirect(reverse("login"))


@login_required
def user_preferences(request, template_name='accounts/prefs.html'):
    # TODO: Figure out the right place to redirect when using a LocalSite.
    redirect_to = \
        request.REQUEST.get(REDIRECT_FIELD_NAME,
            request.REQUEST.get('redirect_to', None))

    if not redirect_to:
        redirect_to = reverse("dashboard")

    try:
        profile = request.user.get_profile()
    except Profile.DoesNotExist:
        # The Profile didn't exist, but it might have been created since.
        # Let's try to create one, and if one exists now, we'll just
        # fetch again.
        try:
            profile = Profile.objects.create(user=request.user)
        except IntegrityError:
            # This was created since we checked, so load it again.
            profile = request.user.get_profile()

    auth_backends = get_auth_backends()

    if request.POST:
        form = PreferencesForm(request.user, request.POST)

        if form.is_valid():
            form.save(request.user)

            return HttpResponseRedirect(redirect_to)
    else:
        form = PreferencesForm(request.user, {
            'settings': settings,
            'redirect_to': redirect_to,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'timezone': profile.timezone,
            'syntax_highlighting': profile.syntax_highlighting,
            'profile_private': profile.is_private,
            'open_an_issue': profile.open_an_issue,
            'groups': [g.id for g in request.user.review_groups.all()],
        })

    return render_to_response(template_name, RequestContext(request, {
        'form': form,
        'settings': settings,
        'can_change_password': auth_backends[0].supports_change_password,
    }))
