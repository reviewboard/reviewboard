from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext_lazy as _

from reviewboard.accounts.decorators import (check_login_required,
                                             valid_prefs_required)
from reviewboard.datagrids.grids import (DashboardDataGrid,
                                         GroupDataGrid,
                                         ReviewRequestDataGrid,
                                         UsersDataGrid,
                                         UserPageReviewsDataGrid,
                                         UserPageReviewRequestDataGrid)
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.site.decorators import check_local_site_access
from reviewboard.site.urlresolvers import local_site_reverse


def _is_datagrid_gridonly(request):
    """Return whether or not the current request is for an embedded datagrid.

    This method allows us to disable consent checks in
    :py:func:`~reviewboard.accounts.decorators.valid_prefs_required` when a
    datagrid is requesting updated data so that we do not return a redirect
    and embed the result of that redirect in the datagrid instead.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

    Returns:
        bool:
        Whether or not this request is for an embedded datagrid.
    """
    return 'gridonly' in request.GET


@check_login_required
@check_local_site_access
@valid_prefs_required(disable_consent_checks=_is_datagrid_gridonly)
def all_review_requests(request,
                        local_site=None,
                        template_name='datagrids/datagrid.html'):
    """Display a list of all review requests."""
    datagrid = ReviewRequestDataGrid(
        request,
        ReviewRequest.objects.public(user=request.user,
                                     status=None,
                                     local_site=local_site,
                                     with_counts=True,
                                     show_inactive=True),
        _("All Review Requests"),
        local_site=local_site)
    return datagrid.render_to_response(template_name)


@login_required
@check_local_site_access
@valid_prefs_required(disable_consent_checks=_is_datagrid_gridonly)
def dashboard(request,
              template_name='datagrids/dashboard.html',
              local_site=None):
    """Display the dashboard.

    This shows review requests organized by a variety of lists, depending on
    the 'view' parameter.

    Valid 'view' parameters are:

        * 'outgoing'
        * 'to-me'
        * 'to-group'
        * 'starred'
        * 'incoming'
        * 'mine'
    """
    grid = DashboardDataGrid(request, local_site=local_site)
    return grid.render_to_response(template_name)


@check_login_required
@check_local_site_access
@valid_prefs_required(disable_consent_checks=_is_datagrid_gridonly)
def group(request,
          name,
          template_name='datagrids/datagrid.html',
          local_site=None):
    """Display a list of review requests belonging to a particular group."""
    # Make sure the group exists
    group = get_object_or_404(Group, name=name, local_site=local_site)

    if not group.is_accessible_by(request.user):
        return render(request, 'datagrids/group_permission_denied.html',
                      status=403)

    datagrid = ReviewRequestDataGrid(
        request,
        ReviewRequest.objects.to_group(name,
                                       local_site,
                                       user=request.user,
                                       status=None,
                                       with_counts=True),
        _('Review requests for %s') % group.display_name,
        local_site=local_site)

    return datagrid.render_to_response(template_name)


@check_login_required
@check_local_site_access
@valid_prefs_required(disable_consent_checks=_is_datagrid_gridonly)
def group_list(request,
               local_site=None,
               template_name='datagrids/datagrid.html'):
    """Display a list of all review groups."""
    grid = GroupDataGrid(request, local_site=local_site)
    return grid.render_to_response(template_name)


@check_login_required
@check_local_site_access
@valid_prefs_required(disable_consent_checks=_is_datagrid_gridonly)
def group_members(request,
                  name,
                  template_name='datagrids/datagrid.html',
                  local_site=None):
    """Display a list of users registered for a particular group."""
    # Make sure the group exists
    group = get_object_or_404(Group,
                              name=name,
                              local_site=local_site)

    if not group.is_accessible_by(request.user):
        return render(request, 'datagrids/group_permission_denied.html',
                      status=403)

    datagrid = UsersDataGrid(request,
                             group.users.filter(is_active=True),
                             _("Members of group %s") % name)

    return datagrid.render_to_response(template_name)


@check_login_required
@check_local_site_access
@valid_prefs_required(disable_consent_checks=_is_datagrid_gridonly)
def submitter(request,
              username,
              grid=None,
              template_name='datagrids/datagrid.html',
              local_site=None):
    """Display a user's profile, showing their review requests and reviews.

    The 'grid' parameter determines which is displayed, and can take on the
    following values:

        * 'reviews'
        * 'review-requests'
    """
    # Make sure the user exists
    if local_site:
        try:
            user = local_site.users.get(username=username)
        except User.DoesNotExist:
            raise Http404
    else:
        user = get_object_or_404(User, username=username)

    if grid is None or grid == 'review-requests':
        datagrid_cls = UserPageReviewRequestDataGrid
    elif grid == 'reviews':
        datagrid_cls = UserPageReviewsDataGrid
    else:
        raise Http404

    datagrid = datagrid_cls(request, user, local_site=local_site)
    datagrid.tabs = [
        (UserPageReviewRequestDataGrid.tab_title,
         local_site_reverse('user', local_site=local_site,
                            args=[username])),
        (UserPageReviewsDataGrid.tab_title,
         local_site_reverse('user-grid', local_site=local_site,
                            args=[username, 'reviews']))
    ]

    return datagrid.render_to_response(template_name)


@check_login_required
@check_local_site_access
@valid_prefs_required(disable_consent_checks=_is_datagrid_gridonly)
def users_list(request,
               local_site=None,
               template_name='datagrids/datagrid.html'):
    """Display a list of all users."""
    grid = UsersDataGrid(request, local_site=local_site)
    return grid.render_to_response(template_name)
