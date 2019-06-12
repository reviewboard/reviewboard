"""Sidebar item management for datagrids."""

from __future__ import unicode_literals

from django.utils import six
from django.utils.six.moves.urllib.parse import urlencode
from djblets.util.compat.django.template.loader import render_to_string

from reviewboard.site.urlresolvers import local_site_reverse


class BaseSidebarItem(object):
    """Base class for an item on the sidebar of a datagrid.

    Items can optionally have labels and counts associated with them.
    Depending on the subclass, it may also be able to nest items.

    They may also have custom templates, for more advanced rendering.

    See :py:class:`SidebarNavItem` and :py:class:`BaseSidebarSection` for the
    common types of sidebar items.

    Attributes:
        datagrid (djblets.datagrid.grids.DataGrid):
            The datagrid containing this item.

        sidebar (Sidebar):
            The sidebar containing this item.
    """

    #: The template to use for rendering this item in the sidebar.
    template_name = None

    #: The displayed label for the item.
    label = None

    #: The name of the optional CSS icon to use beside the label.
    icon_name = None

    #: The datagrid "view" to link to when clicking this item.
    #:
    #: This corresponds to the ``?view=`` parameter passed to the datagrid
    #: page.
    view_id = None

    #: Additional key/values to pass to the URL when clicking this item.
    #:
    #: If provided, this must be a dictionary of keys and values for the
    #: URL. The keys and values will be automatically URL-encoded.
    view_args = None

    #: Additional CSS classes to include for the item.
    css_classes = None

    def __init__(self, sidebar, datagrid):
        """Initialize the sidebar item.

        Args:
            sidebar (Sidebar):
                The sidebar containing this item.

            datagrid (djblets.datagrid.grids.DataGrid):
                The datagrid containing this item.
        """
        self.sidebar = sidebar
        self.datagrid = datagrid

    def get_url(self):
        """Return the URL used when clicking the item.

        By default, this builds a URL to the parent datagrid using
        the ``view_id`` and ``view_args`` attributes. If they are not
        set, then the item won't be clickable.

        Returns:
            unicode:
            The URL to the dashboard view represented by this item.
        """
        if not self.view_id and not self.view_args:
            return None

        if self.view_args:
            url_args = self.view_args.copy()
        else:
            url_args = {}

        if self.view_id:
            url_args['view'] = self.view_id

        return '%s?%s' % (self.datagrid.request.path, urlencode(url_args))

    def get_count(self):
        """Return the count shown for this item.

        By default, this shows nothing. Subclasses can override to display
        a count.

        Returns:
            int:
            The count to display beside the item, or ``None`` if no count
            should be displayed.
        """
        return None

    def is_visible(self):
        """Return whether the item is visible.

        By default, an item is visible. Subclasses can override this to
        control visibility.

        Returns:
            bool:
            ``True`` if the item is visible. ``False`` if it's hidden.
        """
        return True

    def is_active(self):
        """Return whether the item is currently active.

        The item will be active if the current page matches the URL
        associated with the item.

        Returns:
            bool:
            ``True`` if the item represents the active page. ``False`` if it
            does not.
        """
        if self.view_id is None:
            return False

        request = self.datagrid.request
        view_id = request.GET.get('view', self.sidebar.default_view_id)

        if view_id != self.view_id:
            return False

        if self.view_args:
            for key, value in six.iteritems(self.view_args):
                if request.GET.get(key) != value:
                    return False

        return True

    def render(self):
        """Render the item.

        Returns:
            django.utils.safestring.SafeText:
            The rendered HTML for the item.
        """
        count = self.get_count()
        context = {
            'datagrid': self.datagrid,
            'label': self.label,
            'icon_name': self.icon_name or '',
            'view_id': self.view_id,
            'view_args': self.view_args,
            'count': count,
            'has_count': count is not None,
            'url': self.get_url(),
            'active': self.is_active(),
            'css_classes': self.css_classes or [],
        }
        context.update(self.get_extra_context())

        return render_to_string(template_name=self.template_name,
                                context=context,
                                request=self.datagrid.request)

    def get_extra_context(self):
        """Return extra context for the render.

        Returns:
            dict:
            A dictionary of additional template context. By default, this is
            empty.
        """
        return {}


class BaseSidebarSection(BaseSidebarItem):
    """Base class for a section of items on the sidebar.

    Subclasses can override this to define a section and provide items
    listed in the section.

    Sections can optionally be clickable and display a count.
    """

    template_name = 'datagrids/sidebar_section.html'

    def __init__(self, *args, **kwargs):
        """Initialize the section.

        Args:
            *args (tuple):
                Positional arguments to pass to the parent class.

            **kwargs (dict):
                Keyword arguments to pass to the parent class.
        """
        super(BaseSidebarSection, self).__init__(*args, **kwargs)

        self.items = list(self.get_items())

    def get_items(self):
        """Return the items displayed in this section.

        Subclasses must override this and return or yield the items
        to be displayed.

        Returns:
            list of BaseSidebarItem:
            The list of items to display in the section.
        """
        raise NotImplementedError

    def is_visible(self):
        """Return whether the section is visible.

        By default, a section is visible if it has any item classes
        registered. Subclasses can override this to provide more specific
        logic.

        Returns:
            bool:
            ``True`` if the section is visible. ``False`` if it's hidden.
        """
        return len(self.items) > 0

    def get_extra_context(self):
        """Return extra context for the section.

        Subclasses that override this method must call the parent method.

        Returns:
            dict:
            Additional template context for the rendering of the section.
        """
        return {
            'items': self.items,
        }


