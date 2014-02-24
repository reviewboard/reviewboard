from __future__ import unicode_literals

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.template.defaultfilters import date
from django.utils import six
from django.utils.html import conditional_escape
from django.utils.six.moves import reduce
from django.utils.translation import ugettext_lazy as _, ugettext
from djblets.datagrid.grids import Column, DateTimeColumn

from reviewboard.accounts.models import Profile
from reviewboard.reviews.models import ReviewRequest
from reviewboard.reviews.templatetags.reviewtags import render_star
from reviewboard.site.urlresolvers import local_site_reverse


class BaseStarColumn(Column):
    """Indicates if an item is starred.

    This is the base class for all columns that deal with starring items.

    The star is interactive, allowing the user to star or unstar the item.
    """
    def __init__(self, *args, **kwargs):
        super(BaseStarColumn, self).__init__(
            image_class='rb-icon rb-icon-star-on',
            image_alt=_('Starred'),
            detailed_label=_('Starred'),
            shrink=True,
            *args, **kwargs)

        self.all_starred = {}

    def render_data(self, obj):
        obj.starred = self.all_starred.get(obj.id, False)
        return render_star(self.datagrid.request.user, obj)


class BugsColumn(Column):
    """Shows the list of bugs specified on a review request.

    The list of bugs will be linked to the bug tracker, if a bug tracker
    was configured for the repository the review request's change is on.
    """
    def __init__(self, *args, **kwargs):
        super(BugsColumn, self).__init__(
            label=_('Bugs'),
            css_class='bugs',
            link=False,
            shrink=True,
            sortable=False,
            *args, **kwargs)

    def augment_queryset(self, queryset):
        return queryset.select_related('repository')

    def render_data(self, review_request):
        bugs = review_request.get_bug_list()
        repository = review_request.repository

        if repository and repository.bug_tracker:
            try:
                return ', '.join(['<a href="%s">%s</a>' %
                                  (repository.bug_tracker % bug, bug)
                                  for bug in bugs])
            except TypeError:
                logging.warning('Invalid bug tracker format when rendering '
                                'bugs column: %s' % repository.bug_tracker)

        return ', '.join(bugs)


class DateTimeSinceColumn(DateTimeColumn):
    """Displays how long it has been since a given date/time.

    These columns will dynamically update as the page is shown, so that the
    number of minutes, hours, days, etc. ago is correct.
    """
    def render_data(self, obj):
        return '<time class="timesince" datetime="%s">%s</time>' % (
            date(getattr(obj, self.field_name), 'c'),
            super(DateTimeSinceColumn, self).render_data(obj))


