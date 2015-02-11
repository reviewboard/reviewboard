from __future__ import unicode_literals

import pytz

from django.contrib.auth.models import User
from django.http import Http404
from django.utils.translation import ugettext_lazy as _
from djblets.datagrid.grids import Column, DateTimeColumn, DataGrid
from djblets.util.templatetags.djblets_utils import ageid

from reviewboard.accounts.models import Profile, LocalSiteProfile
from reviewboard.datagrids.columns import (BugsColumn,
                                           DateTimeSinceColumn,
                                           DiffSizeColumn,
                                           DiffUpdatedColumn,
                                           DiffUpdatedSinceColumn,
                                           GroupMemberCountColumn,
                                           GroupsColumn,
                                           MyCommentsColumn,
                                           NewUpdatesColumn,
                                           PendingCountColumn,
                                           PeopleColumn,
                                           RepositoryColumn,
                                           ReviewCountColumn,
                                           ReviewGroupStarColumn,
                                           ReviewRequestCheckboxColumn,
                                           ReviewRequestIDColumn,
                                           ReviewRequestStarColumn,
                                           ShipItColumn,
                                           SubmitterColumn,
                                           SummaryColumn,
                                           ToMeColumn)
from reviewboard.datagrids.sidebar import Sidebar, DataGridSidebarMixin
from reviewboard.datagrids.builtin_items import (IncomingSection,
                                                 OutgoingSection,
                                                 UserGroupsItem,
                                                 UserProfileItem)
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.site.urlresolvers import local_site_reverse


class ReviewRequestDataGrid(DataGrid):
    """A datagrid that displays a list of review requests.

    This datagrid accepts the show_closed parameter in the URL, allowing
    submitted review requests to be filtered out or displayed.
    """
    my_comments = MyCommentsColumn()
    star = ReviewRequestStarColumn()
    ship_it = ShipItColumn()
    summary = SummaryColumn()
    submitter = SubmitterColumn()

    branch = Column(
        label=_('Branch'),
        db_field='branch',
        shrink=True,
        sortable=True,
        link=False)
    bugs_closed = BugsColumn()
    repository = RepositoryColumn()
    time_added = DateTimeColumn(
        label=_('Posted'),
        detailed_label=_('Posted Time'),
        format='F jS, Y, P',
        shrink=True,
        css_class=lambda r: ageid(r.time_added))
    last_updated = DateTimeColumn(
        label=_('Last Updated'),
        format='F jS, Y, P',
        shrink=True,
        db_field='last_updated',
        field_name='last_updated',
        css_class=lambda r: ageid(r.last_updated))
    diff_updated = DiffUpdatedColumn(
        format='F jS, Y, P',
        shrink=True,
        css_class=lambda r: ageid(r.diffset_history.last_diff_updated))
    time_added_since = DateTimeSinceColumn(
        label=_('Posted'),
        detailed_label=_('Posted Time (Relative)'),
        field_name='time_added', shrink=True,
        css_class=lambda r: ageid(r.time_added))
    last_updated_since = DateTimeSinceColumn(
        label=_('Last Updated'),
        detailed_label=_('Last Updated (Relative)'), shrink=True,
        db_field='last_updated',
        field_name='last_updated',
        css_class=lambda r: ageid(r.last_updated))
    diff_updated_since = DiffUpdatedSinceColumn(
        detailed_label=_('Diff Updated (Relative)'),
        shrink=True,
        css_class=lambda r: ageid(r.diffset_history.last_diff_updated))
    diff_size = DiffSizeColumn()

    review_count = ReviewCountColumn()

    target_groups = GroupsColumn()
    target_people = PeopleColumn()
    to_me = ToMeColumn()

    review_id = ReviewRequestIDColumn()

    def __init__(self, *args, **kwargs):
        self.local_site = kwargs.pop('local_site', None)

        super(ReviewRequestDataGrid, self).__init__(*args, **kwargs)

        self.listview_template = 'datagrids/review_request_listview.html'
        self.profile_sort_field = 'sort_review_request_columns'
        self.profile_columns_field = 'review_request_columns'
        self.show_closed = True
        self.submitter_url_name = 'user'
        self.default_sort = ['-last_updated']
        self.default_columns = [
            'star', 'summary', 'submitter', 'time_added', 'last_updated_since'
        ]

        # Add local timezone info to the columns
        user = self.request.user
        if user.is_authenticated():
            profile, is_new = Profile.objects.get_or_create(user=user)
            self.timezone = pytz.timezone(profile.timezone)
            self.time_added.timezone = self.timezone
            self.last_updated.timezone = self.timezone
            self.diff_updated.timezone = self.timezone

    def load_extra_state(self, profile, allow_hide_closed=True):
        if profile:
            self.show_closed = profile.show_closed

        try:
            self.show_closed = (
                int(self.request.GET.get('show-closed',
                                         self.show_closed))
                != 0)
        except ValueError:
            # do nothing
            pass

        if allow_hide_closed and not self.show_closed:
            self.queryset = self.queryset.filter(status='P')

        self.queryset = self.queryset.filter(local_site=self.local_site)

        if profile and self.show_closed != profile.show_closed:
            profile.show_closed = self.show_closed
            return True

        return False

    def post_process_queryset(self, queryset):
        q = queryset.with_counts(self.request.user)
        return super(ReviewRequestDataGrid, self).post_process_queryset(q)

    def link_to_object(self, state, obj, value):
        if value and isinstance(value, User):
            return local_site_reverse('user', request=self.request,
                                      args=[value])

        return obj.get_absolute_url()


