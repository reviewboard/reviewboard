import pytz

from django.contrib.auth.models import User
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.http import Http404
from django.template.defaultfilters import date
from django.utils.datastructures import SortedDict
from django.utils.html import conditional_escape
from django.utils.translation import ugettext_lazy as _
from djblets.datagrid.grids import Column, DateTimeColumn, DataGrid
from djblets.util.templatetags.djblets_utils import ageid

from reviewboard.accounts.models import Profile
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.reviews.templatetags.reviewtags import render_star
from reviewboard.site.urlresolvers import local_site_reverse


class DateTimeSinceColumn(DateTimeColumn):
    """A column that displays how long it has been since a date/time.

    These columns will dynamically update as the page is shown, so that the
    number of minutes, hours, days, etc. ago is correct.
    """
    def render_data(self, obj):
        return '<time class="timesince" datetime="%s">%s</time>' % (
            date(getattr(obj, self.field_name), 'c'),
            super(DateTimeSinceColumn, self).render_data(obj))


class StarColumn(Column):
    """
    A column used to indicate whether the object is "starred" or watched.
    The star is interactive, allowing the user to star or unstar the object.
    """
    def __init__(self, *args, **kwargs):
        Column.__init__(self, *args, **kwargs)
        self.image_url = static("rb/images/star_on.png")
        self.image_width = 16
        self.image_height = 15
        self.image_alt = _("Starred")
        self.detailed_label = _("Starred")
        self.shrink = True
        self.all_starred = {}

    def render_data(self, obj):
        obj.starred = self.all_starred.get(obj.id, False)
        return render_star(self.datagrid.request.user, obj)


class ReviewGroupStarColumn(StarColumn):
    """
    A specialization of StarColumn that augments the SQL query to include
    the starred calculation for review groups.
    """
    def augment_queryset(self, queryset):
        user = self.datagrid.request.user

        if user.is_anonymous():
            return queryset

        try:
            profile = user.get_profile()
        except Profile.DoesNotExist:
            return queryset

        pks = profile.starred_groups.filter(
            pk__in=self.datagrid.id_list).values_list('pk', flat=True)

        self.all_starred = {}

        for pk in pks:
            self.all_starred[pk] = True

        return queryset


class ReviewRequestStarColumn(StarColumn):
    """
    A specialization of StarColumn that augments the SQL query to include
    the starred calculation for review requests.
    """
    def augment_queryset(self, queryset):
        user = self.datagrid.request.user

        if user.is_anonymous():
            return queryset

        try:
            profile = user.get_profile()
        except Profile.DoesNotExist:
            return queryset

        pks = profile.starred_review_requests.filter(
            pk__in=self.datagrid.id_list).values_list('pk', flat=True)

        self.all_starred = {}

        for pk in pks:
            self.all_starred[pk] = True

        return queryset


class ShipItColumn(Column):
    """
    A column used to indicate whether someone has marked this review request
    as "Ship It!"
    """
    def __init__(self, *args, **kwargs):
        Column.__init__(self, *args, **kwargs)
        self.image_url = static("rb/images/shipit.png")
        self.image_width = 16
        self.image_height = 16
        self.image_alt = _("Ship It!")
        self.detailed_label = _("Ship It!")
        self.db_field = "shipit_count"
        self.sortable = True
        self.shrink = True

    def render_data(self, review_request):
        if review_request.shipit_count > 0:
            return '<span class="shipit-count">' \
                    '<img src="%s" width="9" height="8" alt="%s" ' \
                         'title="%s" /> %s' \
                   '</span>' % \
                (static("rb/images/shipit_checkmark.png"),
                 self.image_alt, self.image_alt, review_request.shipit_count)

        return ""