class DiffUpdatedColumn(DateTimeColumn):
    """Shows the date/time that the diff was last updated."""
    def __init__(self, *args, **kwargs):
        super(DiffUpdatedColumn, self).__init__(
            label=_('Diff Updated'),
            db_field='diffset_history__last_diff_updated',
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
            return ''


class DiffUpdatedSinceColumn(DateTimeSinceColumn):
    """Shows the elapsed time since the diff was last updated."""
    def __init__(self, *args, **kwargs):
        super(DiffUpdatedSinceColumn, self).__init__(
            label=_('Diff Updated'),
            db_field='diffset_history__last_diff_updated',
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
            return ''


class GroupMemberCountColumn(Column):
    """Shows the number of users that are part of a review group."""
    def __init__(self, *args, **kwargs):
        super(GroupMemberCountColumn, self).__init__(
            link=True,
            link_func=self.link_to_object,
            *args, **kwargs)

    def render_data(self, group):
        return six.text_type(group.users.count())

    def link_to_object(self, group, value):
        return local_site_reverse('group-members',
                                  request=self.datagrid.request,
                                  args=[group.name])


class GroupsColumn(Column):
    """Shows the list of groups requested to review the review request."""
    def __init__(self, *args, **kwargs):
        super(GroupsColumn, self).__init__(
            label=_('Groups'),
            detailed_label=_('Target Groups'),
            sortable=False,
            shrink=False,
            *args, **kwargs)

    def render_data(self, review_request):
        groups = review_request.target_groups.all()
        return reduce(lambda a, d: a + d.name + ' ', groups, '')


class MyCommentsColumn(Column):
    """Shows if the current user has reviewed the review request."""
    def __init__(self, *args, **kwargs):
        super(MyCommentsColumn, self).__init__(
            image_class='rb-icon rb-icon-datagrid-comment-draft',
            image_alt=_('My Comments'),
            detailed_label=_('My Comments'),
            shrink=True,
            *args, **kwargs)

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
        super(NewUpdatesColumn, self).__init__(
            image_class='rb-icon rb-icon-datagrid-new-updates',
            image_alt=_('New Updates'),
            detailed_label=_('New Updates'),
            shrink=True,
            *args, **kwargs)

    def render_data(self, review_request):
        if review_request.new_review_count > 0:
            return '<div class="%s" title="%s" />' % \
                   (self.image_class, self.image_alt)

        return ''


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
        super(PeopleColumn, self).__init__(
            label=_('People'),
            detailed_label=_('Target People'),
            sortable=False,
            shrink=False,
            *args, **kwargs)

    def render_data(self, review_request):
        people = review_request.target_people.all()
        return reduce(lambda a, d: a + d.username + ' ', people, '')


class RepositoryColumn(Column):
    """Shows the name of the repository the review request's change is on."""
    def __init__(self, *args, **kwargs):
        super(RepositoryColumn, self).__init__(
            label=_('Repository'),
            db_field='repository__name',
            shrink=True,
            sortable=True,
            link=False,
            css_class='repository-column',
            *args, **kwargs)

    def augment_queryset(self, queryset):
        return queryset.select_related('repository')

    def render_data(self, obj):
        return super(RepositoryColumn, self).render_data(obj) or ''


class ReviewCountColumn(Column):
    """Shows the number of published reviews for a review request."""
    def __init__(self, *args, **kwargs):
        super(ReviewCountColumn, self).__init__(
            label=_('Reviews'),
            detailed_label=_('Number of Reviews'),
            shrink=True,
            link=True,
            link_func=self.link_to_object,
            *kwargs, **kwargs)

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
        return '%s#last-review' % review_request.get_absolute_url()


class ReviewGroupStarColumn(BaseStarColumn):
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


class ReviewRequestIDColumn(Column):
    """Displays the ID of the review request."""
    def __init__(self, *args, **kwargs):
        super(ReviewRequestIDColumn, self).__init__(
            label=_('ID'),
            detailed_label=_('Review Request ID'),
            shrink=True,
            link=True,
            *args, **kwargs)

    def render_data(self, review_request):
        return review_request.display_id


class ReviewRequestStarColumn(BaseStarColumn):
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
        super(ShipItColumn, self).__init__(
            image_class='rb-icon rb-icon-shipit',
            image_alt=_('Ship It!'),
            detailed_label = _('Ship It!'),
            db_field='shipit_count',
            sortable=True,
            shrink=True,
            *args, **kwargs)

    def render_data(self, review_request):
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


class SubmitterColumn(Column):
    """Shows the username of the user who submitted the review request."""
    def __init__(self, *args, **kwargs):
        super(SubmitterColumn, self).__init__(
            label=_('Submitter'),
            db_field='submitter__username',
            shrink=True,
            sortable=True,
            link=True,
            *args, **kwargs)

    def augment_queryset(self, queryset):
        return queryset.select_related('submitter')


class SummaryColumn(Column):
    """Shows the summary of a review request.

    This will also prepend the draft/submitted/discarded state, if any,
    to the summary.
    """
    def __init__(self, *args, **kwargs):
        super(SummaryColumn, self).__init__(
            label=_('Summary'),
            expand=True,
            link=True,
            css_class='summary',
            *args, **kwargs)

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


class ToMeColumn(Column):
    """Indicates if the user is requested to review the change.

    This will show an indicator if the user is on the Target People reviewers
    list.
    """
    def __init__(self, *args, **kwargs):
        raquo = '\u00BB'

        super(ToMeColumn, self).__init__(
            label=raquo,
            detailed_label=_('To Me'),
            detailed_label_html=(ugettext('%s To Me') % raquo),
            shrink=True,
            *args, **kwargs)

    def render_data(self, review_request):
        user = self.datagrid.request.user
        if (user.is_authenticated() and
            review_request.target_people.filter(pk=user.pk).exists()):
            return ('<div title="%s"><b>&raquo;</b></div>'
                    % (self.detailed_label))

        return ''


class DiffSizeColumn(Column):
    """Indicates line add/delete counts for the latest diffset."""
    def __init__(self, *args, **kwargs):
        super(DiffSizeColumn, self).__init__(
            label=_('Diff Size'),
            sortable=False,
            shrink=True,
            *args, **kwargs)

    def render_data(self, review_request):
        try:
            diffset = review_request.diffset_history.diffsets.latest()
        except ObjectDoesNotExist:
            return ''

        counts = diffset.get_total_line_counts()
        insert_count = counts['raw_insert_count']
        delete_count = counts['raw_delete_count']
        result = []

        if insert_count:
            result.append('<span class="diff-size-column insert">+%d</span>' %
                          insert_count)

        if delete_count:
            result.append('<span class="diff-size-column delete">-%d</span>' %
                          delete_count)

        return ' '.join(result)
