from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Q, Count
from django.utils.html import conditional_escape
from django.utils.translation import ugettext_lazy as _
from djblets.datagrid.grids import Column, DateTimeColumn, \
                                   DateTimeSinceColumn, DataGrid
from djblets.util.templatetags.djblets_utils import ageid

from reviewboard.accounts.models import Profile
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.reviews.templatetags.reviewtags import render_star


class StarColumn(Column):
    """
    A column used to indicate whether the object is "starred" or watched.
    The star is interactive, allowing the user to star or unstar the object.
    """
    def __init__(self, *args, **kwargs):
        Column.__init__(self, *args, **kwargs)
        self.image_url = settings.MEDIA_URL + "rb/images/star_on.png"
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

        print profile.starred_groups.all()
        pks = profile.starred_groups.filter(
            pk__in=self.datagrid.id_list).values_list('pk', flat=True)

        self.all_starred = {}

        for pk in pks:
            self.all_starred[pk] = True

        print self.all_starred

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
        self.image_url = settings.MEDIA_URL + "rb/images/shipit.png"
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
                    '<img src="%srb/images/shipit_checkmark.png?%s" ' \
                         'width="9" height="8" alt="%s" title="%s" /> %s' \
                   '</span>' % \
                (settings.MEDIA_URL, settings.MEDIA_SERIAL,
                 self.image_alt, self.image_alt, review_request.shipit_count)

        return ""


class MyCommentsColumn(Column):
    """
    A column meant to represent the status of the logged-in user's
    comments on the review.
    """
    def __init__(self, *args, **kwargs):
        Column.__init__(self, *args, **kwargs)
        self.image_url = settings.MEDIA_URL + "rb/images/comment-draft-small.png"
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
                image_url = settings.MEDIA_URL + \
                            "rb/images/comment-shipit-small.png"
                image_alt = _("Comments published. Ship it!")
            else:
                image_url = settings.MEDIA_URL + "rb/images/comment-small.png"
                image_alt = _("Comments published")

        return '<img src="%s?%s" width="%s" height="%s" alt="%s" ' \
               'title="%s" />' % \
                (image_url, settings.MEDIA_SERIAL, self.image_width,
                 self.image_height, image_alt, image_alt)


class NewUpdatesColumn(Column):
    """
    A column used to indicate whether the review request has any new updates
    since the user last saw it.
    """
    def __init__(self, *args, **kwargs):
        Column.__init__(self, *args, **kwargs)
        self.image_url = settings.MEDIA_URL + "rb/images/convo.png"
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
        if not summary:
            summary = '&nbsp;<i>%s</i>' % _('No Summary')

        if review_request.submitter_id == self.datagrid.request.user.id:
            if review_request.draft_summary is not None:
                summary = conditional_escape(review_request.draft_summary)
                return self.__labeled_summary(_('Draft'), summary)

            if (not review_request.public and
                review_request.status == ReviewRequest.PENDING_REVIEW):
                return self.__labeled_summary(_('Draft'), summary)

        if review_request.status == ReviewRequest.SUBMITTED:
            return self.__labeled_summary(_('Submitted'), summary)
        elif review_request.status == ReviewRequest.DISCARDED:
            return self.__labeled_summary(_('Discarded'), summary)

        return summary

    def __labeled_summary(self, label, summary):
        return u'<span class="draftlabel">[%s]</span> %s' % (label, summary)


class SubmitterColumn(Column):
    def __init__(self, *args, **kwargs):
        Column.__init__(self, _("Submitter"), db_field="submitter__username",
                        shrink=True, sortable=True, link=True,
                        *args, **kwargs)

    def augment_queryset(self, queryset):
        return queryset.select_related('submitter')


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
        return reverse('group_members', args=[group.name])


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