class MyCommentsColumn(Column):
    """
    A column meant to represent the status of the logged-in user's
    comments on the review.
    """
    def __init__(self, *args, **kwargs):
        Column.__init__(self, *args, **kwargs)
        self.image_url = static("rb/images/comment-draft-small.png")
        self.image_width = 16
        self.image_height = 16
        self.image_alt = _("My Comments")
        self.detailed_label = _("My Comments")
        self.shrink = True

        # XXX It'd be nice to be able to sort on this, but datagrids currently
        # can only sort based on stored (in the DB) values, not computed values.

    def augment_queryset(self, queryset):
        user = self.datagrid.request.user

        if user.is_anonymous():
            return queryset

        query_dict = {
            'user_id': str(user.id),
        }

        return queryset.extra(select={
            'mycomments_my_reviews': """
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = %(user_id)s
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
            """ % query_dict,
            'mycomments_private_reviews': """
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = %(user_id)s
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND NOT reviews_review.public
            """ % query_dict,
            'mycomments_shipit_reviews': """
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = %(user_id)s
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND reviews_review.ship_it
            """ % query_dict,
        })

    def render_data(self, review_request):
        user = self.datagrid.request.user

        if user.is_anonymous() or review_request.mycomments_my_reviews == 0:
            return ""

        image_url = None
        image_alt = None

        # Priority is ranked in the following order:
        #
        # 1) Non-public (draft) reviews
        # 2) Public reviews marked "Ship It"
        # 3) Public reviews not marked "Ship It"
        if review_request.mycomments_private_reviews > 0:
            image_url = self.image_url
            image_alt = _("Comments drafted")
        else:
            if review_request.mycomments_shipit_reviews > 0:
                image_url = static("rb/images/comment-shipit-small.png")
                image_alt = _("Comments published. Ship it!")
            else:
                image_url = static("rb/images/comment-small.png")
                image_alt = _("Comments published")

        return '<img src="%s" width="%s" height="%s" alt="%s" ' \
               'title="%s" />' % \
                (image_url, self.image_width, self.image_height,
                 image_alt, image_alt)


class ToMeColumn(Column):
    """
    A column used to indicate whether the current logged-in user is targeted
    by the review request.
    """
    def __init__(self, *args, **kwargs):
        Column.__init__(self, *args, **kwargs)
        self.label = u"\u00BB"  # this is &raquo;
        self.detailed_label = u"\u00BB To Me"
        self.shrink = True

    def render_data(self, review_request):
        user = self.datagrid.request.user
        if (user.is_authenticated() and
            review_request.target_people.filter(pk=user.pk).exists()):
            return '<div title="%s"><b>&raquo;</b></div>' % \
                    (self.detailed_label)

        return ""


class NewUpdatesColumn(Column):
    """
    A column used to indicate whether the review request has any new updates
    since the user last saw it.
    """
    def __init__(self, *args, **kwargs):
        Column.__init__(self, *args, **kwargs)
        self.image_url = static("rb/images/convo.png")
        self.image_width = 18
        self.image_height = 16
        self.image_alt = "New Updates"
        self.detailed_label = "New Updates"
        self.shrink = True

    def render_data(self, review_request):
        if review_request.new_review_count > 0:
            return '<img src="%s" width="%s" height="%s" alt="%s" ' \
                   'title="%s" />' % \
                (self.image_url, self.image_width, self.image_height,
                 self.image_alt, self.image_alt)

        return ""


class SummaryColumn(Column):
    """
    A column used to display a summary of the review request, along with
    labels indicating if it's a draft or if it's submitted.
    """
    def __init__(self, label=_("Summary"), *args, **kwargs):
        Column.__init__(self, label=label, *args, **kwargs)
        self.sortable = True

    def augment_queryset(self, queryset):
        user = self.datagrid.request.user

        if user.is_anonymous():
            return queryset

        return queryset.extra(select={
            'draft_summary': """
                SELECT reviews_reviewrequestdraft.summary
                  FROM reviews_reviewrequestdraft
                  WHERE reviews_reviewrequestdraft.review_request_id =
                        reviews_reviewrequest.id
            """
        })

    def render_data(self, review_request):
        summary = conditional_escape(review_request.summary)
        labels = {}

        if not summary:
            summary = '&nbsp;<i>%s</i>' % _('No Summary')

        if review_request.submitter_id == self.datagrid.request.user.id:

            if review_request.draft_summary is not None:
                summary = conditional_escape(review_request.draft_summary)
                labels.update({_('Draft'):  'label-draft'})
            elif (not review_request.public and
                  review_request.status == ReviewRequest.PENDING_REVIEW):
                labels.update({_('Draft'): 'label-draft'})

        if review_request.status == ReviewRequest.SUBMITTED:
            labels.update({_('Submitted'): 'label-submitted'})
        elif review_request.status == ReviewRequest.DISCARDED:
            labels.update({_('Discarded'): 'label-discarded'})

        display_data = ''

        for label in labels:
           display_data += u'<span class="%s">[%s] </span>' % (
               labels[label], label)
        display_data += u'%s' % summary
        return display_data


