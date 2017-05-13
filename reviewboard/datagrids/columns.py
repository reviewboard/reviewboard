from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import NoReverseMatch
from django.template.defaultfilters import date
from django.utils import six
from django.utils.html import (conditional_escape, escape, format_html,
                               format_html_join)
from django.utils.six.moves import reduce
from django.utils.translation import ugettext_lazy as _, ugettext
from djblets.datagrid.grids import CheckboxColumn, Column, DateTimeColumn
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.models import Profile, ReviewRequestVisit
from reviewboard.avatars import avatar_services
from reviewboard.reviews.models import ReviewRequest
from reviewboard.reviews.templatetags.reviewtags import render_star
from reviewboard.site.urlresolvers import local_site_reverse


class BaseStarColumn(Column):
    """Indicates if an item is starred.

    This is the base class for all columns that deal with starring items.

    The star is interactive, allowing the user to star or unstar the item.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(BaseStarColumn, self).__init__(
            image_class='rb-icon rb-icon-star-on',
            image_alt=_('Starred'),
            detailed_label=_('Starred'),
            shrink=True,
            *args, **kwargs)

    def setup_state(self, state):
        """Set up the state for this column."""
        state.all_starred = set()

    def render_data(self, state, obj):
        """Return the rendered contents of the column."""
        obj.starred = obj.pk in state.all_starred
        return render_star(state.datagrid.request.user, obj)


class UsernameColumn(Column):
    """A column for showing a username and the user's avatar.

    The username and avatar will link to the user's profile page and will
    show basic profile information when hovering over the link.

    When constructing an instance of this column, the relation between the
    object being represented in the datagrid and the user can be specified
    as a tuple or list of field names forming a path to the user field.
    """

    AVATAR_SIZE = 24

    def __init__(self, label=_('Username'), user_relation=[], *args, **kwargs):
        """Initialize the column.

        Args:
            label (unicode, optional):
                The label for the column.

            user_relation (list of unicode, optional):
                A list of fields forming a relation path to the user. This can
                be left blank if representing the user.

            *args (tuple):
                Additional positional arguments to pass to the column.

            **kwargs (dict):
                Additional keyword arguments to pass to the column.
        """
        self._user_relation = user_relation

        super(UsernameColumn, self).__init__(
            label=label,
            db_field='__'.join(user_relation + ['username']),
            css_class='submitter-column',
            shrink=True,
            sortable=True,
            link=True,
            *args, **kwargs)

    def render_data(self, state, obj):
        """Render the user's name and avatar as HTML.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            obj (django.db.models.Model):
                The object being rendered in the datagrid.

        Returns:
            django.utils.safestring.SafeText:
            The HTML for the column.
        """
        # Look up the user in the provided obj by traversing the relation.
        # If _user_relation is empty, then obj is the user.
        user = obj

        for field_name in self._user_relation:
            user = getattr(user, field_name)

        # If avatars are eanbled, we'll want to include that in the resulting
        # HTML.
        siteconfig = SiteConfiguration.objects.get_current()
        request = state.datagrid.request
        avatar_html = ''

        if siteconfig.get(avatar_services.AVATARS_ENABLED_KEY):
            avatar_service = avatar_services.for_user(user)

            if avatar_service:
                avatar_html = avatar_service.render(request=request,
                                                    user=user,
                                                    size=self.AVATAR_SIZE)

        # Render the link to the user page, using the avatar and username.
        username = user.username
        user_url = local_site_reverse('user', request=request, kwargs={
            'username': username,
        })

        return format_html(
            '<a class="user" href="{0}">{1}{2}</a>',
            user_url, avatar_html, username)

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset.

        This will select fields for the user and the user's profile, to
        help with query performance.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        user_field = '__'.join(self._user_relation)

        if user_field:
            fields = [user_field, '%s__profile' % user_field]
        else:
            fields = ['profile']

        return queryset.select_related(*fields)


class BugsColumn(Column):
    """Shows the list of bugs specified on a review request.

    The list of bugs will be linked to the bug tracker, if a bug tracker
    was configured for the repository the review request's change is on.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        # Note that we're enabling linking but overriding the link function
        # to return None. This is to disable the automatic linking to the
        # review request, so that the cell isn't generally clickable,
        # preventing visual and interaction issues with the bug links.
        super(BugsColumn, self).__init__(
            label=_('Bugs'),
            css_class='bugs',
            link=True,
            link_func=lambda *args: None,
            shrink=True,
            sortable=False,
            *args, **kwargs)

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset."""
        return queryset.select_related('repository')

    def render_data(self, state, review_request):
        """Return the rendered contents of the column."""
        bugs = review_request.get_bug_list()
        repository = review_request.repository
        local_site_name = None

        if review_request.local_site:
            local_site_name = review_request.local_site.name

        if repository and repository.bug_tracker:
            links = []

            for bug in bugs:
                try:
                    url = local_site_reverse(
                        'bug_url',
                        local_site_name=local_site_name,
                        args=[review_request.display_id, bug])
                    links.append(
                        format_html('<a class="bug" href="{0}">{1}</a>',
                                    url, bug))
                except NoReverseMatch:
                    links.append(escape(bug))

            return ', '.join(links)

        return format_html_join(
            ', ',
            '<span class="bug">{0}</span>',
            ((bug,) for bug in bugs)
        )


class ReviewRequestCheckboxColumn(CheckboxColumn):
    """A column containing a check-box."""

    def render_data(self, state, obj):
        """Return the rendered contents of the column."""
        if self.is_selectable(state, obj):
            checked = ''

            if self.is_selected(state, obj):
                checked = 'checked="true"'

            return ('<input type="checkbox" data-object-id="%s" '
                    'data-checkbox-name="%s" %s />'
                    % (obj.display_id, escape(self.checkbox_name), checked))
        else:
            return ''


class DateTimeSinceColumn(DateTimeColumn):
    """Displays how long it has been since a given date/time.

    These columns will dynamically update as the page is shown, so that the
    number of minutes, hours, days, etc. ago is correct.
    """

    def render_data(self, state, obj):
        """Return the rendered contents of the column."""
        return '<time class="timesince" datetime="%s">%s</time>' % (
            date(getattr(obj, self.field_name), 'c'),
            super(DateTimeSinceColumn, self).render_data(state, obj))


class DiffUpdatedColumn(DateTimeColumn):
    """Shows the date/time that the diff was last updated."""

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(DiffUpdatedColumn, self).__init__(
            label=_('Diff Updated'),
            db_field='diffset_history__last_diff_updated',
            field_name='last_diff_updated',
            sortable=True,
            link=False,
            *args, **kwargs)

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset."""
        return queryset.select_related('diffset_history')

    def render_data(self, state, obj):
        """Return the rendered contents of the column."""
        if obj.diffset_history.last_diff_updated:
            return super(DiffUpdatedColumn, self).render_data(
                state, obj.diffset_history)
        else:
            return ''


