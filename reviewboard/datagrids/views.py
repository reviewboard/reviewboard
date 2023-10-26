"""Views for the Review Board datagrids."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Type

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _

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

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse
    from djblets.datagrid.grids import DataGrid

    from reviewboard.site.models import LocalSite


#: The template used for rendering all datagrids.
#:
#: Version Added:
#:     5.0.7
_DATAGRID_TEMPLATE_NAME = 'datagrids/datagrid.html'


def _is_datagrid_gridonly(
    request: HttpRequest,
) -> bool:
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
def all_review_requests(
    request: HttpRequest,
    *,
    local_site: Optional[LocalSite] = None,
) -> HttpResponse:
    """Display a list of all review requests.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site.

    Returns:
        django.http.HttpResponse:
        The rendered HTTP response for the datagrid.
    """
    datagrid = ReviewRequestDataGrid(
        request=request,
        queryset=ReviewRequest.objects.public(
            user=request.user,
            status=None,
            local_site=local_site,
            with_counts=True,
            show_inactive=True),
        title=_('All Review Requests'),
        local_site=local_site)

    return datagrid.render_to_response(_DATAGRID_TEMPLATE_NAME)


@login_required
@check_local_site_access
@valid_prefs_required(disable_consent_checks=_is_datagrid_gridonly)
def dashboard(
    request: HttpRequest,
    local_site: Optional[LocalSite] = None,
) -> HttpResponse:
    """Display the dashboard.

    This shows review requests organized by a variety of lists, depending on
    the ``view`` GET parameter. Valid ``view`` parameters are:

    * ``incoming``
    * ``mine``
    * ``outgoing``
    * ``overview``
    * ``starred``
    * ``to-group``
    * ``to-me``

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site.

    Returns:
        django.http.HttpResponse:
        The rendered HTTP response for the datagrid. What datagrid is rendered
        depends on the ``view`` parameter.
    """
    grid = DashboardDataGrid(request=request,
                             local_site=local_site)

    return grid.render_to_response(_DATAGRID_TEMPLATE_NAME)


@check_login_required
@check_local_site_access
@valid_prefs_required(disable_consent_checks=_is_datagrid_gridonly)
def group(
    request: HttpRequest,
    *,
    name: str,
    local_site: Optional[LocalSite] = None,
) -> HttpResponse:
    """Display a list of review requests belonging to a particular group.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        name (str):
            The name of the review group to view.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site.

    Returns:
        django.http.HttpResponse:
        The rendered HTTP response for the datagrid.
    """
    # Make sure the group exists
    group = get_object_or_404(Group, name=name, local_site=local_site)

    if not group.is_accessible_by(request.user):
        return render(request, 'datagrids/group_permission_denied.html',
                      status=403)

    datagrid = ReviewRequestDataGrid(
        request=request,
        queryset=ReviewRequest.objects.to_group(
            group_name=name,
            local_site=local_site,
            user=request.user,
            status=None,
            with_counts=True),
        title=_('Review requests for %s') % group.display_name,
        local_site=local_site)

    return datagrid.render_to_response(_DATAGRID_TEMPLATE_NAME)


@check_login_required
@check_local_site_access
@valid_prefs_required(disable_consent_checks=_is_datagrid_gridonly)
def group_list(
    request: HttpRequest,
    *,
    local_site: Optional[LocalSite] = None,
) -> HttpResponse:
    """Display a list of all review groups.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site.

    Returns:
        django.http.HttpResponse:
        The rendered HTTP response for the datagrid.
    """
    grid = GroupDataGrid(request=request,
                         local_site=local_site)

    return grid.render_to_response(_DATAGRID_TEMPLATE_NAME)


@check_login_required
@check_local_site_access
@valid_prefs_required(disable_consent_checks=_is_datagrid_gridonly)
def group_members(
    request: HttpRequest,
    *,
    name: str,
    local_site: Optional[LocalSite] = None,
) -> HttpResponse:
    """Display a list of users registered for a particular group.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        name (str):
            The name of the review group to view.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site.

    Returns:
        django.http.HttpResponse:
        The rendered HTTP response for the datagrid.
    """
    # Make sure the group exists
    group = get_object_or_404(Group,
                              name=name,
                              local_site=local_site)

    if not group.is_accessible_by(request.user):
        return render(request, 'datagrids/group_permission_denied.html',
                      status=403)

    datagrid = UsersDataGrid(
        request=request,
        queryset=group.users.filter(is_active=True),
        title=_('Members of group %s') % name)

    return datagrid.render_to_response(_DATAGRID_TEMPLATE_NAME)


@check_login_required
@check_local_site_access
@valid_prefs_required(disable_consent_checks=_is_datagrid_gridonly)
def submitter(
    request: HttpRequest,
    *,
    username: str,
    local_site: Optional[LocalSite] = None,
    grid: Optional[str] = None,
) -> HttpResponse:
    """Display a user's profile, showing their review requests and reviews.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site.

        grid (str):
            The name of the datagrid to view.

            This can be one of:

            * ``review-request``
            * ``reviews``

    Returns:
        django.http.HttpResponse:
        The rendered HTTP response for the datagrid.
    """
    # Make sure the user exists.
    if local_site:
        try:
            user = local_site.users.get(username=username)
        except User.DoesNotExist:
            raise Http404
    else:
        user = get_object_or_404(User, username=username)

    datagrid_cls: Type[DataGrid]

    if grid is None or grid == 'review-requests':
        datagrid_cls = UserPageReviewRequestDataGrid
    elif grid == 'reviews':
        datagrid_cls = UserPageReviewsDataGrid
    else:
        raise Http404

    datagrid = datagrid_cls(request, user, local_site=local_site)
    datagrid.tabs = [
        (UserPageReviewRequestDataGrid.tab_title,
         local_site_reverse('user',
                            local_site=local_site,
                            args=[username])),
        (UserPageReviewsDataGrid.tab_title,
         local_site_reverse('user-grid',
                            local_site=local_site,
                            args=[username, 'reviews']))
    ]

    return datagrid.render_to_response(_DATAGRID_TEMPLATE_NAME)


@check_login_required
@check_local_site_access
@valid_prefs_required(disable_consent_checks=_is_datagrid_gridonly)
def users_list(
    request: HttpRequest,
    *,
    local_site: Optional[LocalSite] = None,
) -> HttpResponse:
    """Display a list of all users.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site.

    Returns:
        django.http.HttpResponse:
        The rendered HTTP response for the datagrid.
    """
    grid = UsersDataGrid(request=request,
                         local_site=local_site)

    return grid.render_to_response(_DATAGRID_TEMPLATE_NAME)
