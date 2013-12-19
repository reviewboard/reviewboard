from __future__ import unicode_literals

import pytz
import logging

from django.contrib.auth.models import User
from django.http import Http404
from django.template.defaultfilters import date
from django.utils.datastructures import SortedDict
from django.utils.html import conditional_escape
from django.utils.translation import ugettext_lazy as _
from djblets.datagrid.grids import (CheckboxColumn, Column, DateTimeColumn,
                                    DataGrid)
from djblets.util.compat import six
from djblets.util.templatetags.djblets_utils import ageid

from reviewboard.accounts.models import Profile, LocalSiteProfile
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.reviews.templatetags.reviewtags import render_star
from reviewboard.site.urlresolvers import local_site_reverse


class DateTimeSinceColumn(DateTimeColumn):
    """Displays how long it has been since a given date/time.

    These columns will dynamically update as the page is shown, so that the
    number of minutes, hours, days, etc. ago is correct.
    """
    def render_data(self, obj):
        return '<time class="timesince" datetime="%s">%s</time>' % (
            date(getattr(obj, self.field_name), 'c'),
            super(DateTimeSinceColumn, self).render_data(obj))


class StarColumn(Column):
    """Indicates if an item is starred.

    This is the base class for all columns that deal with starring items.

    The star is interactive, allowing the user to star or unstar the item.
    """
    def __init__(self, *args, **kwargs):
        super(StarColumn, self).__init__(*args, **kwargs)

        self.image_class = 'rb-icon rb-icon-star-on'
        self.image_alt = _("Starred")
        self.detailed_label = _("Starred")
        self.shrink = True
        self.all_starred = {}

    def render_data(self, obj):
        obj.starred = self.all_starred.get(obj.id, False)
        return render_star(self.datagrid.request.user, obj)


class ReviewGroupStarColumn(StarColumn):
    """Indicates if a review group is starred.

    The star is interactive, allowing the user to star or unstar the group.
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
    """Indicates if a review request is starred.

    The star is interactive, allowing the user to star or unstar the
    review request.
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
    """Shows the "Ship It" count for a review request."""
    def __init__(self, *args, **kwargs):
        super(ShipItColumn, self).__init__(*args, **kwargs)

        self.image_class = 'rb-icon rb-icon-shipit'
        self.image_alt = _("Ship It!")
        self.detailed_label = _("Ship It!")
        self.db_field = "shipit_count"
        self.sortable = True
        self.shrink = True

    def render_data(self, review_request):
        if review_request.shipit_count > 0:
            return '<span class="shipit-count">' \
                   ' <div class="rb-icon rb-icon-shipit-checkmark"' \
                   '      title="%s"></div> %s' \
                   '</span>' % \
                (self.image_alt, review_request.shipit_count)

        return ""


