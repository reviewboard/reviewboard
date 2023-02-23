"""Hooks for adding info the the dashboard."""

from __future__ import annotations

from djblets.extensions.hooks import (DataGridColumnsHook,
                                      ExtensionHook,
                                      ExtensionHookPoint)

from reviewboard.datagrids.grids import (DashboardDataGrid,
                                         UserPageReviewRequestDataGrid)


class DataGridSidebarItemsHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for adding items to the sidebar of a datagrid.

    Extensions can use this hook to plug new items into the sidebar of
    any datagrid supporting sidebars.

    The items can be any subclass of
    :py:class:`reviewboard.datagrids.sidebar.BaseSidebarItem`, including the
    built-in :py:class:`reviewboard.datagrids.sidebar.BaseSidebarSection` and
    built-in :py:class:`reviewboard.datagrids.sidebar.SidebarNavItem`.
    """

    def initialize(self, datagrid, item_classes):
        """Initialize the hook.

        This will register the provided datagrid sidebar item classes in the
        provided datagrid.

        Args:
            datagrid (type):
                The datagrid class to register the items on. The datagrid
                must have a sidebar, or an error will occur.

            item_classes (list of type):
                The list of item classes to register on the datagrid's
                sidebar. Each must be a subclass of
                :py:class:`~reviewboard.datagrids.sidebar.BaseSidebarItem`.

        Raises:
            ValueError:
                A datagrid was provided that does not contain a sidebar.
        """
        if not hasattr(datagrid, 'sidebar'):
            raise ValueError('The datagrid provided does not have a sidebar')

        self.datagrid = datagrid
        self.item_classes = item_classes

        for item in item_classes:
            datagrid.sidebar.add_item(item)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each item class from the datagrid's sidebar.
        """
        for item in self.item_classes:
            self.datagrid.sidebar.remove_item(item)


# We don't use the ExtensionHookPoint metaclass here, because we actually
# want these to register in the base DataGridColumnsHook point.
class DashboardColumnsHook(DataGridColumnsHook):
    """A hook for adding custom columns to the dashboard.

    Extensions can use this hook to provide one or more custom columns
    in the dashboard. These columns can be added by users, moved around,
    and even sorted, like other columns.

    Each value passed to ``columns`` must be an instance of
    :py:class:`djblets.datagrid.grids.Column`.

    It also must have an ``id`` attribute set. This must be unique within
    the dashboard. It is recommended to use a vendor-specific prefix to the
    ID, in order to avoid conflicts.
    """

    def initialize(self, columns):
        """Initialize the hook.

        This will register each of the provided columns on the Dashboard.

        Args:
            columns (list of djblets.datagrid.grids.Column):
                The list of column instances to register on the Dashboard.
        """
        super(DashboardColumnsHook, self).initialize(DashboardDataGrid,
                                                     columns)


class DashboardSidebarItemsHook(DataGridSidebarItemsHook,
                                metaclass=ExtensionHookPoint):
    """A hook for adding items to the sidebar of the dashboard.

    Extensions can use this hook to plug new items into the sidebar of
    the dashboard. These will appear below the built-in items.

    The items can be any subclass of
    :py:class:`reviewboard.datagrids.sidebar.BaseSidebarItem`, including the
    built-in :py:class:`reviewboard.datagrids.sidebar.BaseSidebarSection` and
    built-in :py:class:`reviewboard.datagrids.sidebar.SidebarNavItem`.
    """

    def initialize(self, item_classes):
        """Initialize the hook.

        This will register the provided datagrid sidebar item classes in the
        Dashboard.

        Args:
            item_classes (list of type):
                The list of item classes to register on the datagrid's
                sidebar. Each must be a subclass of
                :py:class:`~reviewboard.datagrids.sidebar.BaseSidebarItem`.
        """
        super(DashboardSidebarItemsHook, self).initialize(DashboardDataGrid,
                                                          item_classes)


class UserPageSidebarItemsHook(DataGridSidebarItemsHook,
                               metaclass=ExtensionHookPoint):
    """A hook for adding items to the sidebar of the user page.

    Extensions can use this hook to plug new items into the sidebar of
    the user page. These will appear below the built-in items.

    The items can be any subclass of
    :py:class:`reviewboard.datagrids.sidebar.BaseSidebarItem`, including the
    built-in :py:class:`reviewboard.datagrids.sidebar.BaseSidebarSection` and
    built-in :py:class:`reviewboard.datagrids.sidebar.SidebarNavItem`.
    """

    def initialize(self, item_classes):
        """Initialize the hook.

        This will register the provided datagrid sidebar item classes in the
        user page's datagrid.

        Args:
            item_classes (list of type):
                The list of item classes to register on the datagrid's
                sidebar. Each must be a subclass of
                :py:class:`~reviewboard.datagrids.sidebar.BaseSidebarItem`.
        """
        super(UserPageSidebarItemsHook, self).initialize(
            UserPageReviewRequestDataGrid, item_classes)
