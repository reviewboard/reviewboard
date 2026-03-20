"""Columns for datagrids."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Count, Q
from django.template.defaultfilters import date
from django.urls import NoReverseMatch
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext, gettext_lazy as _, ngettext
from djblets.datagrid.grids import CheckboxColumn, Column, DateTimeColumn
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.avatars import avatar_services
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.reviews.templatetags.reviewtags import render_star
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime
    from typing import Any, Final, NotRequired, TypedDict

    from django.contrib.auth.models import User
    from django.db.models import QuerySet
    from django.utils.safestring import SafeString
    from djblets.datagrid.grids import StatefulColumn
    from typelets.django.strings import StrPromise

    from reviewboard.accounts.models import (StarrableObject,
                                             User as RBUser)
    from reviewboard.reviews.models import Review

    class _BugsColumnData(TypedDict):
        id: str
        url: NotRequired[str]


class BaseStarColumn(Column):
    """Indicates if an item is starred.

    This is the base class for all columns that deal with starring items.

    The star is interactive, allowing the user to star or unstar the item.
    """

    detailed_label = _('Starred')
    image_alt = _('Starred')
    image_class = 'rb-icon rb-icon-star-on'
    shrink = True

    #: The starrable model handled by the column.
    starrable_model: type[StarrableObject]

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
        """Add additional queries to the queryset.

        This will load the list of starrable object IDs to check in the
        starred list, and then set them in the user's star cache for
        later rendering.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        user = state.datagrid.request.user

        if user.is_authenticated:
            profile = user.get_profile()
            profile.prefetch_starred_objects(self.starrable_model,
                                             state.datagrid.id_list)

        return queryset

    def render_data(
        self,
        state: StatefulColumn,
        obj: StarrableObject,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (django.db.models.Model):
                The starrable model object for the row.

        Returns:
            django.utils.safestring.SafeString:
            The rendered data as HTML.
        """
        return render_star(state.datagrid.request.user, obj)

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: StarrableObject,
    ) -> bool:
        """Return the raw value for the star state.

        This will determine whether the object is starred and save it
        for lookup during rendering.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (django.db.models.Model):
                The starrable model object for the row.

        Returns:
            bool:
            The star state for the object.
        """
        user = state.datagrid.request.user

        return (
            user.is_authenticated and
            user.get_profile().is_object_starred(obj)
        )


class UsernameColumn(Column):
    """A column for showing a username and the user's avatar.

    The username and avatar will link to the user's profile page and will
    show basic profile information when hovering over the link.

    When constructing an instance of this column, the relation between the
    object being represented in the datagrid and the user can be specified
    as a tuple or list of field names forming a path to the user field.
    """

    AVATAR_SIZE = 24

    label = _('Username')
    css_class = 'submitter-column'
    shrink = True
    sortable = True
    link = True
    link_css_class = 'user'

    def __init__(
        self,
        user_relation: (Sequence[str] | None) = None,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the column.

        Args:
            user_relation (list of str, optional):
                A list of fields forming a relation path to the user. This can
                be left blank if representing the user.

            *args (tuple):
                Additional positional arguments to pass to the column.

            **kwargs (dict):
                Additional keyword arguments to pass to the column.
        """
        if user_relation is None:
            user_relation = []

        self._user_relation = user_relation

        super().__init__(
            db_field='__'.join([*user_relation, 'username']),
            link_func=self._link_user,
            *args, **kwargs)

    def get_user(
        self,
        obj: Any,
    ) -> RBUser:
        """Return the user associated with this object.

        Args:
            obj (object):
                The object provided to the column.

        Returns:
            reviewboard.accounts.models.User:
            The resulting user.
        """
        # Look up the user in the provided obj by traversing the relation.
        # If _user_relation is empty, then obj is the user.
        user = obj

        for field_name in self._user_relation:
            user = getattr(user, field_name)

        return user

    def render_data(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> SafeString:
        """Render the user's name and avatar as HTML.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            obj (django.db.models.Model):
                The object being rendered in the datagrid.

        Returns:
            django.utils.safestring.SafeString:
            The HTML for the column.
        """
        user = self.get_user(obj)

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

        return format_html('{0}{1}', avatar_html, username)

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
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

    def _link_user(
        self,
        state: StatefulColumn,
        obj: Any,
        *args,
    ) -> str:
        """Return the URL to link the user associated with this object.

        Args:
            state (djblets.datagrid.grids.StatefulColumn, unused):
                The column state.

            obj (object):
                The object provided to the column.

            *args (tuple):
                Additional keyword arguments provided to the method.

        Returns:
            str:
            The URL for the user.
        """
        return local_site_reverse(
            'user',
            request=state.datagrid.request,
            kwargs={
                'username': self.get_user(obj).username,
            })


class FullNameColumn(Column):
    """Shows the full name of the user when appropriate."""

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
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
        return queryset.select_related('profile')

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: RBUser,
    ) -> str | None:
        """Return the raw value for the full name.

        If the profile is private, the full name will not be provided.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.accounts.models.User):
                The user for the row.

        Returns:
            str:
            The full name, or ``None`` if the profile is private.
        """
        profile = obj.get_profile()
        request_user = state.datagrid.request.user

        if obj.is_profile_visible(request_user):
            return profile.get_display_name(request_user)

        return None


class BugsColumn(Column):
    """Shows the list of bugs specified on a review request.

    The list of bugs will be linked to the bug tracker, if a bug tracker
    was configured for the repository the review request's change is on.
    """

    label = _('Bugs')
    css_class = 'bugs'
    shrink = True
    sortable = False
    link = False

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
        """Add additional queries to the queryset.

        This will include the repository along with each review request.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        return queryset.select_related('repository')

    def render_data(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request being rendered for this row.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML.
        """
        result: list[SafeString] = []

        for bug_info in self.get_raw_object_value(state, obj):
            url = bug_info.get('url')
            bug_id = bug_info['id']

            if url:
                html = format_html(
                    '<a class="bug" href="{}">{}</a>',
                    url, bug_id,
                )
            else:
                html = format_html(
                    '<span class="bug">{}</span>',
                    bug_id,
                )

            result.append(html)

        return mark_safe(', '.join(result))

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> Sequence[_BugsColumnData]:
        """Return the raw value for the bugs information.

        This will return the list of bug IDs and URLs (if present) from the
        review request.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request for the row.

        Returns:
            list of _BugsColumnData:
            The list of bug information.
        """
        review_request = obj
        repository = review_request.repository

        # Determine the Local Site name for the review request, if any.
        local_site_name: (str | None) = None

        if review_request.local_site:
            local_site_name = review_request.local_site.name

        result: list[_BugsColumnData]
        bugs = obj.get_bug_list()

        if repository and repository.bug_tracker:
            result = []

            for bug in bugs:
                bug_info: _BugsColumnData = {
                    'id': bug,
                }

                try:
                    bug_info['url'] = local_site_reverse(
                        'bug_url',
                        local_site_name=local_site_name,
                        args=[review_request.display_id, bug],
                    )
                except NoReverseMatch:
                    pass

                result.append(bug_info)
        else:
            result = [
                {
                    'id': bug,
                }
                for bug in bugs
            ]

        return result


class ReviewRequestCheckboxColumn(CheckboxColumn):
    """A column containing a check-box."""

    def render_data(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request being rendered for this row.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML.
        """
        if not self.is_selectable(state, obj):
            return mark_safe('')

        if self.is_selected(state, obj):
            checked = mark_safe('checked="true"')
        else:
            checked = mark_safe('')

        return format_html(
            '<input type="checkbox" data-object-id="{}" '
            'data-checkbox-name="{}" {}>',
            obj.display_id,
            self.checkbox_name,
            checked,
        )


class DateTimeSinceColumn(DateTimeColumn):
    """Displays how long it has been since a given date/time.

    These columns will dynamically update as the page is shown, so that the
    number of minutes, hours, days, etc. ago is correct.
    """

    def render_data(
        self,
        state: StatefulColumn,
        obj: Any,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (object):
                The object being rendered for this row.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML.
        """
        value = self.get_raw_object_value(state, obj)

        if value is None:
            return mark_safe('')

        return format_html(
            '<time class="timesince" datetime="{}">{}</time>',
            date(value, 'c'),
            super().render_data(state, obj),
        )


class DiffUpdatedColumn(DateTimeColumn):
    """Shows the date/time that the diff was last updated."""

    label = _('Diff Updated')
    db_field = 'diffset_history__last_diff_updated'
    sortable = True
    link = False

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
        """Add additional queries to the queryset.

        This will include the diffset history along with each review request.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        return queryset.select_related('diffset_history')

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> datetime | None:
        """Return the diff updated timestamp.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request to return the value for.

        Returns:
            datetime.datetime:
            The diff updated timestamp, or ``None`` if there's no diff.
        """
        if ((diffset_history := obj.diffset_history) and
            (last_diff_updated := diffset_history.last_diff_updated)):
            return last_diff_updated

        return None


class DiffUpdatedSinceColumn(DateTimeSinceColumn):
    """Shows the elapsed time since the diff was last updated."""

    label = _('Diff Updated')
    db_field = 'diffset_history__last_diff_updated'
    sortable = True
    link = False

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
        """Add additional queries to the queryset.

        This will include the diffset history along with each review request.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        return queryset.select_related('diffset_history')

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> datetime | None:
        """Return the diff updated timestamp.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request to return the value for.

        Returns:
            datetime.datetime:
            The diff updated timestamp, or ``None`` if there's no diff.
        """
        if obj.diffset_history and obj.diffset_history.last_diff_updated:
            return obj.diffset_history.last_diff_updated

        return None


class GroupMemberCountColumn(Column):
    """Shows the number of users that are part of a review group."""

    link = True

    def augment_queryset_for_data(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
        **kwargs,
    ) -> QuerySet:
        """Augment a queryset for data-rendering purposes.

        This will count the number of group members for display.

        Version Added:
            5.0.7

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the DataGrid instance.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

            **kwargs (dict):
                Additional keyword arguments for future expansion.

        Returns:
            django.db.models.query.QuerySet:
            The resulting augmented QuerySet.
        """
        return queryset.annotate(column_group_member_count=Count('users'))

    def render_data(
        self,
        state: StatefulColumn,
        obj: Group,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.group.Group):
                The object being rendered for this row.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML.
        """
        return escape(str(self.get_raw_object_value(state, obj)))

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: Group,
    ) -> int:
        """Return the raw value for the group membership count.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.Group):
                The review group for the row.

        Returns:
            int:
            The group membership count.
        """
        return getattr(obj, 'column_group_member_count', 0)

    @staticmethod
    def link_func(
        state: StatefulColumn,
        obj: Group,
        value: str,
    ) -> str:
        """Return the link to the object in the column.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            obj (reviewboard.reviews.models.Group):
                The review group for the row.

            value (str):
                The rendered data.

        Returns:
            str:
            The URL to link to.
        """
        return local_site_reverse('group-members',
                                  request=state.datagrid.request,
                                  args=[obj.name])


class GroupsColumn(Column):
    """Shows the list of groups requested to review the review request."""

    label = _('Groups')
    detailed_label = _('Target Groups')
    sortable = False
    shrink = False

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
        """Add additional queries to the queryset.

        This will pre-fetch the review groups for each review request.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        return queryset.prefetch_related('target_groups')

    def render_data(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the datagrid.

            obj (reviewboard.reviews.models.review_request.ReviewRequest):
                The review request.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML.
        """
        return escape(' '.join(
            group.name
            for group in self.get_raw_object_value(state, obj)
        ))

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> Sequence[Group]:
        """Return the list of review groups.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request to return the value for.

        Returns:
            list of reviewboard.reviews.models.Group:
            The list of review groups.
        """
        return list(obj.target_groups.all())


class MyCommentsColumn(Column):
    """Shows if the current user has reviewed the review request."""

    detailed_label = _('My Comments')
    image_alt = _('My Comments')
    image_class = 'rb-icon rb-icon-datagrid-comment-draft'
    shrink = True

    #: A mapping of computed statuses to icon CSS classes.
    #:
    #: Version Added:
    #:     7.1
    _ICON_CLASSES: Final[Mapping[str, str]] = {
        'has-draft-review': 'rb-icon-datagrid-comment-draft',
        'has-review': 'rb-icon-datagrid-comment',
        'has-ship-it': 'rb-icon-datagrid-comment-shipit',
    }

    #: A mapping of computed statuses to image alt text.
    #:
    #: Version Added:
    #:     7.1
    _IMAGE_ALTS: Final[Mapping[str, StrPromise]] = {
        'has-draft-review': _('Comments drafted'),
        'has-review': _('Comments published'),
        'has-ship-it': _('Comments published. Ship it!'),
    }

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
        """Add additional queries to the queryset.

        This will add subqueries for determining whether there are
        posted reviews, draft reviews, or Ship It! reviews.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the DataGrid instance.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting augmented QuerySet.
        """
        user = state.datagrid.request.user

        if user.is_anonymous:
            return queryset

        query_dict = {
            'user_id': str(user.pk),
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

    def render_data(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request being rendered for this row.
        """
        info = self.get_raw_object_value(state, obj)

        if not info:
            return mark_safe('')

        status = info['status']

        return format_html(
            '<div class="rb-icon {}" title="{}"></div>',
            self._ICON_CLASSES[status],
            self._IMAGE_ALTS[status],
        )

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> Mapping[str, Any]:
        """Return the raw value for review status.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request for the row.

        Returns:
            dict:
            Information on the review status.
        """
        user = state.datagrid.request.user

        if user.is_anonymous or obj.mycomments_my_reviews == 0:
            return {}

        has_draft_reviews = bool(getattr(obj, 'mycomments_private_reviews'))
        has_shipit_reviews = bool(getattr(obj, 'mycomments_shipit_reviews'))
        status: str = ''

        # Priority is ranked in the following order:
        #
        # 1) Non-public (draft) reviews
        # 2) Public reviews marked "Ship It"
        # 3) Public reviews not marked "Ship It"
        if has_draft_reviews:
            status = 'has-draft-review'
        elif has_shipit_reviews:
            status = 'has-ship-it'
        else:
            status = 'has-review'

        return {
            'has_draft_reviews': has_draft_reviews,
            'has_ship_its': has_shipit_reviews,
            'status': status,
        }


class NewUpdatesColumn(Column):
    """Indicates if there are new updates on a review request.

    This will show an icon if the review request has had any new updates
    or reviews since the user last saw it.
    """

    detailed_label = _('New Updates')
    image_alt = _('New Updates')
    image_class = 'rb-icon rb-icon-new-updates'
    shrink = True

    def render_data(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The group or review request being rendered for this row.
        """
        new_review_count = self.get_raw_object_value(state, obj)

        if new_review_count > 0:
            return format_html(
                '<div class="{}" title="{}"></div>',
                self.image_class, self.image_alt,
            )

        return mark_safe('')

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> int:
        """Return the raw value for the new review count.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request for the row.

        Returns:
            int:
            The new review count for the review request.
        """
        # Review requests for un-authenticated users will not contain the
        # new_review_count attribute.
        return getattr(obj, 'new_review_count', 0)


class PendingCountColumn(Column):
    """Shows the pending number of review requests for a user or group.

    This will show the pending number of review requests for the given
    review group or user. It only applies to group or user lists.
    """

    def augment_queryset_for_data(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
        **kwargs,
    ) -> QuerySet:
        """Augment a queryset for data-rendering purposes.

        This will count the number of accessible open review requests.

        Version Added:
            5.0.7

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the DataGrid instance.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

            **kwargs (dict):
                Additional keyword arguments for future expansion.

        Returns:
            django.db.models.query.QuerySet:
            The resulting augmented QuerySet.
        """
        return queryset.annotate(
            column_pending_review_request_count=Count(
                'review_requests',
                filter=(Q(review_requests__public=True) &
                        Q(review_requests__status='P'))))

    def render_data(
        self,
        state: StatefulColumn,
        obj: Group,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the datagrid.

            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML.
        """
        return escape(str(self.get_raw_object_value(state, obj)))

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: Group,
    ) -> int:
        """Return the raw value for the pending review request count.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.Group):
                The review request for the row.

        Returns:
            int:
            The pending review request count.
        """
        return getattr(obj, 'column_pending_review_request_count', 0)


class PeopleColumn(Column):
    """Shows the list of people requested to review the review request."""

    label = _('People')
    detailed_label = _('Target People')
    sortable = False
    shrink = False

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
        """Add additional queries to the queryset.

        This will pre-fetch the reviewers for each review request.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        return queryset.prefetch_related('target_people')

    def render_data(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the datagrid.

            obj (reviewboard.reviews.models.review_request.ReviewRequest):
                The review request.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML.
        """
        return escape(' '.join(
            user.username
            for user in self.get_raw_object_value(state, obj)
        ))

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> Sequence[User]:
        """Return the list of reviewers.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request to return the value for.

        Returns:
            list of django.contrib.auth.models.User:
            The list of reviewers.
        """
        return list(obj.target_people.all())


class RepositoryColumn(Column):
    """Shows the name of the repository the review request's change is on."""

    field_name = 'repository'
    label = _('Repository')
    db_field = 'repository__name'
    css_class = 'repository-column'
    shrink = True
    sortable = True
    link = False

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
        """Add additional queries to the queryset.

        This will include the repository for each review request.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        return queryset.select_related('repository')

    def render_data(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the datagrid.

            obj (reviewboard.reviews.models.review_request.ReviewRequest):
                The review request.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML.
        """
        if obj.repository_id is None:
            return mark_safe('')

        return escape(obj.repository.name)


class ReviewCountColumn(Column):
    """Shows the number of published reviews for a review request."""

    label = _('Reviews')
    detailed_label = _('Number of Reviews')
    shrink = True
    link = True

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
        """Add additional queries to the queryset.

        This will perform a subquery to return a public review count for
        each review request.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
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

    def render_data(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the datagrid.

            obj (reviewboard.reviews.models.review_request.ReviewRequest):
                The review request.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML for the column.
        """
        return escape(str(self.get_raw_object_value(state, obj)))

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> int:
        """Return the count value for the review request.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request to return the value for.

        Returns:
            int:
            The review count value.
        """
        return getattr(obj, 'publicreviewcount_count')

    @staticmethod
    def link_func(
        state: StatefulColumn,
        obj: ReviewRequest,
        value: str,
    ) -> str:
        """Return the link to the object in the column.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request for the row.

            value (str):
                The rendered data.

        Returns:
            str:
            The URL to link to.
        """
        return '%s#last-review' % obj.get_absolute_url()


class ReviewGroupStarColumn(BaseStarColumn):
    """Indicates if a review group is starred.

    The star is interactive, allowing the user to star or unstar the group.
    """

    starrable_model = Group


class ReviewRequestIDColumn(Column):
    """Displays the ID of the review request."""

    label = _('ID')
    detailed_label = _('Review Request ID')
    field_name = 'display_id'
    shrink = True
    sortable = True
    link = True

    def get_sort_field(
        self,
        state: StatefulColumn,
    ) -> str:
        """Return the model field for sorting this column.

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

        Returns:
            str:
            The sort field.
        """
        if state.datagrid.local_site:
            return 'local_id'
        else:
            return 'id'


class ReviewRequestStarColumn(BaseStarColumn):
    """Indicates if a review request is starred.

    The star is interactive, allowing the user to star or unstar the
    review request.
    """

    starrable_model = ReviewRequest


class ShipItColumn(Column):
    """Shows the "Ship It" and issue counts for a review request.

    If there are any issues still to resolve or verify, this will instead show
    information on those issues. Otherwise, it will show information on the
    number of Ship It! reviews filed.

    The following is the order of priority in which information is shown:

    1. Open issues with issues requiring verification
    2. Open issues
    3. Issues requiring verification
    4. Ship It! counts

    If showing a Ship It!, and if the latest review is older than the last
    update on the review request, the Ship It! will be marked as stale,
    helping visually indicate that it may need a re-review. The ARIA label
    reflects this as well.

    Version Changed:
        5.0:
        * Added ARIA attributes for the displayed output.
        * Ship It! counts are now shown as stale if older than the latest
          update to the review request.
    """

    detailed_label = _('Ship It!/Issue Counts')
    db_field = 'shipit_count'
    image_alt = _('Ship It!/Issue Counts')
    image_class = 'rb-icon rb-icon-datagrid-column-shipits-issues'
    shrink = True
    sortable = True

    def render_data(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the datagrid.

            obj (reviewboard.reviews.models.review_request.ReviewRequest):
                The review request.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML for the column.
        """
        info = self.get_raw_object_value(state, obj)

        open_issues = info['issue_open_count']
        verifying_issues = info['issue_verifying_count']
        shipit_count = info['shipit_count']

        if open_issues > 0 and verifying_issues > 0:
            return self._render_counts(
                [
                    {
                        'count': open_issues,
                        'title': _('Open issue count'),
                    },
                    {
                        'count': verifying_issues,
                        'css_class': 'issue-verifying-count',
                        'icon_name': 'issue-verifying',
                        'title': _('Verifying issue count'),
                    },
                ],
                aria_label=(
                    ngettext(
                        '%(open_issue_count)d issue opened, '
                        '%(verifying_issue_count)d requiring verification',
                        '%(open_issue_count)d issues opened, '
                        '%(verifying_issue_count)d requiring verification',
                        open_issues)
                    % {
                        'open_issue_count': open_issues,
                        'verifying_issue_count': verifying_issues,
                    }
                ))
        elif open_issues > 0:
            return self._render_counts(
                [{
                    'count': open_issues,
                }],
                aria_label=(
                    ngettext(
                        '%(open_issue_count)d issue opened',
                        '%(open_issue_count)d issues opened',
                        open_issues)
                    % {
                        'open_issue_count': open_issues,
                    }
                ))
        elif verifying_issues > 0:
            return self._render_counts(
                [{
                    'count': verifying_issues,
                    'icon_name': 'issue-verifying',
                }],
                aria_label=(
                    ngettext(
                        '%(verifying_issue_count)d issue requiring '
                        'verification',
                        '%(verifying_issue_count)d issues requiring '
                        'verification',
                        verifying_issues)
                    % {
                        'verifying_issue_count': verifying_issues,
                    }
                ))
        elif shipit_count > 0:
            container_css_classes = ['shipit-count-container']

            if info.get('shipits_stale'):
                container_css_classes.append('-is-stale')
                aria_label = ngettext(
                    '%(shipit_count)d Ship It! (New updates to review)',
                    "%(shipit_count)d Ship It's! (New updates to review)",
                    shipit_count)
            else:
                aria_label = ngettext(
                    '%(shipit_count)d Ship It!',
                    "%(shipit_count)d Ship It's!",
                    shipit_count)

            return self._render_counts(
                [{
                    'count': shipit_count,
                    'css_class': 'shipit-count',
                    'icon_name': 'shipit',
                }],
                aria_label=aria_label % {
                    'shipit_count': shipit_count,
                },
                container_css_class=' '.join(container_css_classes))
        else:
            return mark_safe('')

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> Mapping[str, Any]:
        """Return the summary and labels for a review request.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request to calculate summary information for.

        Returns:
            dict:
            The summary and labels for the review request.
        """
        review_request = obj
        open_issues = review_request.issue_open_count
        verifying_issues = review_request.issue_verifying_count
        shipit_count = review_request.shipit_count

        return {
            'issue_open_count': open_issues,
            'issue_verifying_count': verifying_issues,
            'shipit_count': shipit_count,
            'shipits_stale': bool(
                review_request.last_review_activity_timestamp and
                review_request.last_updated and
                (review_request.last_review_activity_timestamp <
                 review_request.last_updated)
            ),
        }

    def _render_counts(
        self,
        count_details: Sequence[Mapping[str, Any]],
        aria_label: str,
        container_css_class: str = 'issue-count-container',
    ) -> SafeString:
        """Render the counts for the column.

        This will render a container bubble in the column and render each
        provided count and icon in the bubble. This can be used for issues,
        Ship Its, or anything else we need down the road.

        Version Added:
            5.0:
            * Added ``aria_label``.
            * Removed the ``title`` key from ``count_details``.

        Args:
            count_details (list of dict):
                The list of details for the count. Each supports the following
                keys:

                Keys:
                    count (int):
                        The count to show for the indicator.

                    css_class (str, optional):
                        The CSS class to use for the indicator.

                    icon_name (str, optional):
                        The name of the icon to use for the indicator.

            aria_label (str):
                The label to use for the ``aria-label`` attribute and the
                ``title`` attribute.

            container_css_class (str, optional):
                The optional CSS class name for the outer container.

        Returns:
            django.utils.safestring.SafeString:
            The resulting HTML for the counts bubble.
        """
        # Note that the HTML is very whitespace-sensitive, so don't try to
        # change the templates to be nicely indented. The spacing is this way
        # for a reason.
        #
        # We also can't use format_html_join, unfortunately, as that doesn't
        # support keyword arguments.
        return format_html(
            '<div class="{container_css_class}" aria-label="{aria_label}"'
            ' title="{aria_label}">'
            '{count_html}'
            '</div>',
            aria_label=aria_label,
            container_css_class=container_css_class,
            count_html=mark_safe(''.join(
                format_html(
                    '<span class="{css_class}" aria-hidden="true">'
                    '<span class="rb-icon rb-icon-datagrid-{icon_name}">'
                    '</span>'
                    '{count}'
                    '</span>',
                    **{
                        'css_class': 'issue-count',
                        'icon_name': 'open-issues',
                        **count_detail,
                    },
                )
                for count_detail in count_details
            )))


class SummaryColumn(Column):
    """Shows the summary of a review request.

    This will also prepend the draft/submitted/discarded state, if any,
    to the summary.
    """

    label = _('Summary')
    css_class = 'summary'
    expand = True
    sortable = True
    link = True
    link_css_class = 'review-request-link'

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
        """Add additional queries to the queryset.

        This will perform subqueries to retrieve draft summaries and
        archive/mute states for the review requests, in order to show
        labels before the summaries.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        user = state.datagrid.request.user

        if user.is_anonymous:
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
                'user_id': str(user.pk),
            }
        })

    def render_data(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> SafeString:
        """Return the rendered contents of the column.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The state for the datagrid.

            obj (reviewboard.reviews.models.review_request.ReviewRequest):
                The review request.

        Returns:
            django.utils.safestring.SafeString:
            The rendered column.
        """
        info = self.get_raw_object_value(state, obj)
        summary = info['summary']
        labels = info['labels']

        label_status_map = {
            'completed': 'submitted',
        }

        result: list[str] = []

        for label_info in labels:
            status = label_info['status']

            result.append(format_html(
                '<label class="label-{}">{}</label>',
                label_status_map.get(status, status),
                label_info['label'],
            ))

        if summary:
            result.append(format_html('<span>{}</span>', summary))
        else:
            result.append(format_html('<span class="no-summary">{}</span>',
                                      _('No Summary')))

        return mark_safe(''.join(result))

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> Mapping[str, Any]:
        """Return the summary and labels for a review request.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request to calculate summary information for.

        Returns:
            dict:
            The summary and labels for the review request.
        """
        review_request = obj
        summary = review_request.summary
        labels: list[Mapping[str, str]] = []

        if review_request.submitter_id == state.datagrid.request.user.id:
            draft_summary = getattr(review_request, 'draft_summary')

            if draft_summary is not None:
                summary = draft_summary
                labels.append({
                    'label': gettext('Draft'),
                    'status': 'draft',
                })
            elif (not review_request.public and
                  review_request.status == ReviewRequest.PENDING_REVIEW):
                labels.append({
                    'label': gettext('Draft'),
                    'status': 'draft',
                })

        # review_request.visibility is not defined when the user is not
        # logged in.
        if state.datagrid.request.user.is_authenticated:
            visibility = getattr(review_request, 'visibility')

            if visibility == ReviewRequestVisit.ARCHIVED:
                labels.append({
                    'label': gettext('Archived'),
                    'status': 'archived',
                })
            elif visibility == ReviewRequestVisit.MUTED:
                labels.append({
                    'label': gettext('Muted'),
                    'status': 'muted',
                })

        if review_request.status == ReviewRequest.SUBMITTED:
            labels.append({
                'label': gettext('Completed'),
                'status': 'completed',
            })
        elif review_request.status == ReviewRequest.DISCARDED:
            labels.append({
                'label': gettext('Discarded'),
                'status': 'discarded',
            })

        return {
            'labels': labels,
            'summary': summary,
        }


class ReviewSummaryColumn(Column):
    """Shows the summary of the review request of a review.

    This does not (yet) prepend the draft/submitted/discarded state, if any,
    to the summary.
    """

    label = _('Review Request Summary')
    css_class = 'summary'
    expand = True
    sortable = True
    link = True
    link_css_class = 'review-request-link'

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
        """Add additional queries to the queryset.

        This will load the review requests along with each review.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        return queryset.select_related('review_request')

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: Review,
    ) -> str:
        """Return the raw value for review summary.

        This will fetch the summary from the associated review request.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.Review):
                The review being rendered.

        Returns:
            str:
            The summary of the associated review request.
        """
        return obj.review_request.summary


class ToMeColumn(Column):
    """Indicates if the user is requested to review the change.

    This will show an indicator if the user is on the Target People reviewers
    list.
    """

    label = '\u00BB'
    detailed_label = _('To Me')
    detailed_label_html = _('\u00BB To Me')
    shrink = True

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
        """Add additional queries to the queryset.

        This will load the PKs of the review requests directed to the
        user and store them as state on the column for rendering.

        Args:
            state (djblets.datagrid.grids.StatefulColumn):
                The column state.

            queryset (django.db.models.query.QuerySet):
                The queryset to augment.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        user = state.datagrid.request.user

        if user.is_authenticated:
            pks = set(
                user.directed_review_requests
                .filter(pk__in=state.datagrid.id_list)
                .values_list('pk', flat=True)
            )
        else:
            pks = set()

        state.extra_data['all_to_me'] = pks

        return queryset

    def render_data(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> SafeString:
        """Return the rendered contents of the column.

        If the object was directed to the user, an indicator will be
        shown.

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request the column applies to.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML.
        """
        if self.get_raw_object_value(state, obj):
            return format_html(
                '<div title="{}"><b>&raquo;</b></div>',
                self.detailed_label,
            )

        return mark_safe('')

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> bool:
        """Return the "to me" state as a boolean.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request for the row.

        Returns:
            bool:
            ``True`` if the column was directed to the user. ``False`` if
            it was not.
        """
        return obj.pk in state.extra_data['all_to_me']


class DiffSizeColumn(Column):
    """Indicates line add/delete counts for the latest diffset."""

    label = _('Diff Size')
    shrink = True

    def render_data(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> SafeString:
        """Return the rendered contents of the column.

        This will format HTML showing the diff's insert and delete
        line counts.

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request the column applies to.

        Returns:
            django.utils.safestring.SafeString:
            The rendered HTML.
        """
        counts = self.get_raw_object_value(state, obj)

        if counts:
            insert_count = counts.get('raw_insert_count')
            delete_count = counts.get('raw_delete_count')
            result: list[SafeString] = []

            if insert_count:
                result.append(format_html(
                    '<span class="diff-size-column insert">+{}</span>',
                    insert_count,
                ))

            if delete_count:
                result.append(format_html(
                    '<span class="diff-size-column delete">-{}</span>',
                    delete_count,
                ))

            if result:
                return mark_safe('&nbsp;'.join(result))

        return mark_safe('')

    def get_raw_object_value(
        self,
        state: StatefulColumn,
        obj: ReviewRequest,
    ) -> Mapping[str, int] | None:
        """Return the raw value for the diff size information.

        This will return the line count information for the diffset.

        Version Added:
            7.1

        Args:
            state (djblets.datagrids.grids.StatefulColumn):
                The state for the DataGrid instance.

            obj (reviewboard.reviews.models.ReviewRequest):
                The review request for the row.

        Returns:
            dict:
            The list of diff size information.
        """
        if obj.repository_id is not None:
            diffset_history = obj.diffset_history
            assert diffset_history is not None

            diffsets = list(diffset_history.diffsets.all())

            if diffsets:
                return diffsets[-1].get_total_line_counts()

        return None

    def augment_queryset(
        self,
        state: StatefulColumn,
        queryset: QuerySet,
    ) -> QuerySet:
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