class MyCommentsColumn(Column):
    """Shows if the current user has reviewed the review request."""
    def __init__(self, *args, **kwargs):
        super(MyCommentsColumn, self).__init__(*args, **kwargs)

        self.image_class = 'rb-icon rb-icon-datagrid-comment-draft'
        self.image_alt = _("My Comments")
        self.detailed_label = _("My Comments")
        self.shrink = True

        # XXX It'd be nice to be able to sort on this, but datagrids currently
        # can only sort based on stored (in the DB) values, not computed
        # values.

    def augment_queryset(self, queryset):
        user = self.datagrid.request.user

        if user.is_anonymous():
            return queryset

        query_dict = {
            'user_id': six.text_type(user.id),
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

        # Priority is ranked in the following order:
        #
        # 1) Non-public (draft) reviews
        # 2) Public reviews marked "Ship It"
        # 3) Public reviews not marked "Ship It"
        if review_request.mycomments_private_reviews > 0:
            icon_class = 'rb-icon-datagrid-comment-draft'
            image_alt = _("Comments drafted")
        else:
            if review_request.mycomments_shipit_reviews > 0:
                icon_class = 'rb-icon-datagrid-comment-shipit'
                image_alt = _("Comments published. Ship it!")
            else:
                icon_class = 'rb-icon-datagrid-comment'
                image_alt = _("Comments published")

        return '<div class="rb-icon %s" title="%s"></div>' % \
               (icon_class, image_alt)


class ToMeColumn(Column):
    """Indicates if the user is requested to review the change.

    This will show an indicator if the user is on the Target People reviewers
    list.
    """
    def __init__(self, *args, **kwargs):
        super(ToMeColumn, self).__init__(*args, **kwargs)

        self.label = "\u00BB"  # this is &raquo;
        self.detailed_label = "\u00BB To Me"
        self.shrink = True

    def render_data(self, review_request):
        user = self.datagrid.request.user
        if (user.is_authenticated() and
            review_request.target_people.filter(pk=user.pk).exists()):
            return ('<div title="%s"><b>&raquo;</b></div>'
                    % (self.detailed_label))

        return ""


class NewUpdatesColumn(Column):
    """Indicates if there are new updates on a review request.

    This will show an icon if the review request has had any new updates
    or reviews since the user last saw it.
    """
    def __init__(self, *args, **kwargs):
        super(NewUpdatesColumn, self).__init__(*args, **kwargs)

        self.image_class = 'rb-icon rb-icon-datagrid-new-updates'
        self.image_alt = "New Updates"
        self.detailed_label = "New Updates"
        self.shrink = True

    def render_data(self, review_request):
        if review_request.new_review_count > 0:
            return '<div class="%s" title="%s" />' % \
                   (self.image_class, self.image_alt)

        return ""


class SummaryColumn(Column):
    """Shows the summary of a review request.

    This will also prepend the draft/submitted/discarded state, if any,
    to the summary.
    """
    def __init__(self, label=_("Summary"), *args, **kwargs):
        super(SummaryColumn, self).__init__(label=label, *args, **kwargs)

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
                labels.update({_('Draft'): 'label-draft'})
            elif (not review_request.public and
                  review_request.status == ReviewRequest.PENDING_REVIEW):
                labels.update({_('Draft'): 'label-draft'})

        if review_request.status == ReviewRequest.SUBMITTED:
            labels.update({_('Submitted'): 'label-submitted'})
        elif review_request.status == ReviewRequest.DISCARDED:
            labels.update({_('Discarded'): 'label-discarded'})

        display_data = ''

        for label in labels:
            display_data += '<span class="%s">[%s] </span>' % (
                labels[label], label)
        display_data += summary
        return display_data


class SubmitterColumn(Column):
    """Shows the username of the user who submitted the review request."""
    def __init__(self, *args, **kwargs):
        super(SubmitterColumn, self).__init__(
            _("Submitter"), db_field="submitter__username",
            shrink=True, sortable=True, link=True, *args, **kwargs)

    def augment_queryset(self, queryset):
        return queryset.select_related('submitter')


class RepositoryColumn(Column):
    """Shows the name of the repository the review request's change is on."""
    def __init__(self, *args, **kwargs):
        super(RepositoryColumn, self).__init__(
            _("Repository"), db_field="repository__name",
            shrink=True, sortable=True, link=False,
            css_class='repository-column', *args, **kwargs)

    def augment_queryset(self, queryset):
        return queryset.select_related('repository')

    def render_data(self, obj):
        return super(RepositoryColumn, self).render_data(obj) or ''


class PendingCountColumn(Column):
    """Shows the pending number of review requests for a user or group.

    This will show the pending number of review requests for the given
    review group or user. It only applies to group or user lists.
    """
    def __init__(self, *args, **kwargs):
        super(PendingCountColumn, self).__init__(*args, **kwargs)

    def render_data(self, obj):
        return six.text_type(
            getattr(obj, self.field_name).filter(
                public=True, status='P').count())


class PeopleColumn(Column):
    """Shows the list of people requested to review the review request."""
    def __init__(self, *args, **kwargs):
        super(PeopleColumn, self).__init__(*args, **kwargs)

        self.label = _("People")
        self.detailed_label = _("Target People")
        self.sortable = False
        self.shrink = False

    def render_data(self, review_request):
        people = review_request.target_people.all()
        return reduce(lambda a, d: a + d.username + ' ', people, '')


class GroupsColumn(Column):
    """Shows the list of groups requested to review the review request."""
    def __init__(self, *args, **kwargs):
        super(GroupsColumn, self).__init__(*args, **kwargs)

        self.label = _("Groups")
        self.detailed_label = _("Target Groups")
        self.sortable = False
        self.shrink = False

    def render_data(self, review_request):
        groups = review_request.target_groups.all()
        return reduce(lambda a, d: a + d.name + ' ', groups, '')


class GroupMemberCountColumn(Column):
    """Shows the number of users that are part of a review group."""
    def __init__(self, *args, **kwargs):
        super(GroupMemberCountColumn, self).__init__(*args, **kwargs)

        self.link = True
        self.link_func = self.link_to_object

    def render_data(self, group):
        return six.text_type(group.users.count())

    def link_to_object(self, group, value):
        return local_site_reverse('group_members',
                                  request=self.datagrid.request,
                                  args=[group.name])


class ReviewCountColumn(Column):
    """Shows the number of published reviews for a review request."""
    def __init__(self, label=_("Reviews"),
                 detailed_label=_("Number of Reviews"),
                 *args, **kwargs):
        super(ReviewCountColumn, self).__init__(label=label,
                                                detailed_label=detailed_label,
                                                *kwargs, **kwargs)

        self.shrink = True
        self.link = True
        self.link_func = self.link_to_object

    def render_data(self, review_request):
        return six.text_type(review_request.publicreviewcount_count)

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
    """Shows the date/time that the diff was last updated."""
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
    """Shows the elapsed time since the diff was last updated."""
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


class BugsColumn(Column):
    """Shows the list of bugs specified on a review request.

    The list of bugs will be linked to the bug tracker, if a bug tracker
    was configured for the repository the review request's change is on.
    """
    def __init__(self, *args, **kwargs):
        super(BugsColumn, self).__init__(_("Bugs"), link=False, shrink=True,
                                         sortable=False, css_class="bugs",
                                         *args, **kwargs)

    def augment_queryset(self, queryset):
        return queryset.select_related('repository')

    def render_data(self, review_request):
        bugs = review_request.get_bug_list()
        repository = review_request.repository

        if repository and repository.bug_tracker:
            try:
                return (", ").join(['<a href="%s">%s</a>' %
                                    (repository.bug_tracker % bug, bug)
                                    for bug in bugs])
            except TypeError:
                logging.warning('Invalid bug tracker format when rendering '
                                'bugs column: %s' % repository.bug_tracker)

        return (", ").join(bugs)


class ReviewRequestDataGrid(DataGrid):
    """A datagrid that displays a list of review requests.

    This datagrid accepts the show_submitted parameter in the URL, allowing
    submitted review requests to be filtered out or displayed.
    """
    my_comments = MyCommentsColumn()
    star = ReviewRequestStarColumn()
    ship_it = ShipItColumn()
    summary = SummaryColumn(expand=True, link=True, css_class="summary")
    submitter = SubmitterColumn()

    branch = Column(_("Branch"), db_field="branch",
                    shrink=True, sortable=True, link=False)
    bugs_closed = BugsColumn()
    repository = RepositoryColumn()
    time_added = DateTimeColumn(
        _("Posted"),
        detailed_label=_("Posted Time"),
        format="F jS, Y, P", shrink=True,
        css_class=lambda r: ageid(r.time_added))
    last_updated = DateTimeColumn(
        _("Last Updated"),
        format="F jS, Y, P", shrink=True,
        db_field="last_updated",
        field_name="last_updated",
        css_class=lambda r: ageid(r.last_updated))
    diff_updated = DiffUpdatedColumn(
        format="F jS, Y, P", shrink=True,
        css_class=lambda r: ageid(r.diffset_history.last_diff_updated))
    time_added_since = DateTimeSinceColumn(
        _("Posted"),
        detailed_label=_("Posted Time (Relative)"),
        field_name="time_added", shrink=True,
        css_class=lambda r: ageid(r.time_added))
    last_updated_since = DateTimeSinceColumn(
        _("Last Updated"),
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

        super(ReviewRequestDataGrid, self).__init__(*args, **kwargs)

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
            profile, is_new = Profile.objects.get_or_create(user=user)
            self.timezone = pytz.timezone(profile.timezone)
            self.time_added.timezone = self.timezone
            self.last_updated.timezone = self.timezone
            self.diff_updated.timezone = self.timezone

    def load_extra_state(self, profile):
        if profile:
            self.show_submitted = profile.show_submitted

        try:
            self.show_submitted = (
                int(self.request.GET.get('show_submitted',
                                         self.show_submitted))
                != 0)
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
    """Displays the dashboard.

    The dashboard is the main place where users see what review requests
    are out there that may need their attention.
    """
    new_updates = NewUpdatesColumn()
    my_comments = MyCommentsColumn()
    selected = CheckboxColumn()

    def __init__(self, *args, **kwargs):
        local_site = kwargs.get('local_site', None)

        super(DashboardDataGrid, self).__init__(*args, **kwargs)

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
        group_name = self.request.GET.get('group', '')
        view = self.request.GET.get('view', self.default_view)
        user = self.request.user

        if view == 'outgoing':
            self.queryset = ReviewRequest.objects.from_user(
                user, user, local_site=self.local_site)
            self.title = _("All Outgoing Review Requests")
        elif view == 'mine':
            self.queryset = ReviewRequest.objects.from_user(
                user, user, None, local_site=self.local_site)
            self.title = _("All My Review Requests")
        elif view == 'to-me':
            self.queryset = ReviewRequest.objects.to_user_directly(
                user, user, local_site=self.local_site)
            self.title = _("Incoming Review Requests to Me")
        elif view == 'to-group':
            if group_name:
                # to-group is special because we want to make sure that the
                # group exists and show a 404 if it doesn't. Otherwise, we'll
                # show an empty datagrid with the name.
                try:
                    group = user.review_groups.get(name=group_name,
                                                   local_site=self.local_site)
                except Group.DoesNotExist:
                    raise Http404

                self.queryset = ReviewRequest.objects.to_group(
                    group_name, self.local_site, user)
                self.title = _("Incoming Review Requests to %s") % group_name
            else:
                self.queryset = ReviewRequest.objects.to_user_groups(
                    user, user, local_site=self.local_site)
                self.title = _("All Incoming Review Requests to My Groups")
        elif view == 'starred':
            profile, is_new = Profile.objects.get_or_create(user=user)
            self.queryset = profile.starred_review_requests.public(
                user=user, local_site=self.local_site, status=None)
            self.title = _("Starred Review Requests")
        elif view == 'incoming':
            self.queryset = ReviewRequest.objects.to_user(
                user, user, local_site=self.local_site)
            self.title = _("All Incoming Review Requests")
        else:
            raise Http404

        return False


class SubmitterDataGrid(DataGrid):
    """A datagrid showing a list of users registered on Review Board."""
    username = Column(_("Username"), link=True, sortable=True)
    fullname = Column(_("Full Name"), field_name="get_full_name",
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

        super(SubmitterDataGrid, self).__init__(request, qs, title)

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
    """A datagrid showing a list of review groups accessible by the user."""
    star = ReviewGroupStarColumn()
    name = Column(_("Group ID"), link=True, sortable=True)
    displayname = Column(_("Group Name"), field_name="display_name",
                         link=True, expand=True)
    pending_count = PendingCountColumn(_("Pending Reviews"),
                                       field_name="review_requests",
                                       link=True,
                                       shrink=True)
    member_count = GroupMemberCountColumn(_("Members"),
                                          field_name="members",
                                          shrink=True)

    def __init__(self, request, title=_("All groups"), *args, **kwargs):
        local_site = kwargs.pop('local_site', None)
        queryset = Group.objects.accessible(request.user,
                                            local_site=local_site)

        super(GroupDataGrid, self).__init__(request, queryset=queryset,
                                            title=title, *args, **kwargs)

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
    """Shows the list of review groups watched by the user."""
    def __init__(self, request, title=_("Watched groups"), *args, **kwargs):
        local_site = kwargs.pop('local_site', None)

        super(WatchedGroupDataGrid, self).__init__(request, title=title,
                                                   *args, **kwargs)

        user = request.user
        profile, is_new = Profile.objects.get_or_create(user=user)

        self.queryset = profile.starred_groups.all()
        self.queryset = self.queryset.filter(local_site=local_site)

    def link_to_object(self, group, value):
        return ".?view=to-group&group=%s" % group.name


def get_sidebar_counts(user, local_site):
    """Returns counts used for the Dashboard sidebar."""
    profile, is_new = Profile.objects.get_or_create(user=user)

    site_profile, is_new = LocalSiteProfile.objects.get_or_create(
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
            starred_by=profile, local_site=local_site).order_by('name'):
        counts['starred_groups'][group.name] = group.incoming_request_count

    return counts