class SubmitterColumn(Column):
    def __init__(self, *args, **kwargs):
        Column.__init__(self, _("Submitter"), db_field="submitter__username",
                        shrink=True, sortable=True, link=True,
                        *args, **kwargs)

    def augment_queryset(self, queryset):
        return queryset.select_related('submitter')


class RepositoryColumn(Column):
    def __init__(self, *args, **kwargs):
        Column.__init__(self, _("Repository"), db_field="repository__name",
                        shrink=True, sortable=True, link=False,
                        css_class='repository-column',
                        *args, **kwargs)

    def augment_queryset(self, queryset):
        return queryset.select_related('repository')


class PendingCountColumn(Column):
    """
    A column used to show the pending number of review requests for a
    group or user.
    """
    def __init__(self, *args, **kwargs):
        Column.__init__(self, *args, **kwargs)

    def render_data(self, obj):
        return str(getattr(obj, self.field_name).filter(public=True,
                                                        status='P').count())


class PeopleColumn(Column):
    def __init__(self, *args, **kwargs):
        Column.__init__(self, *args, **kwargs)
        self.label = _("People")
        self.detailed_label = _("Target People")
        self.sortable = False
        self.shrink = False

    def render_data(self, review_request):
        people = review_request.target_people.all()
        return reduce(lambda a, d: a + d.username + ' ', people, '')


class GroupsColumn(Column):
    def __init__(self, *args, **kwargs):
        Column.__init__(self, *args, **kwargs)
        self.label = _("Groups")
        self.detailed_label = _("Target Groups")
        self.sortable = False
        self.shrink = False

    def render_data(self, review_request):
        groups = review_request.target_groups.all()
        return reduce(lambda a, d: a + d.name + ' ', groups, '')


class GroupMemberCountColumn(Column):
    """
    A column used to show the number of users that registered for a group.
    """
    def __init__(self, *args, **kwargs):
        Column.__init__(self, *args, **kwargs)
        self.link = True
        self.link_func = self.link_to_object

    def render_data(self, group):
        return str(group.users.count())

    def link_to_object(self, group, value):
        return local_site_reverse('group_members',
                                  request=self.datagrid.request,
                                  args=[group.name])


class ReviewCountColumn(Column):
    """
    A column showing the number of reviews for a review request.
    """
    def __init__(self, label=_("Reviews"),
                 detailed_label=_("Number of Reviews"),
                 *args, **kwargs):
        Column.__init__(self, label=label, detailed_label=detailed_label,
                        *kwargs, **kwargs)
        self.shrink = True
        self.link = True
        self.link_func = self.link_to_object

    def render_data(self, review_request):
        return str(review_request.publicreviewcount_count)

    def augment_queryset(self, queryset):
        return queryset.extra(select={
            'publicreviewcount_count': """
                SELECT COUNT(*)
                  FROM reviews_review
                  WHERE reviews_review.public
                    AND reviews_review.base_reply_to_id is NULL
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
            """
        })

    def link_to_object(self, review_request, value):
        return "%s#last-review" % review_request.get_absolute_url()


class DiffUpdatedColumn(DateTimeColumn):
    """A column indicating the date and time the diff was last updated."""
    def __init__(self, *args, **kwargs):
        super(DiffUpdatedColumn, self).__init__(
            _("Diff Updated"),
            db_field="diffset_history__last_diff_updated",
            field_name='last_diff_updated',
            sortable=True,
            link=False,
            *args, **kwargs)

    def augment_queryset(self, queryset):
        return queryset.select_related('diffset_history')

    def render_data(self, obj):
        if obj.diffset_history.last_diff_updated:
            return super(DiffUpdatedColumn, self).render_data(
                obj.diffset_history)
        else:
            return ""


