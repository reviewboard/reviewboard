"""Review Board admin panel-specific decorators"""

from functools import wraps

from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import login
from django.shortcuts import render_to_response
from django.utils.translation import ugettext as _


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
            return render_to_response('admin/permission_denied.html', {
                'request': request,
                'user': request.user,
            })

        return view(request, *args, **kwargs)

    return decorated