class DiffUpdatedSinceColumn(DateTimeSinceColumn):
    """Shows the elapsed time since the diff was last updated."""

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(DiffUpdatedSinceColumn, self).__init__(
            label=_('Diff Updated'),
            db_field='diffset_history__last_diff_updated',
            field_name='last_diff_updated',
            sortable=True,
            link=False,
            *args, **kwargs)

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset."""
        return queryset.select_related('diffset_history')

    def render_data(self, state, obj):
        """Return the rendered contents of the column."""
        if obj.diffset_history.last_diff_updated:
            return super(DiffUpdatedSinceColumn, self).render_data(
                state, obj.diffset_history)
        else:
            return ''


class GroupMemberCountColumn(Column):
    """Shows the number of users that are part of a review group."""

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(GroupMemberCountColumn, self).__init__(
            link=True,
            link_func=self.link_to_object,
            *args, **kwargs)

    def render_data(self, state, group):
        """Return the rendered contents of the column."""
        return six.text_type(group.users.count())

    def link_to_object(self, state, group, value):
        """Return the link to the object in the column."""
        return local_site_reverse('group-members',
                                  request=state.datagrid.request,
                                  args=[group.name])


class GroupMembersUsernamesColumn(Column):
    """Shows the names of users that are part of a review group."""
    def __init__(self, *args, **kwargs):
        super(GroupMembersUsernamesColumn, self).__init__(
            link=True,
            link_func=self.link_to_object,
            *args, **kwargs)

    def render_data(self, state, group):
        users = list(group.users.all())
        usernames = ", ".join([user.username for user in users])
        return six.text_type(usernames)

    def link_to_object(self, state, group, value):
        return local_site_reverse('group-members',
                                  request=state.datagrid.request,
                                  args=[group.name])

class GroupsColumn(Column):
    """Shows the list of groups requested to review the review request."""

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(GroupsColumn, self).__init__(
            label=_('Groups'),
            detailed_label=_('Target Groups'),
            sortable=False,
            shrink=False,
            *args, **kwargs)

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset."""
        return queryset.prefetch_related('target_groups')

    def render_data(self, state, review_request):
        """Return the rendered contents of the column."""
        groups = review_request.target_groups.all()
        return reduce(lambda a, d: a + d.name + ' ', groups, '')


