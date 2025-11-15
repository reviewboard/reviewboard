"""Template tags for actions.

Version Added:
    6.0
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from django.template import Context, Library
from django.utils.safestring import SafeString, mark_safe

from reviewboard.actions import BaseAction, actions_registry
from reviewboard.actions.renderers import BaseActionGroupRenderer

if TYPE_CHECKING:
    from collections.abc import Iterable


logger = logging.getLogger(__name__)
register = Library()


@register.simple_tag(takes_context=True)
def actions_html(
    context: Context,
    attachment: str,
) -> SafeString:
    """Render the actions HTML for the given attachment point.

    Version Added:
        6.0

    Args:
        context (django.template.Context):
            The current template rendering context.

    Returns:
        django.utils.safestring.SafeString:
        The rendered HTML.
    """
    request = context['request']
    actions: Iterable[BaseAction] = \
        actions_registry.get_for_attachment(attachment)
    rendered: list[str] = []

    for action in actions:
        try:
            rendered.append(action.render(request=request, context=context))
        except Exception as e:
            logger.exception('Error rendering action %s: %s',
                             action.action_id, e)

    return mark_safe(''.join(rendered))


@register.simple_tag(takes_context=True)
def child_actions_html(
    context: Context,
) -> SafeString:
    """Render all the child actions of the current menu.

    Version Added:
        6.0

    Args:
        context (django.template.Context):
            The current template rendering context.

    Returns:
        django.utils.safestring.SafeString:
        The rendered HTML.

    Raises:
        TypeError:
            The action renderer was an invalid type for this action.
    """
    parent_renderer = context['action_renderer']

    if not isinstance(parent_renderer, BaseActionGroupRenderer):
        raise TypeError(
            f"Attempted to use {{% child_actions_html %}} from a renderer "
            f"that is not a subclass of BaseActionGroupRenderer (it's a "
            f"{type(parent_renderer)!r}"
        )

    default_item_renderer_cls = parent_renderer.default_item_renderer_cls

    request = context['request']
    actions: Iterable[BaseAction] = context['children']
    rendered: list[str] = []

    for child in actions:
        try:
            if child.is_custom_rendered():
                item_renderer_cls = child.default_renderer_cls
            else:
                item_renderer_cls = default_item_renderer_cls

            rendered.append(child.render(request=request,
                                         context=context,
                                         renderer=item_renderer_cls))
        except Exception:
            logger.exception('Error rendering child action %s',
                             child.action_id)

    return mark_safe(''.join(rendered))


@register.simple_tag(takes_context=True)
def actions_js(
    context: Context,
) -> SafeString:
    """Render the actions JavaScript.

    Version Added:
        6.0

    Args:
        context (django.template.Context):
            The current template rendering context.

    Returns:
        django.utils.safestring.SafeString:
        The rendered JavaScript.
    """
    request = context['request']
    actions: Iterable[BaseAction] = actions_registry
    rendered: list[str] = []

    for action in actions:
        try:
            rendered.append(action.render_js(request=request, context=context))
        except Exception:
            logger.exception('Error rendering action %s JavaScript',
                             action.action_id)

    return mark_safe(''.join(rendered))


@register.simple_tag(takes_context=True)
def action_js_model_data(
    context: Context,
    action: BaseAction,
) -> SafeString:
    """Render the JS model data for an action.

    Version Added:
        6.0

    Args:
        context (django.template.Context):
            The current template rendering context.

        action (reviewboard.actions.base.BaseAction):
            The action to render.

    Returns:
        django.utils.safestring.SafeString:
        The rendered JavaScript.
    """
    return mark_safe(json.dumps(
        action.get_js_model_data(context=context)))


@register.simple_tag(takes_context=True)
def action_js_view_data_items(
    context: Context,
    action: BaseAction,
) -> SafeString:
    """Render the JS view data for an action.

    Version Added:
        6.0

    Args:
        context (django.template.Context):
            The current template rendering context.

        action (reviewboard.actions.base.BaseAction):
            The action to render.

    Returns:
        django.utils.safestring.SafeString:
        The rendered JavaScript.
    """
    renderer = context['action_renderer']

    encoded = json.dumps(renderer.get_js_view_data(context=context),
                         sort_keys=True)[1:-1]

    if encoded:
        encoded += ','

    return mark_safe(encoded)