class DiffUpdatedSinceColumn(DateTimeSinceColumn):
    """A column indicating the elapsed time since the diff was last updated."""
    def __init__(self, *args, **kwargs):
        super(DiffUpdatedSinceColumn, self).__init__(
            _("Diff Updated"),
            db_field="diffset_history__last_diff_updated",
            field_name='last_diff_updated',
            sortable=True,
            link=False,
            *args, **kwargs)

    def augment_queryset(self, queryset):
        return queryset.select_related('diffset_history')

    def render_data(self, obj):
        if obj.diffset_history.last_diff_updated:
            return DateTimeSinceColumn.render_data(self, obj.diffset_history)
        else:
            return ""


class ReviewRequestDataGrid(DataGrid):
    """
    A datagrid that displays a list of review requests.

    This datagrid accepts the show_submitted parameter in the URL, allowing
    submitted review requests to be filtered out or displayed.
    """
    my_comments  = MyCommentsColumn()
    star         = ReviewRequestStarColumn()
    ship_it      = ShipItColumn()
    summary      = SummaryColumn(expand=True, link=True, css_class="summary")
    submitter    = SubmitterColumn()

    branch       = Column(_("Branch"), db_field="branch",
                          shrink=True, sortable=True, link=False)
    bugs_closed  = Column(_("Bugs"), db_field="bugs_closed",
                          shrink=True, sortable=False, link=False)
    repository   = RepositoryColumn()
    time_added   = DateTimeColumn(_("Posted"),
        detailed_label=_("Posted Time"),
        format="F jS, Y, P", shrink=True,
        css_class=lambda r: ageid(r.time_added))
    last_updated = DateTimeColumn(_("Last Updated"),
        format="F jS, Y, P", shrink=True,
        db_field="last_updated",
        field_name="last_updated",
        css_class=lambda r: ageid(r.last_updated))
    diff_updated = DiffUpdatedColumn(
        format="F jS, Y, P", shrink=True,
        css_class=lambda r: ageid(r.diffset_history.last_diff_updated))
    time_added_since = DateTimeSinceColumn(_("Posted"),
        detailed_label=_("Posted Time (Relative)"),
        field_name="time_added", shrink=True,
        css_class=lambda r: ageid(r.time_added))
    last_updated_since = DateTimeSinceColumn(_("Last Updated"),
        detailed_label=_("Last Updated (Relative)"), shrink=True,
        db_field="last_updated",
        field_name="last_updated",
        css_class=lambda r: ageid(r.last_updated))
    diff_updated_since = DiffUpdatedSinceColumn(
        detailed_label=_("Diff Updated (Relative)"),
        shrink=True,
        css_class=lambda r: ageid(r.diffset_history.last_diff_updated))

    review_count = ReviewCountColumn()

    target_groups = GroupsColumn()
    target_people = PeopleColumn()
    to_me = ToMeColumn()

    review_id = Column(_("Review ID"),
                       shrink=True, sortable=True, link=True)

    def __init__(self, *args, **kwargs):
        self.local_site = kwargs.pop('local_site', None)

        if self.local_site:
            review_id_field = 'local_id'
        else:
            review_id_field = 'pk'

        self.review_id = Column(_("Review ID"),
                                field_name=review_id_field,
                                shrink=True, sortable=True, link=True)

        DataGrid.__init__(self, *args, **kwargs)
        self.listview_template = 'reviews/review_request_listview.html'
        self.profile_sort_field = 'sort_review_request_columns'
        self.profile_columns_field = 'review_request_columns'
        self.show_submitted = True
        self.submitter_url_name = "user"
        self.default_sort = ["-last_updated"]
        self.default_columns = [
            "star", "summary", "submitter", "time_added", "last_updated_since"
        ]

        # Add local timezone info to the columns
        user = self.request.user
        if user.is_authenticated():
            self.timezone = pytz.timezone(user.get_profile().timezone)
            self.time_added.timezone = self.timezone
            self.last_updated.timezone = self.timezone
            self.diff_updated.timezone = self.timezone

    def load_extra_state(self, profile):
        if profile:
            self.show_submitted = profile.show_submitted

        try:
            self.show_submitted = \
                int(self.request.GET.get('show_submitted',
                                     self.show_submitted)) != 0
        except ValueError:
            # do nothing
            pass

        if self.show_submitted:
            # There are only three states: Published, Submitted and Discarded.
            # We want the first two, but it's faster to just search for not
            # discarded.
            self.queryset = self.queryset.exclude(status='D')
        else:
            self.queryset = self.queryset.filter(status='P')

        self.queryset = self.queryset.filter(local_site=self.local_site)

        if profile and self.show_submitted != profile.show_submitted:
            profile.show_submitted = self.show_submitted
            return True

        return False

    def post_process_queryset(self, queryset):
        q = queryset.with_counts(self.request.user)
        return super(ReviewRequestDataGrid, self).post_process_queryset(q)

    def link_to_object(self, obj, value):
        if value and isinstance(value, User):
            return local_site_reverse("user", request=self.request,
                                      args=[value])

        return obj.get_absolute_url()