class MyCommentsColumn(Column):
    """Shows if the current user has reviewed the review request."""

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(MyCommentsColumn, self).__init__(
            image_class='rb-icon rb-icon-datagrid-comment-draft',
            image_alt=_('My Comments'),
            detailed_label=_('My Comments'),
            shrink=True,
            *args, **kwargs)

        # XXX It'd be nice to be able to sort on this, but datagrids currently
        # can only sort based on stored (in the DB) values, not computed
        # values.

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset."""
        user = state.datagrid.request.user

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

    def render_data(self, state, review_request):
        """Return the rendered contents of the column."""
        user = state.datagrid.request.user

        if user.is_anonymous() or review_request.mycomments_my_reviews == 0:
            return ''

        # Priority is ranked in the following order:
        #
        # 1) Non-public (draft) reviews
        # 2) Public reviews marked "Ship It"
        # 3) Public reviews not marked "Ship It"
        if review_request.mycomments_private_reviews > 0:
            icon_class = 'rb-icon-datagrid-comment-draft'
            image_alt = _('Comments drafted')
        else:
            if review_request.mycomments_shipit_reviews > 0:
                icon_class = 'rb-icon-datagrid-comment-shipit'
                image_alt = _('Comments published. Ship it!')
            else:
                icon_class = 'rb-icon-datagrid-comment'
                image_alt = _('Comments published')

        return '<div class="rb-icon %s" title="%s"></div>' % \
               (icon_class, image_alt)


class NewUpdatesColumn(Column):
    """Indicates if there are new updates on a review request.

    This will show an icon if the review request has had any new updates
    or reviews since the user last saw it.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(NewUpdatesColumn, self).__init__(
            image_class='rb-icon rb-icon-datagrid-new-updates',
            image_alt=_('New Updates'),
            detailed_label=_('New Updates'),
            shrink=True,
            *args, **kwargs)

    def render_data(self, state, review_request):
        """Return the rendered contents of the column."""

        # Review requests for un-authenticated users will not contain the
        # new_review_count attribute, so confirm its existence before
        # attempting to access.
        if (hasattr(review_request, 'new_review_count') and
            review_request.new_review_count > 0):
            return '<div class="%s" title="%s" />' % \
                   (self.image_class, self.image_alt)

        return ''


class PendingCountColumn(Column):
    """Shows the pending number of review requests for a user or group.

    This will show the pending number of review requests for the given
    review group or user. It only applies to group or user lists.
    """

    def render_data(self, state, obj):
        """Return the rendered contents of the column."""
        return six.text_type(
            getattr(obj, self.field_name).filter(
                public=True, status='P').count())


class PeopleColumn(Column):
    """Shows the list of people requested to review the review request."""

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(PeopleColumn, self).__init__(
            label=_('People'),
            detailed_label=_('Target People'),
            sortable=False,
            shrink=False,
            *args, **kwargs)

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset."""
        return queryset.prefetch_related('target_people')

    def render_data(self, state, review_request):
        """Return the rendered contents of the column."""
        people = review_request.target_people.all()
        return reduce(lambda a, d: a + d.username + ' ', people, '')


class RepositoryColumn(Column):
    """Shows the name of the repository the review request's change is on."""

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(RepositoryColumn, self).__init__(
            label=_('Repository'),
            db_field='repository__name',
            shrink=True,
            sortable=True,
            link=False,
            css_class='repository-column',
            *args, **kwargs)

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset."""
        return queryset.select_related('repository')

    def render_data(self, state, obj):
        """Return the rendered contents of the column."""
        return super(RepositoryColumn, self).render_data(state, obj) or ''


class ReviewCountColumn(Column):
    """Shows the number of published reviews for a review request."""

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(ReviewCountColumn, self).__init__(
            label=_('Reviews'),
            detailed_label=_('Number of Reviews'),
            shrink=True,
            link=True,
            link_func=self.link_to_object,
            *kwargs, **kwargs)

    def render_data(self, state, review_request):
        """Return the rendered contents of the column."""
        return six.text_type(review_request.publicreviewcount_count)

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset."""
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

    def link_to_object(self, state, review_request, value):
        """Return the link to the object in the column."""
        return '%s#last-review' % review_request.get_absolute_url()


