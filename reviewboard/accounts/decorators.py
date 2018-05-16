from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from djblets.privacy.consent import get_consent_tracker
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import simple_decorator

from reviewboard.accounts.models import Profile
from reviewboard.site.urlresolvers import local_site_reverse


@simple_decorator
def check_login_required(view_func):
    """Check whether the user needs to log in.

    This is a view decorator that checks whether login is required on this
    installation and, if so, checks if the user is logged in. If login is
    required and the user is not logged in, they're redirected to the login
    link.
    """
    def _check(*args, **kwargs):
        siteconfig = SiteConfiguration.objects.get_current()

        if siteconfig.get("auth_require_sitewide_login"):
            return login_required(view_func)(*args, **kwargs)
        else:
            return view_func(*args, **kwargs)

    return _check


@simple_decorator
def valid_prefs_required(view_func):
    """Check whether the profile object exists.

    Several views assume that the user profile object exists, and will break if
    it doesn't. This decorator will ensure that the profile exists before the
    view code runs.

    If the user is not logged in, this will do nothing. That allows it to
    be used with @check_login_required.
    """
    def _check_valid_prefs(request, *args, **kwargs):
        user = request.user

        # Fetch the profile. If it doesn't exist, create it.
        if user.is_authenticated():
            profile, is_new = Profile.objects.get_or_create(user=user)
            siteconfig = SiteConfiguration.objects.get_current()
            consent_tracker = get_consent_tracker()

            # Check if there are any privacy consent requirements that the
            # user needs to decide on before we can continue.
            if (siteconfig.get('privacy_enable_user_consent') and
                (is_new or
                 consent_tracker.get_pending_consent_requirements(user))):
                return HttpResponseRedirect(
                    '%s#privacy' % local_site_reverse('user-preferences',
                                                      request=request))

        return view_func(request, *args, **kwargs)

    return _check_valid_prefs
