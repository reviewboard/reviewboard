from __future__ import unicode_literals

import pytz

from django.contrib.auth.models import User
from django.http import Http404
from django.utils.translation import ugettext_lazy as _
from djblets.datagrid.grids import (
    Column,
    DateTimeColumn,
    DataGrid as DjbletsDataGrid,
    AlphanumericDataGrid as DjbletsAlphanumericDataGrid)
from djblets.util.templatetags.djblets_utils import ageid

from reviewboard.accounts.models import (LocalSiteProfile, Profile,
                                         ReviewRequestVisit)
from reviewboard.datagrids.columns import (BugsColumn,
                                           DateTimeSinceColumn,
                                           DiffSizeColumn,
                                           DiffUpdatedColumn,
                                           DiffUpdatedSinceColumn,
                                           FullNameColumn,
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
                                           ReviewSummaryColumn,
                                           ShipItColumn,
                                           SummaryColumn,
                                           ToMeColumn,
                                           UsernameColumn)
from reviewboard.datagrids.sidebar import Sidebar, DataGridSidebarMixin
from reviewboard.datagrids.builtin_items import (IncomingSection,
                                                 OutgoingSection,
                                                 OverviewSection,
                                                 UserGroupsItem,
                                                 UserProfileItem)
from reviewboard.reviews.models import Group, ReviewRequest, Review
from reviewboard.site.urlresolvers import local_site_reverse


class ShowClosedReviewRequestsMixin(object):
    """A mixin for showing or hiding closed review requests."""

    def load_extra_state(self, profile, allow_hide_closed=True):
        """Load extra state for the datagrid."""
        if profile:
            self.show_closed = profile.show_closed

        try:
            self.show_closed = (
                int(self.request.GET.get('show-closed',
                                         self.show_closed)) != 0)
        except ValueError:
            # do nothing
            pass

        if allow_hide_closed and not self.show_closed:
            self.queryset = self.queryset.filter(**{
                self.status_query_field: 'P',
            })

        self.queryset = self.queryset.filter(**{
            self.site_query_field: self.local_site,
        })

        if profile and self.show_closed != profile.show_closed:
            profile.show_closed = self.show_closed
            return True

        return False


class DataGridJSMixin(object):
    """Mixin that provides enhanced JavaScript support for datagrids.

    This contains additional information on the JavaScript views/models
    to load for the page, allowing for enhanced functionality in datagrids.
    """

    #: A list of extra CSS static bundles to load on the page.
    css_bundle_names = []

    #: A list of extra JavaScript static bundles to load on the page.
    js_bundle_names = []

    #: The JavaScript Model to use for the page state.
    js_model_class = 'RB.DatagridPage'

    #: The JavaScript View to use for the page rendering.
    js_view_class = 'RB.DatagridPageView'

    #: Whether or not to periodically reload the contents of the datagrid.
    periodic_reload = False

    #: Extra data to pass to the JavaScript Model.
    extra_js_model_data = None

    def __init__(self, *args, **kwargs):
        """Initialize the mixin.

        This will pull out the Local Site, which is common to all datagrids,
        and store it for later use and for JavaScript attribute population.

        Args:
            *args (tuple):
                Positional arguments passed to the datagrid.

            **kwargs (dict):
                Keyword arguments passed to the datagrid.
        """
        self.local_site = kwargs.pop('local_site', None)

        super(DataGridJSMixin, self).__init__(*args, **kwargs)

    def get_js_model_attrs(self):
        """Return attributes for the JavaScript model.

        These will be passed to the model specified in
        :py:attr:`js_model_class` during construction.

        Subclasses can override this to provide additional data.

        Returns:
            dict:
            Attributes to provide to the JavaScript model.
        """
        attrs = {}

        if self.extra_js_model_data:
            attrs['data'] = self.extra_js_model_data

        if self.local_site:
            attrs['localSiteName'] = self.local_site.name

        return attrs

    def get_js_model_options(self):
        """Return options for the JavaScript model.

        These will be passed to the model specified in
        :py:attr:`js_model_class` during construction.

        Subclasses can override this to provide additional data.

        Returns:
            dict:
            Options to provide to the JavaScript model.
        """
        return {}

    def get_js_view_options(self):
        """Return options for the JavaScript view.

        These will be passed to the view specified in
        :py:attr:`js_view_class` during construction.

        Subclasses can override this to provide additional data.

        Returns:
            dict:
            Options to provide to the JavaScript view.
        """
        return {
            'periodicReload': self.periodic_reload,
        }


class DataGrid(DataGridJSMixin, DjbletsDataGrid):
    """Base class for a datagrid in Review Board.

    This contains additional information on JavaScript views/models
    to load for the page.
    """


