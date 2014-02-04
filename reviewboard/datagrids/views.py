from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from reviewboard.accounts.decorators import (check_login_required,
                                             valid_prefs_required)
from reviewboard.extensions.hooks import DashboardHook, UserPageSidebarHook
from reviewboard.datagrids.grids import (DashboardDataGrid,
                                         GroupDataGrid,
                                         ReviewRequestDataGrid,
                                         SubmitterDataGrid,
                                         WatchedGroupDataGrid,
                                         get_sidebar_counts)
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.reviews.views import _render_permission_denied
from reviewboard.site.decorators import check_local_site_access


@check_login_required
@check_local_site_access
def all_review_requests(request,
                        local_site=None,
                        template_name='datagrids/datagrid.html'):
    """Displays a list of all review requests."""
    datagrid = ReviewRequestDataGrid(
        request,
        ReviewRequest.objects.public(user=request.user,
                                     status=None,
                                     local_site=local_site,
                                     with_counts=True),
        _("All Review Requests"),
        local_site=local_site)
    return datagrid.render_to_response(template_name)


@login_required
@check_local_site_access
@valid_prefs_required
def dashboard(request,
              template_name='datagrids/dashboard.html',
              local_site=None):
    """
    The dashboard view, showing review requests organized by a variety of
    lists, depending on the 'view' parameter.

    Valid 'view' parameters are:

        * 'outgoing'
        * 'to-me'
        * 'to-group'
        * 'starred'
        * 'watched-groups'
        * 'incoming'
        * 'mine'
    """
    view = request.GET.get('view', None)
    context = {}

    if view == "watched-groups":
        # This is special. We want to return a list of groups, not
        # review requests.
        grid = WatchedGroupDataGrid(request, local_site=local_site)
    else:
        grid = DashboardDataGrid(request, local_site=local_site)

    if not request.GET.get('gridonly', False):
        context = {
            'sidebar_counts': get_sidebar_counts(request.user, local_site),
            'sidebar_hooks': DashboardHook.hooks,
        }

    return grid.render_to_response(template_name, extra_context=context)


@check_login_required
@check_local_site_access
def group(request,
          name,
          template_name='datagrids/datagrid.html',
          local_site=None):
    """
    A list of review requests belonging to a particular group.
    """
    # Make sure the group exists
    group = get_object_or_404(Group, name=name, local_site=local_site)

    if not group.is_accessible_by(request.user):
        return _render_permission_denied(
            request, 'datagrids/group_permission_denied.html')

    datagrid = ReviewRequestDataGrid(
        request,
        ReviewRequest.objects.to_group(name,
                                       local_site,
                                       user=request.user,
                                       status=None,
                                       with_counts=True),
        _("Review requests for %s") % name,
        local_site=local_site)

    return datagrid.render_to_response(template_name)


@check_login_required
@check_local_site_access
def group_list(request,
               local_site=None,
               template_name='datagrids/datagrid.html'):
    """Displays a list of all review groups."""
    grid = GroupDataGrid(request, local_site=local_site)
    return grid.render_to_response(template_name)


@check_login_required
@check_local_site_access
def group_members(request,
                  name,
                  template_name='datagrids/datagrid.html',
                  local_site=None):
    """
    A list of users registered for a particular group.
    """
    # Make sure the group exists
    group = get_object_or_404(Group,
                              name=name,
                              local_site=local_site)

    if not group.is_accessible_by(request.user):
        return _render_permission_denied(
            request, 'datagrids/group_permission_denied.html')

    datagrid = SubmitterDataGrid(request,
                                 group.users.filter(is_active=True),
                                 _("Members of group %s") % name)

    return datagrid.render_to_response(template_name)


@check_login_required
@check_local_site_access
def submitter(request,
              username,
              template_name='datagrids/user_page.html',
              local_site=None):
    """
    A list of review requests owned by a particular user.
    """
    # Make sure the user exists
    if local_site:
        try:
            user = local_site.users.get(username=username)
        except User.DoesNotExist:
            raise Http404
    else:
        user = get_object_or_404(User, username=username)

    datagrid = ReviewRequestDataGrid(
        request,
        ReviewRequest.objects.from_user(username,
                                        user=request.user,
                                        status=None,
                                        with_counts=True,
                                        local_site=local_site,
                                        filter_private=True),
        _("%s's review requests") % username,
        local_site=local_site)

    return datagrid.render_to_response(template_name, extra_context={
        'show_profile': user.is_profile_visible(request.user),
        'sidebar_hooks': UserPageSidebarHook.hooks,
        'viewing_user': user,
        'groups': user.review_groups.accessible(request.user),
    })


@check_login_required
@check_local_site_access
def submitter_list(request,
                   local_site=None,
                   template_name='datagrids/datagrid.html'):
    """Displays a list of all users."""
    grid = SubmitterDataGrid(request, local_site=local_site)
    return grid.render_to_response(template_name)