class ReviewGroupStarColumn(BaseStarColumn):
    """Indicates if a review group is starred.

    The star is interactive, allowing the user to star or unstar the group.
    """

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset."""
        user = state.datagrid.request.user

        if user.is_anonymous():
            return queryset

        try:
            profile = user.get_profile()
        except Profile.DoesNotExist:
            return queryset

        state.all_starred = set(
            profile.starred_groups.filter(
                pk__in=state.datagrid.id_list).values_list('pk', flat=True))

        return queryset


class ReviewRequestIDColumn(Column):
    """Displays the ID of the review request."""

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(ReviewRequestIDColumn, self).__init__(
            label=_('ID'),
            detailed_label=_('Review Request ID'),
            shrink=True,
            link=True,
            sortable=True,
            *args, **kwargs)

    def get_sort_field(self, state):
        """Return the model field for sorting this column."""
        if state.datagrid.local_site:
            return 'local_id'
        else:
            return 'id'

    def render_data(self, state, review_request):
        """Return the rendered contents of the column."""
        return review_request.display_id


class ReviewRequestStarColumn(BaseStarColumn):
    """Indicates if a review request is starred.

    The star is interactive, allowing the user to star or unstar the
    review request.
    """

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset."""
        user = state.datagrid.request.user

        if user.is_anonymous():
            return queryset

        try:
            profile = user.get_profile()
        except Profile.DoesNotExist:
            return queryset

        state.all_starred = set(
            profile.starred_review_requests.filter(
                pk__in=state.datagrid.id_list).values_list('pk', flat=True))

        return queryset


class ShipItColumn(Column):
    """Shows the "Ship It" count for a review request."""

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(ShipItColumn, self).__init__(
            image_class='rb-icon rb-icon-shipit',
            image_alt=_('Ship It!'),
            detailed_label=_('Ship It!'),
            db_field='shipit_count',
            sortable=True,
            shrink=True,
            *args, **kwargs)

    def render_data(self, state, review_request):
        """Return the rendered contents of the column."""
        if review_request.issue_open_count > 0:
            return ('<span class="issue-count">'
                    ' <span class="issue-icon">!</span> %s'
                    '</span>'
                    % review_request.issue_open_count)
        elif review_request.shipit_count > 0:
            return '<span class="shipit-count">' \
                   ' <div class="rb-icon rb-icon-shipit-checkmark"' \
                   '      title="%s"></div> %s' \
                   '</span>' % \
                (self.image_alt, review_request.shipit_count)
        else:
            return ''


