from __future__ import unicode_literals

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.utils.six.moves.urllib.parse import quote
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import simple_decorator

from reviewboard.accounts.models import Profile
from reviewboard.accounts.privacy import is_consent_missing
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


def valid_prefs_required(view_func=None, disable_consent_checks=None):
    """Check whether the profile object exists.

    Several views assume that the user profile object exists, and will break if
    it doesn't. This decorator will ensure that the profile exists before the
    view code runs.

    If the user is not logged in, this will do nothing. That allows it to
    be used with @check_login_required.

    Args:
        view_func (callable, optional):
            The view to decorate.

            If this is not specified, this function returns a decorator that
            accepts a view to decorate.

        disable_consent_checks (callable, optional):
            A callable that will determine whether or not consent checks should
            be disabled.

    Returns:
        callable:
        If ``view_func`` was provided, this returns a decorated version of that
        view. Otherwise a decorator is returned.
    """
    def decorator(view_func):
        @wraps(view_func)
        def decorated(request, *args, **kwargs):
            user = request.user

            if user.is_authenticated():
                profile, is_new = Profile.objects.get_or_create(user=user)
                siteconfig = SiteConfiguration.objects.get_current()

                if (siteconfig.get('privacy_enable_user_consent') and
                    not (callable(disable_consent_checks) and
                         disable_consent_checks(request)) and
                    (is_new or is_consent_missing(user))):
                    return HttpResponseRedirect(
                        '%s?next=%s'
                        % (local_site_reverse('user-preferences',
                                              request=request),
                           quote(request.get_full_path()))
                    )

            return view_func(request, *args, **kwargs)

        return decorated

    if view_func is not None:
        return decorator(view_func)

    return decorator