class SidebarNavItem(BaseSidebarItem):
    """A typical navigation link item on the sidebar.

    This is the standard type of item added to sections on a sidebar. An item
    can contain an explicit URL or a resolvable URL name to link to. If not
    provided, the current datagrid page's URL will be used along with query
    arguments built from :py:attr:`view_id` and :py:attr:`view_args`.
    """

    template_name = 'datagrids/sidebar_nav_item.html'

    def __init__(self, section, label, icon_name=None, view_id=None,
                 view_args=None, count=None, url=None, url_name=None,
                 css_classes=None):
        """Initialize the item.

        Args:
            section (BaseSidebarSection):
                The section that should contain this item.

            label (unicode):
                The displayed label for this item.

            icon_name (unicode, optional):
                The name of the optional CSS icon to display beside the label.

            view_id (unicode, optional):
                The ID of the optional datagrid view to display when clicking
                the item. See :py:attr:`BaseSidebarItem.view_id` for more
                information.

            view_args (unicode, optional)
                Keys/values to display in the URL when clicking the item. See
                :py:attr:`BaseSidebarItem.view_args` for more information.

            count (int, optional):
                The count to display beside the label.

            url (unicode, optional):
                The optional URL to navigate to when clicked.

            url_name (unicode, optional):
                The optional URL name to resolve and navigate to when clicked.

            css_classes (list of unicode, optional):
                Additional CSS classes to apply to the item.
        """
        super(SidebarNavItem, self).__init__(section.sidebar, section.datagrid)

        self.label = label
        self.icon_name = icon_name
        self.view_id = view_id
        self.view_args = view_args
        self.count = count
        self.css_classes = css_classes
        self.url = url
        self.url_name = url_name

    def get_url(self):
        """Return the URL for the item.

        If :py:attr:`url` is set, that URL will be returned directly.

        If :py:attr:`url_name` is set instead, it will be resolved relative
        to any Local Site that might be accessed and used as the URL. Note that
        the URL can't require any parameters.

        If not explicit URL or name is provided, the current page is used along
        with query parameters built from :py:attr:`view_id` and
        :py:attr:`view_args`.

        Returns:
            unicode:
            The URL to navigate to when clicked.
        """
        if self.url:
            return self.url
        elif self.url_name:
            return local_site_reverse(self.url_name,
                                      request=self.datagrid.request)
        else:
            return super(SidebarNavItem, self).get_url()

    def get_count(self):
        """Return the count provided in the constructor.

        Subclasses can override this if they need additional logic to compute
        a count.

        Returns:
            int:
            The count to display beside the label, or ``None`` if no count
            should be shown.
        """
        return self.count


class Sidebar(object):
    """Provides a sidebar for a datagrid.

    A sidebar can have several item classes added to it of various types.
    These will be instantiated and rendered when rendering the datagrid.
    """

    def __init__(self, item_classes, default_view_id=None, css_classes=[]):
        """Initialize the sidebar.

        Args:
            item_classes (list of type):
                The list of :py:class:`BaseSidebarItem` subclasses to include
                by default in the sidebar.

            default_view_id (unicode, optional):
                The default "view" of the datagrid to display. This corresponds
                to a registered :py:attr:`BaseSidebarItem.view_id`.

            css_classes (list of unicode):
                The list of additional CSS classes to apply to the sidebar.
        """
        self._item_classes = []
        self.css_classes = css_classes
        self.default_view_id = default_view_id

        for item_cls in item_classes:
            self.add_item(item_cls)

    def add_item(self, item_cls):
        """Add an item class to the sidebar.

        Args:
            item_cls (type):
                The item to add to the sidebar. This must be a subclass of
                :py:class:`BaseSidebarItem`.
        """
        self._item_classes.append(item_cls)

    def remove_item(self, item_cls):
        """Remove an item class from the sidebar.

        Args:
            item_cls (type):
                The item to remove from the sidebar. This must be a subclass
                of :py:class:`BaseSidebarItem`.
        """
        self._item_classes.remove(item_cls)

    def get_items(self, datagrid):
        """Instantiate and return all items on the sidebar.

        Args:
            datagrid (djblets.datagrid.grids.DataGrid):
                The datagrid instance to associate with each item.

        Returns:
            list of DataGridSidebarItem:
            The list of instantiated items.
        """
        return [
            item_cls(self, datagrid)
            for item_cls in self._item_classes
        ]


class DataGridSidebarMixin(object):
    """A mixin for datagrids using a sidebar.

    This is meant to be used along with :py:class:`Sidebar`. It will initialize
    the sidebar, providing instances of all the items for the template.
    """

    def load_extra_state(self, *args, **kwargs):
        """Compute any extra state for the sidebar.

        This will set :py:attr:`sidebar_items` on the datagrid to a list of
        instantiated items.

        Args:
            *args (tuple):
                Additional positional arguments passed to the method.

            **kwargs (dict):
                Additional keyword arguments passed to the method.

        Returns:
            object:
            The result from the parent method on the datagrid.
        """
        result = super(DataGridSidebarMixin, self).load_extra_state(
            *args, **kwargs)

        self.sidebar_items = self.sidebar.get_items(self)

        return result