class DashboardDataGrid(DataGridSidebarMixin, ReviewRequestDataGrid):
    """Displays the dashboard.

    The dashboard is the main place where users see what review requests
    are out there that may need their attention.
    """
    new_updates = NewUpdatesColumn()
    my_comments = MyCommentsColumn()
    selected = ReviewRequestCheckboxColumn()

    sidebar = Sidebar(
        [
            OutgoingSection,
            IncomingSection,
        ],
        default_view_id='incoming',
        css_classes=['scrollable'])

    def __init__(self, *args, **kwargs):
        local_site = kwargs.get('local_site', None)

        super(DashboardDataGrid, self).__init__(*args, **kwargs)

        self.listview_template = 'datagrid/listview.html'
        self.profile_sort_field = 'sort_dashboard_columns'
        self.profile_columns_field = 'dashboard_columns'
        self.default_view = 'incoming'
        self.show_closed = False
        self.default_sort = ['-last_updated']
        self.default_columns = [
            'selected', 'new_updates', 'ship_it', 'my_comments', 'summary',
            'submitter', 'last_updated_since'
        ]

        self.local_site = local_site
        self.user = self.request.user
        self.profile = Profile.objects.get_or_create(user=self.user)[0]
        self.site_profile = LocalSiteProfile.objects.get_or_create(
            user=self.user,
            local_site=local_site,
            profile=self.profile)[0]

    def load_extra_state(self, profile):
        group_name = self.request.GET.get('group', '')
        view = self.request.GET.get('view', self.default_view)
        user = self.request.user

        if view == 'outgoing':
            self.queryset = ReviewRequest.objects.from_user(
                user, user, local_site=self.local_site)
            self.title = _('All Outgoing Review Requests')
        elif view == 'mine':
            self.queryset = ReviewRequest.objects.from_user(
                user, user, None, local_site=self.local_site)
            self.title = _('All My Review Requests')
        elif view == 'to-me':
            self.queryset = ReviewRequest.objects.to_user_directly(
                user, user, local_site=self.local_site)
            self.title = _('Incoming Review Requests to Me')
        elif view in ('to-group', 'to-watched-group'):
            if group_name:
                # to-group is special because we want to make sure that the
                # group exists and show a 404 if it doesn't. Otherwise, we'll
                # show an empty datagrid with the name.
                try:
                    group = Group.objects.get(name=group_name,
                                              local_site=self.local_site)

                    if not group.is_accessible_by(user):
                        raise Http404
                except Group.DoesNotExist:
                    raise Http404

                self.queryset = ReviewRequest.objects.to_group(
                    group_name, self.local_site, user)
                self.title = _('Incoming Review Requests to %s') % group_name
            else:
                self.queryset = ReviewRequest.objects.to_user_groups(
                    user, user, local_site=self.local_site)
                self.title = _('All Incoming Review Requests to My Groups')
        elif view == 'starred':
            self.queryset = self.profile.starred_review_requests.public(
                user=user, local_site=self.local_site, status=None)
            self.title = _('Starred Review Requests')
        elif view == 'incoming':
            self.queryset = ReviewRequest.objects.to_user(
                user, user, local_site=self.local_site)
            self.title = _('All Incoming Review Requests')
        else:
            raise Http404

        return super(DashboardDataGrid, self).load_extra_state(
            profile, allow_hide_closed=False)


