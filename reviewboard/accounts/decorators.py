from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import simple_decorator

from reviewboard.accounts.models import Profile


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
        # Fetch the profile. If it exists, we're done, and it's cached for
        # later. If not, try to create it.
        if request.user.is_authenticated():
            Profile.objects.get_or_create(user=request.user)

        return view_func(request, *args, **kwargs)

    return _check_valid_prefs
