"""Review Board admin panel-specific decorators"""

from functools import wraps

from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import login
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _
from djblets.util.compat.django.shortcuts import render
from djblets.util.decorators import simple_decorator

from reviewboard.admin.read_only import is_site_read_only_for
from reviewboard.site.urlresolvers import local_site_reverse


def superuser_required(view):
    """Wrap a view so that is only accessible to superusers.

    Unauthenticated users will be redirected to the login page. Logged in users
    without sufficient permissions will be redirected to a page showing a
    permission denied error.

    This is very similar to Django's own
    :py:func:`~django.contrib.admin.views.decorators.staff_member_required`,
    except it checks for superuser status instead of staff status.

    Args:
        view (callable):
            The view to wrap.

    Returns:
        callable:
        The wrapped view.
    """
    @wraps(view)
    def decorated(request, *args, **kwargs):
        if not request.user.is_authenticated():
            return login(
                request,
                template_name='admin/login.html',
                authentication_form=AdminAuthenticationForm,
                extra_context={
                    'title': _('Log in'),
                    'app_path': request.get_full_path(),
                    REDIRECT_FIELD_NAME: request.get_full_path(),
                })

        if not (request.user.is_active and request.user.is_superuser):
            return render(
                request=request,
                template_name='admin/permission_denied.html',
                context={
                    'user': request.user,
                })

        return view(request, *args, **kwargs)

    return decorated


@simple_decorator
def check_read_only(view):
    """Check whether the site is read only.

    If the site is currently in read-only mode, this will redirect to a page
    indicating that state.

    Args:
        view (callable):
            The view to wrap.

    Returns:
        callable:
        The wrapped view.
    """
    def _check_read_only(request, *args, **kwargs):
        if is_site_read_only_for(request.user):
            return HttpResponseRedirect(
                local_site_reverse('read-only', request=request))
        else:
            return view(request, *args, **kwargs)

    return _check_read_only