class SummaryColumn(Column):
    """Shows the summary of a review request.

    This will also prepend the draft/submitted/discarded state, if any,
    to the summary.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(SummaryColumn, self).__init__(
            label=_('Summary'),
            expand=True,
            link=True,
            css_class='summary',
            sortable=True,
            *args, **kwargs)

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset."""
        user = state.datagrid.request.user

        if user.is_anonymous():
            return queryset

        return queryset.extra(select={
            'draft_summary': """
                SELECT reviews_reviewrequestdraft.summary
                  FROM reviews_reviewrequestdraft
                  WHERE reviews_reviewrequestdraft.review_request_id =
                        reviews_reviewrequest.id
            """,
            'visibility': """
                SELECT accounts_reviewrequestvisit.visibility
                  FROM accounts_reviewrequestvisit
                 WHERE accounts_reviewrequestvisit.review_request_id =
                       reviews_reviewrequest.id
                   AND accounts_reviewrequestvisit.user_id = %(user_id)s
            """ % {
                'user_id': six.text_type(user.id)
            }
        })

    def render_data(self, state, review_request):
        """Return the rendered contents of the column."""
        summary = review_request.summary
        labels = []

        if review_request.submitter_id == state.datagrid.request.user.id:
            if review_request.draft_summary is not None:
                summary = review_request.draft_summary
                labels.append(('label-draft', _('Draft')))
            elif (not review_request.public and
                  review_request.status == ReviewRequest.PENDING_REVIEW):
                labels.append(('label-draft', _('Draft')))

        # review_request.visibility is not defined when the user is not
        # logged in.
        if state.datagrid.request.user.is_authenticated():
            if review_request.visibility == ReviewRequestVisit.ARCHIVED:
                labels.append(('label-archived', _('Archived')))
            elif review_request.visibility == ReviewRequestVisit.MUTED:
                labels.append(('label-muted', _('Muted')))

        if review_request.status == ReviewRequest.SUBMITTED:
            labels.append(('label-submitted', _('Submitted')))
        elif review_request.status == ReviewRequest.DISCARDED:
            labels.append(('label-discarded', _('Discarded')))

        display_data = format_html_join(
            '', '<label class="{0}">{1}</label>', labels)

        if summary:
            display_data += format_html('<span>{0}</span>', summary)
        else:
            display_data += format_html('<span class="no-summary">{0}</span>',
                                        _('No Summary'))

        return display_data


class ReviewSummaryColumn(SummaryColumn):
    """Shows the summary of the review request of a review.

    This does not (yet) prepend the draft/submitted/discarded state, if any,
    to the summary.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(SummaryColumn, self).__init__(
            label=_('Review Request Summary'),
            expand=True,
            link=True,
            css_class='summary',
            *args, **kwargs)

    def render_data(self, state, review):
        """Return the rendered contents of the column."""
        return conditional_escape(review.review_request.summary)

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset."""
        return queryset.select_related('review_request')


class ToMeColumn(Column):
    """Indicates if the user is requested to review the change.

    This will show an indicator if the user is on the Target People reviewers
    list.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        raquo = '\u00BB'

        super(ToMeColumn, self).__init__(
            label=raquo,
            detailed_label=_('To Me'),
            detailed_label_html=(ugettext('%s To Me') % raquo),
            shrink=True,
            *args, **kwargs)

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset."""
        user = state.datagrid.request.user

        if user.is_authenticated():
            state.all_to_me = set(
                user.directed_review_requests.filter(
                    pk__in=state.datagrid.id_list).values_list('pk',
                                                               flat=True))
        else:
            state.all_to_me = set()

        return queryset

    def render_data(self, state, review_request):
        """Return the rendered contents of the column."""
        if review_request.pk in state.all_to_me:
            return ('<div title="%s"><b>&raquo;</b></div>'
                    % (self.detailed_label))

        return ''


class DiffSizeColumn(Column):
    """Indicates line add/delete counts for the latest diffset."""

    def __init__(self, *args, **kwargs):
        """Initialize the column."""
        super(DiffSizeColumn, self).__init__(
            label=_('Diff Size'),
            sortable=False,
            shrink=True,
            *args, **kwargs)

    def render_data(self, state, review_request):
        """Return the rendered contents of the column."""
        if review_request.repository_id is None:
            return ''

        diffsets = list(review_request.diffset_history.diffsets.all())

        if not diffsets:
            return ''

        diffset = diffsets[-1]

        counts = diffset.get_total_line_counts()
        insert_count = counts.get('raw_insert_count')
        delete_count = counts.get('raw_delete_count')
        result = []

        if insert_count:
            result.append('<span class="diff-size-column insert">+%d</span>' %
                          insert_count)

        if delete_count:
            result.append('<span class="diff-size-column delete">-%d</span>' %
                          delete_count)

        if result:
            return '&nbsp;'.join(result)

        return ''

    def augment_queryset(self, state, queryset):
        """Add additional queries to the queryset.

        This will prefetch the diffsets and filediffs needed to perform the
        line calculations.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        # TODO: Update this to fetch only the specific fields when we move
        #       to a newer version of Django.
        return queryset.prefetch_related('diffset_history__diffsets',
                                         'diffset_history__diffsets__files')
