from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.template.defaultfilters import date, timesince
from django.utils.html import conditional_escape
from django.utils.translation import ugettext_lazy as _
from djblets.datagrid.grids import Column, DateTimeColumn, \
                                   DateTimeSinceColumn, DataGrid
from djblets.util.templatetags.djblets_utils import ageid

from reviewboard.reviews.models import Group, ReviewRequest, ReviewRequestDraft
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
        self.image_alt = "Starred"
        self.detailed_label = "Starred"
        self.shrink = True

    def render_data(self, obj):
        return render_star(self.datagrid.request.user, obj)


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
        self.image_alt = "Ship It!"
        self.detailed_label = "Ship It!"
        self.shrink = True

    def render_data(self, review_request):
        if review_request.get_public_reviews().filter(ship_it=True).count() > 0:
            return '<img src="%s" width="%s" height="%s" alt="%s" />' % \
                (self.image_url, self.image_width, self.image_height,
                 self.image_alt)

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

    def render_data(self, review_request):
        user = self.datagrid.request.user

        if user.is_anonymous():
            return ""

        image_url = None
        image_alt = None
        reviews = review_request.reviews.filter(user=user)

        if reviews.filter(public=False).count() > 0:
            # Remind about drafts over finished comments
            image_url = self.image_url
            image_alt = _("Comments drafted")
        elif review_request.get_public_reviews().filter(ship_it=True,
                                                        user=user).count() > 0):
            image_url = settings.MEDIA_URL + \
                        "rb/images/comment-shipit-small.png"
            image_alt = _("Comments published. Ship it!")
        elif reviews.filter(public=True).count() > 0:
            image_url = settings.MEDIA_URL + "rb/images/comment-small.png"
            image_alt = _("Comments published")
        else:
            return ""

        return '<img src="%s?%s" width="%s" height="%s" alt="%s" />' % \
                (image_url, settings.MEDIA_SERIAL, self.image_width,
                 self.image_height, image_alt)


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
        user = self.datagrid.request.user
        if review_request.get_new_reviews(user).count() > 0:
            return '<img src="%s" width="%s" height="%s" alt="%s" />' % \
                (self.image_url, self.image_width, self.image_height,
                 self.image_alt)

        return ""


class SummaryColumn(Column):
    """
    A column used to display a summary of the review request, along with
    labels indicating if it's a draft or if it's submitted.
    """
    def __init__(self, label=_("Summary"), *args, **kwargs):
        Column.__init__(self, label=label, *args, **kwargs)
        self.sortable = True

    def render_data(self, review_request):
        summary = conditional_escape(review_request.summary)
        if not summary:
            summary = '&nbsp;<i>No Summary</i>'

        if review_request.submitter == self.datagrid.request.user:
            try:
                draft = review_request.draft.get()
                summary = conditional_escape(draft.summary)
                return "<span class=\"draftlabel\">[Draft]</span> " + \
                       summary
            except ReviewRequestDraft.DoesNotExist:
                pass

            if not review_request.public:
                # XXX Do we want to say "Draft?"
                return "<span class=\"draftlabel\">[Draft]</span> " + \
                       summary

        if review_request.status == 'S':
            return "<span class=\"draftlabel\">[Submitted]</span> " + \
                   summary

        return summary


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
        return str(review_request.get_public_reviews().count())

    def link_to_object(self, review_request, value):
        return "%s#last-review" % review_request.get_absolute_url()


class LastUpdatedColumn(DateTimeColumn):
    """
    A column which shows the date of the last change to the review request,
    including reviews.
    """
    def __init__(self, label, db_field="last_updated", *args, **kwargs):
        DateTimeColumn.__init__(self, label, db_field=db_field, *args, **kwargs)

    def find_date(self, review_request):
        update = review_request.last_updated

        reviews = review_request.get_public_reviews().order_by('-timestamp')
        if reviews.count() > 0:
            review_date = reviews[0].timestamp
            if review_date > update:
                update = review_date

        return update

    def render_data(self, review_request):
        return date(self.find_date(review_request), self.format)


class LastUpdatedSinceColumn(LastUpdatedColumn):
    """
    A column which shows the date of the last change to the review request,
    including reviews.
    """
    def render_data(self, review_request):
        return _("%s ago") % timesince(self.find_date(review_request))


class ReviewRequestDataGrid(DataGrid):
    """
    A datagrid that displays a list of review requests.

    This datagrid accepts the show_submitted parameter in the URL, allowing
    submitted review requests to be filtered out or displayed.
    """
    star         = StarColumn()
    ship_it      = ShipItColumn()
    summary      = SummaryColumn(expand=True, link=True, css_class="summary")
    submitter    = Column(_("Submitter"), db_field="submitter__username",
                          shrink=True, sortable=True, link=True)

    repository   = Column(_("Repository"), db_field="repository__name",
                          shrink=True, sortable=True, link=False)
    time_added   = DateTimeColumn(_("Posted"),
        detailed_label=_("Posted Time"),
        format="F jS, Y, P", shrink=True,
        css_class=lambda r: ageid(r.time_added))
    last_updated = LastUpdatedColumn(_("Last Updated"),
        format="F jS, Y, P", shrink=True,
        css_class=lambda r: ageid(r.last_updated))
    diff_updated = DateTimeColumn(_("Diff Updated"),
        format="F jS, Y, P", shrink=True,
        field_name="last_updated",
        css_class=lambda r: ageid(r.last_updated))

    time_added_since = DateTimeSinceColumn(_("Posted"),
        detailed_label=_("Posted Time (Relative)"),
        field_name="time_added", shrink=True,
        css_class=lambda r: ageid(r.time_added))
    last_updated_since = LastUpdatedSinceColumn(_("Last Updated"),
        detailed_label=_("Last Updated (Relative)"), shrink=True,
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
            self.queryset = self.queryset.filter(Q(status='P') | Q(status='S'))
        else:
            self.queryset = self.queryset.filter(status='P')

        if profile and self.show_submitted != profile.show_submitted:
            profile.show_submitted = self.show_submitted
            return True

        return False

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
            self.queryset = ReviewRequest.objects.from_user(user.username, user)
            self.title = _(u"All Outgoing Review Requests")
        elif view == 'to-me':
            self.queryset = \
                ReviewRequest.objects.to_user_directly(user.username, user)
            self.title = _(u"Incoming Review Requests to Me")
        elif view == 'to-group':
            if group != "":
                self.queryset = ReviewRequest.objects.to_group(group, user)
                self.title = _(u"Incoming Review Requests to %s") % group
            else:
                self.queryset = \
                    ReviewRequest.objects.to_user_groups(user.username, user)
                self.title = _(u"All Incoming Review Requests to My Groups")
        elif view == 'starred':
            self.queryset = \
                user.get_profile().starred_review_requests.public(user)
            self.title = _(u"Starred Review Requests")
        else: # "incoming" or invalid
            self.queryset = ReviewRequest.objects.to_user(user.username, user)
            self.title = _(u"All Incoming Review Requests")

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
    star          = StarColumn()
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
        self.queryset = request.user.get_profile().starred_groups.all()

    def link_to_object(self, group, value):
        return ".?view=to-group&group=%s" % group.name
