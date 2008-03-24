from urllib import quote

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect

from djblets.auth.util import login_required
from djblets.util.decorators import simple_decorator

from reviewboard.accounts.models import Profile


@simple_decorator
def check_login_required(view_func):
    """
    A decorator that checks whether login is required on this installation
    and, if so, checks if the user is logged in. If login is required and
    the user is not logged in, they're redirected to the login link.
    """
    def _check(*args, **kwargs):
        if settings.REQUIRE_SITEWIDE_LOGIN:
            return login_required(view_func)(*args, **kwargs)
        else:
            return view_func(*args, **kwargs)

    return _check


@simple_decorator
def valid_prefs_required(view_func):
    """
    A decorator that checks whether the user has completed the first-time
    setup by saving their preferences at least once. Redirects to the
    preferences URL if they have not.
    """
    def _check_valid_prefs(request, *args, **kwargs):
        try:
            profile = request.user.get_profile()
            if profile.first_time_setup_done:
                return view_func(request, *args, **kwargs)
        except Profile.DoesNotExist:
            pass

        return HttpResponseRedirect("%saccount/preferences/?%s=%s" %
                                    (settings.SITE_ROOT,
                                     REDIRECT_FIELD_NAME,
                                     quote(request.get_full_path())))

    return _check_valid_prefs