class DashboardDataGrid(ReviewRequestDataGrid):
    """
    A version of the ReviewRequestDataGrid that displays additional fields
    useful in the dashboard. It also displays a different set of data
    depending on the view that was passed.
    """
    new_updates = NewUpdatesColumn()
    my_comments = MyCommentsColumn()

    def __init__(self, *args, **kwargs):
        local_site = kwargs.pop('local_site', None)
        ReviewRequestDataGrid.__init__(self, *args, **kwargs)
        self.listview_template = 'datagrid/listview.html'
        self.profile_sort_field = 'sort_dashboard_columns'
        self.profile_columns_field = 'dashboard_columns'
        self.default_view = "incoming"
        self.show_submitted = False
        self.default_sort = ["-last_updated"]
        self.default_columns = [
            "new_updates", "star", "summary", "submitter",
            "time_added", "last_updated_since"
        ]
        self.counts = {}

        group = self.request.GET.get('group', None)
        view = self.request.GET.get('view', None)
        extra_query = []

        if view:
            extra_query.append("view=%s" % view)

        if group:
            extra_query.append("group=%s" % group)

        self.extra_context['extra_query'] = "&".join(extra_query)
        self.local_site = local_site

    def load_extra_state(self, profile):
        group = self.request.GET.get('group', '')
        view = self.request.GET.get('view', self.default_view)
        user = self.request.user

        if view == 'outgoing':
            self.queryset = ReviewRequest.objects.from_user(
                user, user, local_site=self.local_site)
            self.title = _(u"All Outgoing Review Requests")
        elif view == 'mine':
            self.queryset = ReviewRequest.objects.from_user(
                user, user, None, local_site=self.local_site)
            self.title = _(u"All My Review Requests")
        elif view == 'to-me':
            self.queryset = ReviewRequest.objects.to_user_directly(
                user, user, local_site=self.local_site)
            self.title = _(u"Incoming Review Requests to Me")
        elif view == 'to-group':
            if group != "":
                # to-group is special because we want to make sure that the
                # group exists and show a 404 if it doesn't. Otherwise, we'll
                # show an empty datagrid with the name.
                has_groups = Group.objects.filter(
                    name=group,
                    local_site=self.local_site).exists()

                if not has_groups:
                    raise Http404

                self.queryset = ReviewRequest.objects.to_group(
                    group, self.local_site, user)
                self.title = _(u"Incoming Review Requests to %s") % group
            else:
                self.queryset = ReviewRequest.objects.to_user_groups(
                    user, user, local_site=self.local_site)
                self.title = _(u"All Incoming Review Requests to My Groups")
        elif view == 'starred':
            profile = user.get_profile()
            self.queryset = profile.starred_review_requests.public(
                user, local_site=self.local_site)
            self.title = _(u"Starred Review Requests")
        elif view == 'incoming':
            self.queryset = ReviewRequest.objects.to_user(
                user, user, local_site=self.local_site)
            self.title = _(u"All Incoming Review Requests")
        else:
            raise Http404

        # Pre-load all querysets for the sidebar.
        self.counts = get_sidebar_counts(user, self.local_site)

        return False


