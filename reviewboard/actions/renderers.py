"""Base support for action renderers.

Version Added:
    7.1
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

if TYPE_CHECKING:
    from typing import Any, ClassVar

    from django.http import HttpRequest
    from django.template import Context
    from django.utils.safestring import SafeString
    from typelets.django.json import SerializableDjangoJSONDict

    from reviewboard.actions.base import BaseAction


logger = logging.getLogger(__name__)


class BaseActionRenderer:
    """Base class for an action renderer.

    Action renderers are responsible for rendering an action and providing
    any setup necessary for a client-side JavaScript view.

    Renderer classes can be passed to an action during rendering or set as
    the default for an action. Renderers don't need to be centrally registered,
    and any action implementation is free to construct custom renderers for
    their needs.

    Version Added:
        7.1
    """

    #: The name of the template to use for rendering action JavaScript.
    js_template_name: ClassVar[str] = 'actions/action_view.js'

    #: The class to instantiate for the JavaScript view.
    js_view_class: ClassVar[str] = 'RB.Actions.ActionView'

    #: The name of the template to use when rendering.
    template_name: ClassVar[str | None] = None

    ######################
    # Instance variables #
    ######################

    #: The action being rendered.
    action: BaseAction

    def __init__(
        self,
        *,
        action: BaseAction,
    ) -> None:
        """Initialize the renderer.

        Args:
            action (reviewboard.actions.base.BaseAction):
                The action being renderered.
        """
        self.action = action

    def get_js_view_data(
        self,
        *,
        context: Context,
    ) -> SerializableDjangoJSONDict:
        """Return data to be passed to the rendered JavaScript view.

        Subclasses can override this to provide custom data for a view.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            A dictionary of options to pass to the view instance.
        """
        return {}

    def get_extra_context(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> dict[str, Any]:
        """Return extra template context for the action.

        Subclasses can override this to provide additional context needed by
        the template for the action.

        By default, this returns the action's context for the template.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            Extra context to use when rendering the action's template.
        """
        return self.action.get_extra_context(request=request,
                                             context=context)

    def render(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> SafeString:
        """Render the action.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            django.utils.safestring.SafeString:
            The rendered action HTML.
        """
        action = self.action

        # NOTE: BaseAction.template_name is deprecated. This is here
        #       for compatibility until that's removed in Review Board 9.
        template_name = action.template_name or self.template_name

        if template_name:
            extra_context = {
                'action': action,
                'action_renderer': self,
                **self.get_extra_context(request=request,
                                         context=context),
            }

            with context.update(extra_context):
                try:
                    return render_to_string(
                        template_name=template_name,
                        context=cast(dict, context.flatten()),
                        request=request)
                except Exception as e:
                    logger.exception('Error rendering action %r, renderer %r: '
                                     '%s',
                                     action, self, e)

        return mark_safe('')

    def render_js(
        self,
        *,
        request: HttpRequest,
        context: Context,
        extra_js_view_data: (SerializableDjangoJSONDict | None) = None,
    ) -> SafeString:
        """Render the action's JavaScript.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

            extra_js_view_data (dict, optional):
                Optional extra data to pass to the JavaScript action view's
                constructor.

        Returns:
            django.utils.safestring.SafeString:
            The rendered action JavaScript.
        """
        action = self.action

        # NOTE: These attributes on BaseModel are deprecated. This is
        #       here for compatibility until those are removed in
        #       Review Board 9.
        js_view_class = action.js_view_class or self.js_view_class

        # Build the data for the JavaScript view.
        js_view_data = self.get_js_view_data(context=context)
        js_view_data['attachmentPointID'] = action.attachment

        if extra_js_view_data:
            js_view_data.update(extra_js_view_data)

        extra_context = {
            'action': action,
            'action_renderer': self,
            'js_model_class': action.js_model_class,
            'js_view_class': js_view_class,
            'js_view_data': js_view_data,
        }

        with context.update(extra_context):
            try:
                return render_to_string(
                    template_name=self.js_template_name,
                    context=cast(dict, context.flatten()),
                    request=request)
            except Exception as e:
                logger.exception('Error rendering JavaScript for action '
                                 '%r, renderer %r: %s',
                                 action, self, e)

                return mark_safe('')


class DefaultActionRenderer(BaseActionRenderer):
    """Default renderer for actions.

    This is the default renderer used for actions that don't otherwise specify
    their own default. It will render as a menu item.
    """

    template_name = 'actions/action.html'
    js_view_class = 'RB.Actions.ActionView'

    def get_js_view_data(
        self,
        *,
        context: Context,
    ) -> SerializableDjangoJSONDict:
        """Return data to be passed to the JavaScript view.

        By default, for backwards-compatibility, this will call
        :py:meth:`BaseAction.get_js_view_data()
        <reviewboard.actions.base.BaseAction.get_js_view_data>`. This method is
        deprecated, and will be removed in Review Board 9.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            A dictionary of options to pass to the view instance.
        """
        # This will be {} by default. In Review Board 9, we can drop this call.
        return self.action.get_js_view_data(context=context)


class BaseActionGroupRenderer(BaseActionRenderer):
    """Base class for an action group renderer.

    Group action renderers are responsible for rendering the group and any
    items within it.

    This must be subclassed to specify rendering behavior for the group and
    a default renderer class for items within the group.

    Version Added:
        7.1
    """

    #: The default class for rendering any items within the group.
    default_item_renderer_cls: type[BaseActionRenderer] = DefaultActionRenderer


class DefaultActionGroupRenderer(BaseActionGroupRenderer):
    """Default class for an action group renderer.

    This is a simple renderer that just displays the children of a group.
    In most cases, an action group will want to provide a more suitable
    renderer than this.

    Version Added:
        7.1
    """

    template_name = 'actions/group_action.html'


class ButtonActionRenderer(BaseActionRenderer):
    """Action renderer that renders as a button.

    This will render a button that reflects and activates the action.

    Version Added:
        7.1
    """

    js_view_class = 'RB.Actions.ButtonActionView'
    template_name = 'actions/button_action.html'


class MenuItemActionRenderer(BaseActionRenderer):
    """Action renderer that renders as a menu item.

    This will render the action as an Ink menu item, intended for use within
    a :py:class:`ActionGroupMenuRenderer`.

    Version Added:
        7.1
    """

    js_view_class = 'RB.Actions.MenuItemActionView'
    template_name = 'actions/action.html'


class MenuActionGroupRenderer(BaseActionGroupRenderer):
    """Group action renderer that renders as a menu of items.

    This will render the group as an Ink menu, with each item in the group
    as a registered Ink menu item available to the menu.

    Version Added:
        7.1
    """

    default_item_renderer_cls: type[BaseActionRenderer] = \
        MenuItemActionRenderer
    js_view_class = 'RB.Actions.MenuActionView'
    template_name = 'actions/menu_action.html'


class DetailedMenuItemActionRenderer(MenuItemActionRenderer):
    """Action renderer that renders as a detailed menu item.

    Detailed menu items have an icon, verbose label, and a description,
    helping provide more guidance beyond a standard menu item.

    Version Added:
        7.1
    """

    template_name = 'actions/detailed_menuitem_action.html'


class DetailedMenuActionGroupRenderer(MenuActionGroupRenderer):
    """Group action renderer that renders as detailed menu items.

    Detailed menu items have an icon, verbose label, and a description,
    helping provide more guidance beyond a standard menu item.

    Version Added:
        7.1
    """

    default_item_renderer_cls: type[BaseActionRenderer] = \
        DetailedMenuItemActionRenderer