class AlphanumericDataGrid(DataGridJSMixin, DjbletsAlphanumericDataGrid):
    """Base class for an alphanumeric datagrid in Review Board.

    This contains additional information on JavaScript views/models
    to load for the page.
    """


class ReviewRequestDataGrid(ShowClosedReviewRequestsMixin, DataGrid):
    """A datagrid that displays a list of review requests.

    This datagrid accepts the show_closed parameter in the URL, allowing
    submitted review requests to be filtered out or displayed.
    """

    new_updates = NewUpdatesColumn()
    my_comments = MyCommentsColumn()
    star = ReviewRequestStarColumn()
    ship_it = ShipItColumn()
    summary = SummaryColumn()
    submitter = UsernameColumn(label=_('Owner'),
                               user_relation=['submitter'])

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

    status_query_field = 'status'
    site_query_field = 'local_site'

    def __init__(self, *args, **kwargs):
        """Initialize the datagrid."""
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

        # Add local timezone info to the columns.
        user = self.request.user

        if user.is_authenticated():
            profile = user.get_profile()
            self.timezone = pytz.timezone(profile.timezone)
            self.time_added.timezone = self.timezone
            self.last_updated.timezone = self.timezone
            self.diff_updated.timezone = self.timezone

    def load_extra_state(self, profile, allow_hide_closed=True):
        """Load extra state for the datagrid."""
        return super(ReviewRequestDataGrid, self).load_extra_state(
            profile, allow_hide_closed)

    def post_process_queryset(self, queryset):
        """Add additional data to the queryset."""
        q = queryset.with_counts(self.request.user)
        return super(ReviewRequestDataGrid, self).post_process_queryset(q)

    def link_to_object(self, state, obj, value):
        """Return a link to the given object."""
        if value and isinstance(value, User):
            return local_site_reverse('user', request=self.request,
                                      args=[value])

        return obj.get_absolute_url()


class ReviewDataGrid(ShowClosedReviewRequestsMixin, DataGrid):
    """A datagrid that displays a list of reviews.

    This datagrid accepts the show_closed parameter in the URL, allowing
    submitted review requests to be filtered out or displayed.
    """

    timestamp = DateTimeColumn(
        label=_('Date Reviewed'),
        format='F jS, Y',
        shrink=True)
    submitter = UsernameColumn(label=_('Owner'),
                               user_relation=['review_request', 'submitter'])
    review_summary = ReviewSummaryColumn()

    status_query_field = 'review_request__status'
    site_query_field = 'review_request__local_site'

    def __init__(self, *args, **kwargs):
        """Initialize the datagrid."""
        super(ReviewDataGrid, self).__init__(*args, **kwargs)

        self.listview_template = 'datagrids/review_request_listview.html'
        self.profile_columns_field = 'review_columns'
        self.show_closed = True
        self.default_sort = ['-timestamp']
        self.default_columns = [
           'submitter', 'review_summary', 'timestamp',
        ]

        # Add local timezone info to the columns.
        user = self.request.user

        if user.is_authenticated():
            profile = user.get_profile()
            self.timezone = pytz.timezone(profile.timezone)
            self.timestamp.timezone = self.timezone


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
            OverviewSection,
            OutgoingSection,
            IncomingSection,
        ],
        default_view_id='incoming')

    js_model_class = 'RB.Dashboard'
    js_view_class = 'RB.DashboardView'
    periodic_reload = True

    def __init__(self, *args, **kwargs):
        """Initialize the datagrid."""
        super(DashboardDataGrid, self).__init__(*args, **kwargs)

        self.listview_template = 'datagrids/hideable_listview.html'
        self.profile_sort_field = 'sort_dashboard_columns'
        self.profile_columns_field = 'dashboard_columns'
        self.default_view = 'incoming'
        self.show_closed = False
        self.show_archived = False
        self.default_sort = ['-last_updated']
        self.default_columns = [
            'selected', 'new_updates', 'ship_it', 'my_comments', 'summary',
            'submitter', 'last_updated_since'
        ]

        self.extra_js_model_data = {
            'show_archived': self.show_archived,
        }

        self.user = self.request.user
        self.profile = self.user.get_profile()
        self.site_profile = self.user.get_site_profile(self.local_site)

    def load_extra_state(self, profile):
        """Load extra state for the datagrid."""
        group_name = self.request.GET.get('group', '')
        view = self.request.GET.get('view', self.default_view)
        user = self.request.user

        if view == 'outgoing':
            self.queryset = ReviewRequest.objects.from_user(
                user, user, local_site=self.local_site)
            self.title = _('All Outgoing Review Requests')
        elif view == 'overview':
            self.queryset = ReviewRequest.objects.to_or_from_user(
                user, user, local_site=self.local_site)
            self.title = _('Open Incoming and Outgoing Review Requests')
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

        if profile and 'show_archived' in profile.extra_data:
            self.show_archived = profile.extra_data['show_archived']

        try:
            show = self.request.GET.get('show-archived', self.show_archived)
            self.show_archived = int(show) != 0
        except ValueError:
            pass

        if not self.show_archived:
            hidden_q = ReviewRequestVisit.objects.filter(
                user=user).exclude(visibility=ReviewRequestVisit.VISIBLE)
            hidden_q = hidden_q.values_list('review_request_id', flat=True)

            self.queryset = self.queryset.exclude(pk__in=hidden_q)

        if (profile and
            self.show_archived != profile.extra_data.get('show_archived')):
            profile.extra_data['show_archived'] = self.show_archived
            profile_changed = True
        else:
            profile_changed = False

        self.extra_js_model_data['show_archived'] = self.show_archived

        parent_profile_changed = \
            super(DashboardDataGrid, self).load_extra_state(
                profile, allow_hide_closed=False)

        return profile_changed or parent_profile_changed


