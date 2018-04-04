from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from djblets.util.decorators import simple_decorator


@simple_decorator
def check_local_site_access(view_func):
    """Checks if a user has access to a Local Site.

    This checks whether or not the logged-in user is either a member of
    a Local Site or if the user otherwise has access to it.
    given local site. If not, this shows a permission denied page.
    """
    def _check(request, local_site_name=None, *args, **kwargs):
        if local_site_name:
            if not request.local_site:
                raise Http404

            local_site = request.local_site

            if not local_site.is_accessible_by(request.user):
                if local_site.public or request.user.is_authenticated():
                    response = render_to_response('permission_denied.html',
                                                  RequestContext(request))
                    response.status_code = 403
                    return response
                else:
                    return HttpResponseRedirect(
                        '%s?next=%s'
                        % (reverse('login'), request.get_full_path()))
        else:
            local_site = None

        return view_func(request, local_site=local_site, *args, **kwargs)

    return _check


@simple_decorator
def check_localsite_admin(view_func):
    """Checks if a user is an admin on a Local Site.

    This checks whether or not the logged-in user is marked as an admin for the
    given local site. If not, this shows a permission denied page.
    """
    def _check(request, local_site_name=None, *args, **kwargs):
        if local_site_name:
            if not request.local_site:
                raise Http404

            local_site = request.local_site

            if not local_site.is_mutable_by(request.user):
                response = render_to_response('permission_denied.html',
                                              RequestContext(request))
                response.status_code = 403
                return response
        else:
            local_site = None

        return view_func(request,
                         local_site_name=local_site_name,
                         local_site=local_site,
                         *args, **kwargs)

    return _check
