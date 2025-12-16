"""Base support for action renderers.

Version Added:
    7.1
"""

from __future__ import annotations

import logging
from typing import Literal, Optional, TYPE_CHECKING, Type, Union, cast

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from reviewboard.actions.errors import MissingActionRendererError

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, ClassVar, TypeAlias

    from django.http import HttpRequest
    from django.template import Context
    from django.utils.safestring import SafeString
    from typelets.django.json import SerializableDjangoJSONDict

    from reviewboard.actions.base import ActionPlacement, BaseAction


logger = logging.getLogger(__name__)


#: The type of an action group renderer for subgroups of groups.
#:
#: This can be a :py:class:`BaseActionGroupRenderer` subclass, the
#: string "self" to reuse the parent action renderer, or ``None`` to
#: prevent rendering.
#:
#: Version Added:
#:     7.1
ActionSubgroupRendererType: TypeAlias = Optional[Union[
    Type['BaseActionGroupRenderer'],
    Literal['self'],
]]


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

    #: The placement for the action.
    placement: ActionPlacement

    def __init__(
        self,
        *,
        action: BaseAction,
        placement: ActionPlacement,
    ) -> None:
        """Initialize the renderer.

        Args:
            action (reviewboard.actions.base.BaseAction):
                The action being renderered.

            placement (reviewboard.actions.base.ActionPlacement):
                The placement for the action.
        """
        self.action = action
        self.placement = placement

        assert placement in (action.placements or [])

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
        action = self.action
        placement = self.placement

        extra_context = action.get_extra_context(request=request,
                                                 context=context)
        extra_context.update({
            'action': action,
            'action_renderer': self,
            'attachment_point_id': placement.attachment,
            'dom_element_id': (
                placement.dom_element_id or
                action.get_dom_element_id() or
                f'action-{placement.attachment}-{action.action_id}'
            ),
            'has_parent': placement.parent_id is not None,
            'is_toplevel': placement.parent_id is None,
            'placement': placement,
        })

        return extra_context

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
            extra_context = self.get_extra_context(request=request,
                                                   context=context)

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
        js_view_data['attachmentPointID'] = self.placement.attachment

        if extra_js_view_data:
            js_view_data.update(extra_js_view_data)

        extra_context = self.get_extra_context(request=request,
                                               context=context)
        extra_context.update({
            'js_model_class': action.js_model_class,
            'js_view_class': js_view_class,
            'js_view_data': js_view_data,
        })

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

    #: The default class for rendering any non-group items within the group.
    default_item_renderer_cls: ClassVar[type[BaseActionRenderer]] = \
        DefaultActionRenderer

    #: The default class for rendering any sub-group items within the group.
    #:
    #: If unset (the default), then something else must supply a default
    #: renderer for subgroups of this group.
    #:
    #: This can be the string "self" to use this class as the renderer for
    #: subgroups.
    default_subgroup_renderer_cls: ClassVar[ActionSubgroupRendererType] = None

    def get_extra_context(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> dict[str, Any]:
        """Return extra template context for the action.

        This includes a ``children`` key containing the children for this
        action in the parent attachment point.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            Extra context to use when rendering the action's template.
        """
        extra_context = super().get_extra_context(request=request,
                                                  context=context)

        extra_context['children'] = [
            child
            for child in self.placement.child_actions
            if child.should_render(context=context)
        ]

        return extra_context

    def render_children(
        self,
        *,
        children: Iterable[BaseAction],
        context: Context,
        request: HttpRequest,
    ) -> SafeString:
        """Render the children in the group.

        This will iterate through all children in the group, rendering
        them using their provided renderer or the group's default renderer.
        The renderer chosen will depend on whether a child is a group action
        or a standard action.

        If this group should not be rendered, then no children will be
        rendered.

        Args:
            children (list of reviewboard.actions.base.BaseAction):
                The children to render.

            context (django.template.Context):
                The current rendering context.

            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            django.utils.safestring.SafeString:
            The rendered children.
        """
        action = self.action

        if not action.should_render(context=context):
            return mark_safe('')

        # Determine the possible renderers allowed for this group.
        default_subgroup_renderer_cls = self.default_subgroup_renderer_cls

        if default_subgroup_renderer_cls == 'self':
            default_subgroup_renderer_cls = type(self)

        default_renderer_classes = {
            True: default_subgroup_renderer_cls,
            False: self.default_item_renderer_cls,
        }

        attachment = self.placement.attachment
        rendered: list[str] = []

        for child in children:
            placement = child.get_placement(attachment)
            renderer = child.get_renderer_cls(
                placement=placement,
                fallback_renderer_cls=(
                    default_renderer_classes[child._is_action_group]),
            )

            try:
                rendered.append(child.render(
                    request=request,
                    context=context,
                    placement=placement,
                    renderer=renderer,
                ))
            except MissingActionRendererError:
                if child._is_action_group:
                    logger.error(
                        'Could not render action %r inside of group action '
                        '%r in attachment point %r. This location does not '
                        'allow for nesting of groups.',
                        child.action_id, action.action_id, attachment)
                else:
                    logger.error(
                        'Could not render action %r inside of group action '
                        '%r in attachment point %r. This location does not '
                        'allow for child actions.',
                        child.action_id, action.action_id, attachment)
            except Exception as e:
                logger.exception('Error rendering child action %r: %s',
                                 child.action_id, e)

        return mark_safe(''.join(rendered))


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

    default_item_renderer_cls: ClassVar[type[BaseActionRenderer]] = \
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

    default_item_renderer_cls: ClassVar[type[BaseActionRenderer]] = \
        DetailedMenuItemActionRenderer


class SidebarItemActionRenderer(BaseActionRenderer):
    """Renderer for items in a sidebar.

    An item in a sidebar contains a label, an optional icon, and an
    optional URL.

    If a URL is supplied and it matches the current page, the item's
    presentation will show as active.

    Version Added:
        7.1
    """

    template_name = 'actions/sidebar_item_action.html'

    def get_extra_context(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> dict[str, Any]:
        """Return extra template context for the action.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            Extra context to use when rendering the action's template.
        """
        extra_context = super().get_extra_context(request=request,
                                                  context=context)
        extra_context['is_active'] = (
            self.action.get_url(context=context) == request.path)

        return extra_context


class SidebarActionGroupRenderer(BaseActionGroupRenderer):
    """Renderer for a group in a sidebar.

    A rendered sidebar group may contain any number of items or nested
    groups (though presentation may not be optimal if a subgroup contains
    anther subgroup, due to space limitations in the sidebar).

    Version Added:
        7.1
    """

    default_item_renderer_cls: ClassVar[type[BaseActionRenderer]] = \
        SidebarItemActionRenderer

    default_subgroup_renderer_cls: ClassVar[ActionSubgroupRendererType] = \
        'self'

    template_name = 'actions/sidebar_group_action.html'