class ReviewRequestDataGrid(DataGrid):
    """
    A datagrid that displays a list of review requests.

    This datagrid accepts the show_submitted parameter in the URL, allowing
    submitted review requests to be filtered out or displayed.
    """
    star         = ReviewRequestStarColumn()
    ship_it      = ShipItColumn()
    summary      = SummaryColumn(expand=True, link=True, css_class="summary")
    submitter    = SubmitterColumn()

    branch       = Column(_("Branch"), db_field="branch",
                          shrink=True, sortable=True, link=False)
    bugs_closed  = Column(_("Bugs"), db_field="bugs_closed",
                          shrink=True, sortable=False, link=False)
    repository   = Column(_("Repository"), db_field="repository__name",
                          shrink=True, sortable=True, link=False,
                          css_class='repository-column')
    time_added   = DateTimeColumn(_("Posted"),
        detailed_label=_("Posted Time"),
        format="F jS, Y, P", shrink=True,
        css_class=lambda r: ageid(r.time_added))
    last_updated = DateTimeColumn(_("Last Updated"),
        format="F jS, Y, P", shrink=True,
        db_field="last_updated",
        field_name="last_updated",
        css_class=lambda r: ageid(r.last_updated))
    diff_updated = DateTimeColumn(_("Diff Updated"),
        format="F jS, Y, P", shrink=True,
        field_name="last_updated",
        css_class=lambda r: ageid(r.last_updated))

    time_added_since = DateTimeSinceColumn(_("Posted"),
        detailed_label=_("Posted Time (Relative)"),
        field_name="time_added", shrink=True,
        css_class=lambda r: ageid(r.time_added))
    last_updated_since = DateTimeSinceColumn(_("Last Updated"),
        detailed_label=_("Last Updated (Relative)"), shrink=True,
        db_field="last_updated",
        field_name="last_updated",
        css_class=lambda r: ageid(r.last_updated))
    diff_updated_since = DateTimeSinceColumn(_("Diff Updated"),
        detailed_label=_("Diff Updated (Relative)"),
        field_name="last_updated", shrink=True,
        css_class=lambda r: ageid(r.last_updated))

    review_count = ReviewCountColumn()

    review_id = Column(_("Review ID"), field_name="id", db_field="id",
                       shrink=True, sortable=True, link=True)

    def __init__(self, *args, **kwargs):
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

    def load_extra_state(self, profile):
        if profile:
            self.show_submitted = profile.show_submitted

        self.show_submitted = \
            int(self.request.GET.get('show_submitted',
                                     self.show_submitted)) != 0

        if self.show_submitted:
            # There are only three states: Published, Submitted and Discarded.
            # We want the first two, but it's faster to just search for not
            # discarded.
            self.queryset = self.queryset.exclude(status='D')
        else:
            self.queryset = self.queryset.filter(status='P')

        if profile and self.show_submitted != profile.show_submitted:
            profile.show_submitted = self.show_submitted
            return True

        return False

    def post_process_queryset(self, queryset):
        return super(ReviewRequestDataGrid, self).post_process_queryset(
            queryset.with_counts(self.request.user))

    def link_to_object(self, obj, value):
        if value and isinstance(value, User):
            return reverse("user", args=[value])

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

    def load_extra_state(self, profile):
        group = self.request.GET.get('group', '')
        view = self.request.GET.get('view', self.default_view)
        user = self.request.user

        if view == 'outgoing':
            self.queryset = ReviewRequest.objects.from_user(user, user)
            self.title = _(u"All Outgoing Review Requests")
        elif view == 'mine':
            self.queryset = ReviewRequest.objects.from_user(user, user, None)
            self.title = _(u"All My Review Requests")
        elif view == 'to-me':
            self.queryset = \
                ReviewRequest.objects.to_user_directly(user, user)
            self.title = _(u"Incoming Review Requests to Me")
        elif view == 'to-group':
            if group != "":
                self.queryset = ReviewRequest.objects.to_group(group, user)
                self.title = _(u"Incoming Review Requests to %s") % group
            else:
                self.queryset = \
                    ReviewRequest.objects.to_user_groups(user, user)
                self.title = _(u"All Incoming Review Requests to My Groups")
        elif view == 'starred':
            profile = user.get_profile()
            self.queryset = \
                profile.starred_review_requests.public(user)
            self.title = _(u"Starred Review Requests")
        else: # "incoming" or invalid
            self.queryset = ReviewRequest.objects.to_user(user, user)
            self.title = _(u"All Incoming Review Requests")

        # Pre-load all querysets for the sidebar.
        self.counts = get_sidebar_counts(user)

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
                 title=_("All submitters")):
        DataGrid.__init__(self, request, queryset, title)
        self.default_sort = ["username"]
        self.profile_sort_field = 'sort_submitter_columns'
        self.profile_columns_field = 'submitter_columns'
        self.default_columns = [
            "username", "fullname", "pending_count"
        ]

    @staticmethod
    def link_to_object(obj, value):
        return reverse("user", args=[obj.username])


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
        DataGrid.__init__(self, request, queryset=Group.objects.all(),
                          title=title, *args, **kwargs)
        self.profile_sort_field = 'sort_group_columns'
        self.profile_columns_field = 'group_columns'
        self.default_sort = ["name"]
        self.default_columns = [
            "star", "name", "displayname", "pending_count"
        ]

    @staticmethod
    def link_to_object(obj, value):
        return reverse("group", args=[obj.name])


class WatchedGroupDataGrid(GroupDataGrid):
    """
    A special version of GroupDataGrid that shows a list of watched groups,
    linking to a dashboard view of them. This is meant for display in the
    dashboard.
    """
    def __init__(self, request, title=_("Watched groups"), *args, **kwargs):
        GroupDataGrid.__init__(self, request, title=title, *args, **kwargs)
        user = request.user
        profile = user.get_profile()
        self.queryset = profile.starred_groups.all()

        # Pre-load all querysets for the sidebar.
        self.counts = get_sidebar_counts(user)

    def link_to_object(self, group, value):
        return ".?view=to-group&group=%s" % group.name


def get_sidebar_counts(user):
    """Returns counts used for the Dashboard sidebar."""
    profile = user.get_profile()

    counts = {
        'outgoing': ReviewRequest.objects.from_user(user, user).count(),
        'incoming': ReviewRequest.objects.to_user(user, user).count(),
        'to-me': ReviewRequest.objects.to_user_directly(user, user).count(),
        'starred': profile.starred_review_requests.public(user).count(),
        'mine': ReviewRequest.objects.from_user(user, user, None).count(),
        'groups': {}
    }

    q = Group.objects.filter(Q(users=user) | Q(starred_by=user)).distinct()
    group_names = list(q.values_list('name', flat=True))

    q = Group.objects.filter(name__in=group_names)
    q = q.filter((Q(review_requests__public=True) |
                  Q(review_requests__submitter=user)) &
                  Q(review_requests__submitter__is_active=True) &
                  Q(review_requests__status='P'))
    q = q.annotate(Count('review_requests'))

    for group in q.values('name', 'review_requests__count'):
        counts['groups'][group['name']] = \
            group['review_requests__count']

    return counts