class SubmitterDataGrid(DataGrid):
    """
    A datagrid showing a list of submitters.
    """
    username      = Column(_("Username"), link=True, sortable=True)
    fullname      = Column(_("Full Name"), field_name="get_full_name",
                           link=True, expand=True)
    pending_count = PendingCountColumn(_("Pending Reviews"),
                                       field_name="directed_review_requests",
                                       shrink=True)

    def __init__(self, request,
                 queryset=User.objects.filter(is_active=True),
                 title=_("All submitters"),
                 local_site=None):
        if local_site:
            qs = queryset.filter(local_site=local_site)
        else:
            qs = queryset

        DataGrid.__init__(self, request, qs, title)
        self.default_sort = ["username"]
        self.profile_sort_field = 'sort_submitter_columns'
        self.profile_columns_field = 'submitter_columns'
        self.default_columns = [
            "username", "fullname", "pending_count"
        ]

    def link_to_object(self, obj, value):
        return local_site_reverse("user", request=self.request,
                                  args=[obj.username])


class GroupDataGrid(DataGrid):
    """
    A datagrid showing a list of review groups.
    """
    star          = ReviewGroupStarColumn()
    name          = Column(_("Group ID"), link=True, sortable=True)
    displayname   = Column(_("Group Name"), field_name="display_name",
                           link=True, expand=True)
    pending_count = PendingCountColumn(_("Pending Reviews"),
                                       field_name="review_requests",
                                       link=True,
                                       shrink=True)
    member_count  = GroupMemberCountColumn(_("Members"),
                                           field_name="members",
                                           shrink=True)

    def __init__(self, request, title=_("All groups"), *args, **kwargs):
        local_site = kwargs.pop('local_site', None)
        queryset = Group.objects.accessible(request.user, local_site=local_site)

        DataGrid.__init__(self, request, queryset=queryset, title=title,
                          *args, **kwargs)
        self.profile_sort_field = 'sort_group_columns'
        self.profile_columns_field = 'group_columns'
        self.default_sort = ["name"]
        self.default_columns = [
            "star", "name", "displayname", "pending_count"
        ]

    @staticmethod
    def link_to_object(obj, value):
        return obj.get_absolute_url()


class WatchedGroupDataGrid(GroupDataGrid):
    """
    A special version of GroupDataGrid that shows a list of watched groups,
    linking to a dashboard view of them. This is meant for display in the
    dashboard.
    """
    def __init__(self, request, title=_("Watched groups"), *args, **kwargs):
        local_site = kwargs.pop('local_site', None)
        GroupDataGrid.__init__(self, request, title=title, *args, **kwargs)
        user = request.user
        profile = user.get_profile()

        self.queryset = profile.starred_groups.all()
        self.queryset = self.queryset.filter(local_site=local_site)

        # Pre-load all querysets for the sidebar.
        self.counts = get_sidebar_counts(user, local_site)

    def link_to_object(self, group, value):
        return ".?view=to-group&group=%s" % group.name


def get_sidebar_counts(user, local_site):
    """Returns counts used for the Dashboard sidebar."""
    profile = user.get_profile()

    site_profile, is_new = user.get_profile().site_profiles.get_or_create(
        local_site=local_site,
        user=user,
        profile=profile)

    if is_new:
        site_profile.save()

    counts = {
        'outgoing': site_profile.pending_outgoing_request_count,
        'incoming': site_profile.total_incoming_request_count,
        'to-me': site_profile.direct_incoming_request_count,
        'starred': site_profile.starred_public_request_count,
        'mine': site_profile.total_outgoing_request_count,
        'groups': SortedDict(),
        'starred_groups': SortedDict(),
    }

    for group in Group.objects.filter(
            users=user, local_site=local_site).order_by('name'):
        counts['groups'][group.name] = group.incoming_request_count

    for group in Group.objects.filter(
            starred_by=user, local_site=local_site).order_by('name'):
        counts['starred_groups'][group.name] = group.incoming_request_count

    return counts
