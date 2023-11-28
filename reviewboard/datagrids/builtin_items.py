"""Built-in sidebar items for datagrids."""

from __future__ import annotations

from typing import Iterator, Optional, Sequence, TYPE_CHECKING

from django.utils.translation import gettext_lazy as _

from reviewboard.datagrids.sidebar import (BaseSidebarItem,
                                           BaseSidebarSection, SidebarNavItem)
from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from reviewboard.reviews.models import Group


class OverviewSection(BaseSidebarItem):
    """The "Overview" section on the Dashboard sidebar.

    This links to a Dashboard view showing all open incoming review requests
    listing the user directly as a reviewer, or listing a group the user is
    a member of and all open outgoing review requests made by the user.
    """

    template_name = 'datagrids/overview.html'
    label = _('Overview')
    view_id = 'overview'


class OutgoingSection(BaseSidebarSection):
    """The "Outgoing" section on the Dashboard sidebar.

    This displays two links: "All" and "Open".

    "All" links to a Dashboard view showing all outgoing review requests
    made by the user, including those that are closed.

    "Open" links to a Dashboard view showing only open outgoing review
    requests made by the user.
    """

    label = _('Outgoing')

    def get_items(self):
        """Yield each of the items within this section."""
        site_profile = self.datagrid.site_profile

        yield SidebarNavItem(self,
                             label=_('All'),
                             view_id='mine',
                             count=site_profile.total_outgoing_request_count)
        yield SidebarNavItem(self,
                             label=_('Open'),
                             view_id='outgoing',
                             count=site_profile.pending_outgoing_request_count)


class IncomingSection(BaseSidebarSection):
    """The "Incoming" section on the Dashboard sidebar.

    This displays three special links ("Open", "To Me", and "Starred"), and
    links for every group the user is a member of or has starred.

    "Open" links to a Dashboard view showing all open incoming review
    requests listing the user directly as a reviewer, or listing a group the
    user is a member of.

    "To Me" links to a Dashboard view showing all open incoming review
    requests listing the user directly as a reviewer.

    "Starred" links to a Dashboard view showing all review requests the
    user has starred. This will only show up if the user has any starred.

    Each group links to a Dashboard view showing all open review requests
    made to that group.
    """

    label = _('Incoming')

    def get_items(self) -> Iterator[SidebarNavItem]:
        """Yield each of the items within this section.

        Yields:
            reviewboard.datagrids.sidebar.SidebarNavItem:
            Each sidebar navigation item.
        """
        datagrid = self.datagrid
        profile = datagrid.profile
        local_site = datagrid.local_site
        site_profile = datagrid.site_profile

        yield SidebarNavItem(self,
                             label=_('Open'),
                             view_id='incoming',
                             count=site_profile.total_incoming_request_count)

        yield SidebarNavItem(self,
                             label=_('To Me'),
                             view_id='to-me',
                             count=site_profile.direct_incoming_request_count)

        if site_profile.starred_public_request_count > 0:
            yield SidebarNavItem(
                self,
                label=_('Starred'),
                view_id='starred',
                icon_name='rb-icon-star-on',
                count=site_profile.starred_public_request_count)

        only_fields = ('incoming_request_count', 'name', 'pk')

        groups = _get_groups(
            queryset=(
                datagrid.user.review_groups
                .only(*only_fields)
            ),
            local_site=local_site)

        seen_groups = {
            group.pk
            for group in groups
        }

        yield from self._add_groups(groups, view_id='to-group')

        if profile.has_starred_review_groups(local_site=local_site):
            yield from self._add_groups(
                _get_groups(
                    queryset=(
                        profile.starred_groups
                        .exclude(pk__in=seen_groups)
                        .only(*only_fields)
                    ),
                    local_site=local_site),
                view_id='to-watched-group',
                icon_name='rb-icon-star-on')

    def _add_groups(
        self,
        groups: Sequence[Group],
        view_id: str,
        icon_name: Optional[str] = None,
    ) -> Iterator[SidebarNavItem]:
        """Add groups to the sidebar.

        This will generate a sidebar navigation item for each group in the
        list.

        Args:
            groups (list of reviewboard.reviews.models.group.Group):
                The list of groups to add.

            view_id (str):
                The ID of the view to link to.

            icon_name (str, optional):
                The name of the icon to show.

        Yields:
            reviewboard.datagrids.sidebar.SidebarNavItem:
            Each group navigation item.
        """
        for i, group in enumerate(groups):
            name = group.name

            if i == 0:
                css_classes = ['new-subsection']
            else:
                css_classes = []

            yield SidebarNavItem(self,
                                 label=name,
                                 view_id=view_id,
                                 view_args={
                                     'group': name,
                                 },
                                 icon_name=icon_name,
                                 css_classes=css_classes,
                                 count=group.incoming_request_count)


class UserProfileItem(BaseSidebarItem):
    """Displays the profile for a user in the user page sidebar.

    This will display information such as the name, e-mail address,
    gravatar, and dates logged in and joined.
    """

    template_name = 'datagrids/sidebar_user_info.html'

    def get_extra_context(self):
        """Return extra data to include in the template render context."""
        request = self.datagrid.request
        user = self.datagrid.user

        return {
            'show_profile': user.is_profile_visible(request.user),
            'profile_user': user,
        }


class UserGroupsItem(BaseSidebarSection):
    """Displays the list of groups a user belongs to in the user page sidebar.

    Each group will be clickable, and will navigate to the corresponding
    group page.
    """

    label = _('Groups')
    css_classes = ['-is-desktop-only']

    def get_items(self) -> Iterator[SidebarNavItem]:
        """Yield each of the items within this section.

        Yields:
            reviewboard.datagrids.sidebar.SidebarNavItem:
            Each sidebar navigation item.
        """
        datagrid = self.datagrid

        groups = _get_groups(
            queryset=(
                datagrid.user.review_groups
                .accessible(datagrid.request.user)
                .only('local_site', 'name', 'pk')
            ),
            local_site=datagrid.local_site)

        for group in groups:
            yield SidebarNavItem(self,
                                 label=group.name,
                                 url=group.get_absolute_url())


def _get_groups(
    *,
    queryset: QuerySet[Group],
    local_site: Optional[LocalSite],
) -> Sequence[Group]:
    """Return review groups for usage in a datagrid sidebar.

    This takes a queryset, conditionally applies a Local Site filter if
    needed, and applies a sort Python-side, returning the list of results.

    Callers should take care to provide a queryset that performs any
    accessibility checks if needed, and to return the minimum number of
    fields used for the item in the sidebar (which must always include "name").

    Version Added:
        5.0.7

    Args:
        queryset (django.db.models.QuerySet):
            The queryset for review groups.

        local_site (reviewboard.site.models.LocalSite):
            The Local Site being viewed, if any.

    Returns:
        list of reviewboard.reviews.models.group.Group:
        The resulting list of sorted review groups.
    """
    local_site_q = LocalSite.objects.build_q(local_site, allow_all=False)

    if local_site_q:
        queryset = queryset.filter(local_site_q)

    return sorted(queryset,
                  key=lambda group: group.name)
