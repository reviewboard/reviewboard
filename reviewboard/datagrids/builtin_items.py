from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from reviewboard.datagrids.sidebar import (BaseSidebarItem,
                                           BaseSidebarSection, SidebarNavItem)


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

    def get_items(self):
        """Yield each of the items within this section."""
        profile = self.datagrid.profile
        site_profile = self.datagrid.site_profile

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

        groups = (
            self.datagrid.user.review_groups
            .filter(local_site=self.datagrid.local_site)
            .order_by('name'))
        seen_groups = set([group.name for group in groups])

        for item in self._add_groups(groups, view_id='to-group'):
            yield item

        starred_groups = (
            profile.starred_groups
            .filter(local_site=self.datagrid.local_site)
            .exclude(name__in=seen_groups)
            .order_by('name'))

        for item in self._add_groups(starred_groups,
                                     view_id='to-watched-group',
                                     icon_name='rb-icon-star-on'):
            yield item

    def _add_groups(self, groups, view_id, icon_name=None):
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

    def get_items(self):
        """Yield each of the items within this section."""
        request = self.datagrid.request

        groups = (
            self.datagrid.user.review_groups.accessible(request.user)
            .filter(local_site=self.datagrid.local_site)
            .order_by('name'))

        for group in groups:
            yield SidebarNavItem(self,
                                 label=group.name,
                                 url=group.get_absolute_url())