class UsersDataGrid(DataGrid):
    """A datagrid showing a list of users registered on Review Board."""
    username = Column(_('Username'), link=True, sortable=True)
    fullname = Column(_('Full Name'), field_name='get_full_name',
                      link=True, expand=True)
    pending_count = PendingCountColumn(_('Open Review Requests'),
                                       field_name='directed_review_requests',
                                       shrink=True)

    def __init__(self, request,
                 queryset=User.objects.filter(is_active=True),
                 title=_('All users'),
                 local_site=None):
        if local_site:
            qs = queryset.filter(local_site=local_site)
        else:
            qs = queryset

        super(UsersDataGrid, self).__init__(request, qs, title)

        self.default_sort = ['username']
        self.profile_sort_field = 'sort_submitter_columns'
        self.profile_columns_field = 'submitter_columns'
        self.default_columns = [
            'username', 'fullname', 'pending_count'
        ]

    def link_to_object(self, state, obj, value):
        return local_site_reverse('user', request=self.request,
                                  args=[obj.username])


class GroupDataGrid(DataGrid):
    """A datagrid showing a list of review groups accessible by the user."""
    star = ReviewGroupStarColumn()
    name = Column(_('Group ID'), link=True, sortable=True)
    displayname = Column(_('Group Name'), field_name='display_name',
                         link=True, expand=True)
    pending_count = PendingCountColumn(_('Open Review Requests'),
                                       field_name='review_requests',
                                       link=True,
                                       shrink=True)
    member_count = GroupMemberCountColumn(_('Members'),
                                          field_name='members',
                                          shrink=True)

    def __init__(self, request, title=_('All groups'), *args, **kwargs):
        local_site = kwargs.pop('local_site', None)
        queryset = Group.objects.accessible(request.user,
                                            local_site=local_site)

        super(GroupDataGrid, self).__init__(request, queryset=queryset,
                                            title=title, *args, **kwargs)

        self.profile_sort_field = 'sort_group_columns'
        self.profile_columns_field = 'group_columns'
        self.default_sort = ['name']
        self.default_columns = [
            'star', 'name', 'displayname', 'pending_count'
        ]

    @staticmethod
    def link_to_object(state, obj, value):
        return obj.get_absolute_url()


class UserPageDataGrid(DataGridSidebarMixin, ReviewRequestDataGrid):
    """A data grid for the user's page.

    This will show the review requests the user has out for review, and
    display information about the user on the side.
    """
    sidebar = Sidebar([
        UserProfileItem,
        UserGroupsItem,
    ])

    def __init__(self, request, user, *args, **kwargs):
        queryset = ReviewRequest.objects.from_user(
            user.username,
            user=request.user,
            status=None,
            with_counts=True,
            local_site=kwargs.get('local_site'),
            filter_private=True,
            show_inactive=True)

        super(UserPageDataGrid, self).__init__(
            request,
            queryset=queryset,
            title=_("%s's review requests") % user.username,
            *args, **kwargs)

        self.groups = user.review_groups.accessible(request.user)
        self.user = user
