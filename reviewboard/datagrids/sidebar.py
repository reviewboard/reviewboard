from __future__ import unicode_literals

from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils import six
from django.utils.six.moves.urllib.parse import urlencode

from reviewboard.site.urlresolvers import local_site_reverse


class BaseSidebarItem(object):
    """Base class for an item on the sidebar of a datagrid.

    Items can optionally have labels and counts associated with them.
    Depending on the subclass, it may also be able to nest items.

    They may also have custom templates, for more advanced rendering.

    See SidebarItem and BaseSidebarSection for the common types of sidebar
    items.
    """

    template_name = None
    label = None
    icon_name = None
    view_id = None
    view_args = None
    css_classes = None

    def __init__(self, sidebar, datagrid):
        """Initialize the sidebar item."""
        self.sidebar = sidebar
        self.datagrid = datagrid

    def get_url(self):
        """Return the URL used when clicking the item.

        By default, this builds a URL to the parent datagrid using
        the ``view_id`` and ``view_args`` attributes. If they are not
        set, then the item won't be clickable.
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
        """
        return None

    def is_visible(self):
        """Return whether the item is visible.

        By default, an item is visible. Subclasses can override this to
        control visibility.
        """
        return True

    def is_active(self):
        """Return whether the item is currently active.

        The item will be active if the current page matches the URL
        associated with the item.
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
        """Render the item."""
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

        return render_to_string(self.template_name,
                                RequestContext(self.datagrid.request, context))

    def get_extra_context(self):
        """Return extra context for the render."""
        return {}


class BaseSidebarSection(BaseSidebarItem):
    """Base class for a section of items on the sidebar.

    Subclasses can override this to define a section and provide items
    listed in the section.

    Sections can optionally be clickable and display a count.
    """

    template_name = 'datagrids/sidebar_section.html'

    def __init__(self, *args, **kwargs):
        """Initialize the section."""
        super(BaseSidebarSection, self).__init__(*args, **kwargs)

        self.items = list(self.get_items())

    def get_items(self):
        """Return the items displayed in this section.

        Subclasses must override this and return or yield the items
        to be displayed.
        """
        raise NotImplementedError

    def is_visible(self):
        """Return whether the section is visible.

        By default, a section is visible if it has any item classes
        registered.
        """
        return len(self.items) > 0

    def get_extra_context(self):
        """Return extra context for the section."""
        return {
            'items': self.items,
        }


class SidebarNavItem(BaseSidebarItem):
    """A typical navigation link item on the sidebar.

    This is the standard type of item added to sections on a sidebar.
    It will automatically generate a link to the dashboard view matching
    ``view_id`` and ``view_args``, and display the provided count.
    """

    template_name = 'datagrids/sidebar_nav_item.html'

    def __init__(self, section, label, icon_name=None, view_id=None,
                 view_args=None, count=None, url=None, url_name=None,
                 css_classes=None):
        """Initialize the item."""
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
        """Return the URL for the item."""
        if self.url:
            return self.url
        elif self.url_name:
            return local_site_reverse(self.url_name,
                                      request=self.datagrid.request)
        else:
            return super(SidebarNavItem, self).get_url()

    def get_count(self):
        """Return the count provided in the constructor."""
        return self.count


class Sidebar(object):
    """Provides a sidebar for a datagrid.

    A sidebar can have several item classes added to it of various types.
    These will be instantiated and rendered when rendering the datagrid.
    """

    def __init__(self, item_classes, default_view_id=None, css_classes=[]):
        """Initialize the sidebar."""
        self._item_classes = []
        self.css_classes = css_classes
        self.default_view_id = default_view_id

        for item_cls in item_classes:
            self.add_item(item_cls)

    def add_item(self, item_cls):
        """Add an item class to the sidebar."""
        self._item_classes.append(item_cls)

    def remove_item(self, item_cls):
        """Remove an item class from the sidebar."""
        self._item_classes.remove(item_cls)

    def get_items(self, datagrid):
        """Instantiate and returns all items on the sidebar."""
        return [
            item_cls(self, datagrid)
            for item_cls in self._item_classes
        ]


class DataGridSidebarMixin(object):
    """A mixin for datagrids using a sidebar.

    This is meant to be used along with Sidebar. It will initialize the
    sidebar, providing instances of all the items for the template.
    """

    def load_extra_state(self, *args, **kwargs):
        """Compute any extra state for the sidebar."""
        result = super(DataGridSidebarMixin, self).load_extra_state(
            *args, **kwargs)

        self.sidebar_items = self.sidebar.get_items(self)

        return result