class UsersDataGrid(AlphanumericDataGrid):
    """A datagrid showing a list of users registered on Review Board."""

    username = UsernameColumn(label=_('Username'))
    fullname = FullNameColumn(label=_('Full Name'), link=True, expand=True)
    pending_count = PendingCountColumn(_('Open Review Requests'),
                                       field_name='directed_review_requests',
                                       shrink=True)

    def __init__(self, request,
                 queryset=User.objects.all(),
                 title=_('All users'),
                 local_site=None):
        """Initialize the datagrid."""
        if local_site:
            qs = queryset.filter(local_site=local_site)
        else:
            qs = queryset

        super(UsersDataGrid, self).__init__(request, qs, title=title,
                                            sortable_column='username',
                                            extra_regex='^[0-9_\-\.].*')

        self.listview_template = 'datagrids/user_listview.html'
        self.default_sort = ['username']
        self.profile_sort_field = 'sort_submitter_columns'
        self.profile_columns_field = 'submitter_columns'
        self.default_columns = [
            'username', 'fullname', 'pending_count'
        ]
        self.show_inactive = False

    def link_to_object(self, state, obj, value):
        """Return a link to the given object."""
        return local_site_reverse('user', request=self.request,
                                  args=[obj.username])

    def load_extra_state(self, profile):
        """Load extra state for the datagrid.

        This handles hiding or showing inactive users.

        Args:
            profile (reviewboard.accounts.models.Profile):
                The user profile which contains some basic
                configurable settings.

        Returns:
            bool:
            Always returns False.
        """
        show_inactive = self.request.GET.get('show-inactive', 0)

        try:
            self.show_inactive = int(show_inactive)
        except ValueError:
            pass

        if not self.show_inactive:
            self.queryset = self.queryset.filter(is_active=True)

        return False


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
        """Initialize the datagrid."""
        local_site = kwargs.get('local_site')
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
        """Return a link to the given object."""
        return obj.get_absolute_url()


class UserPageDataGridMixin(DataGridSidebarMixin):
    """An abstract class for data grids on the user page.

    This will display information about the user on the side.
    """

    sidebar = Sidebar([
        UserProfileItem,
        UserGroupsItem,
    ])


class UserPageReviewRequestDataGrid(UserPageDataGridMixin,
                                    ReviewRequestDataGrid):
    """A data grid for the user page.

    This will show the review requests the user has out for review.
    """

    tab_title = _('Review Requests')

    def __init__(self, request, user, *args, **kwargs):
        """Initialize the datagrid."""
        queryset = ReviewRequest.objects.from_user(
            user.username,
            user=request.user,
            status=None,
            with_counts=True,
            local_site=kwargs.get('local_site'),
            filter_private=True,
            show_inactive=True)

        super(UserPageReviewRequestDataGrid, self).__init__(
            request,
            queryset=queryset,
            title=_("%s's Review Requests") % user.username,
            extra_context={
                'pii_safe_title': _("User's Review Requests"),
            },
            *args, **kwargs)

        self.groups = user.review_groups.accessible(request.user)
        self.user = user


class UserPageReviewsDataGrid(UserPageDataGridMixin, ReviewDataGrid):
    """A data grid for the user page.

    This will show reviews the user has made on other review requests.
    """

    tab_title = _('Reviews')

    def __init__(self, request, user, *args, **kwargs):
        """Initialize the datagrid."""
        queryset = Review.objects.from_user(
            user.username,
            user=request.user,
            public=True,
            filter_private=True,
            status=None,
            local_site=kwargs.get('local_site'))

        super(UserPageReviewsDataGrid, self).__init__(
            request,
            queryset=queryset,
            title=_("%s's Reviews") % user.username,
            extra_context={
                'pii_safe_title': _("User's Reviews"),
            },
            *args, **kwargs)

        self.groups = user.review_groups.accessible(request.user)
        self.user = user
