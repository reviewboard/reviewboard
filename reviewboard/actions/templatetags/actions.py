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
from djblets.pagestate.state import PageState

from reviewboard.actions import (ActionAttachmentPoint,
                                 BaseAction,
                                 action_attachment_points_registry,
                                 actions_registry)
from reviewboard.actions.renderers import BaseActionGroupRenderer

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


logger = logging.getLogger(__name__)
register = Library()


@register.simple_tag(takes_context=True)
def actions_html(
    context: Context,
    attachment: str | ActionAttachmentPoint,
) -> SafeString:
    """Render the actions HTML for the given attachment point.

    Version Changed:
        7.1:
        This now accepts an
        :py:class:`reviewboard.actions.base.ActionAttachmentPoint` instance
        for the attachment point.

    Version Added:
        6.0

    Args:
        context (django.template.Context):
            The current template rendering context.

        attachment (str or reviewboard.actions.base.ActionAttachmentPoint):
            The instance or registered ID of an attachment point.

            Version Changed:
                7.1:
                This now accepts an
                :py:class:`reviewboard.actions.base.ActionAttachmentPoint`
                instance.

    Returns:
        django.utils.safestring.SafeString:
        The rendered HTML.
    """
    request = context['request']

    # Get the referenced attachment point.
    attachment_point: ActionAttachmentPoint | None

    if isinstance(attachment, ActionAttachmentPoint):
        attachment_point = attachment
    else:
        attachment_point = (
            action_attachment_points_registry
            .get_attachment_point(attachment)
        )

        if attachment_point is None:
            logger.error('Unregistered action attachment point "%s" passed '
                         'to {% actions_html %}',
                         attachment,
                         extra={'request': request})
            return mark_safe('')

    # Store the rendered JavaScript views for later page injection.
    page_state = PageState.for_request(request)
    page_state.inject('rb-action-views', {
        'content': attachment_point.render_js(request=request,
                                              context=context),
    })

    # Now render the HTML for this attachment point.
    try:
        return attachment_point.render(request=request,
                                       context=context)
    except Exception as e:
        logger.exception('Unexpected error rendering actions attachment '
                         'point %r: %s',
                         attachment_point, e,
                         extra={'request': request})

        return mark_safe('')


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
    return mark_safe(''.join(_iter_actions_js(context=context)))


def _iter_actions_js(
    *,
    context: Context,
) -> Iterator[SafeString | str]:
    request = context['request']

    # Render all the action model registration.
    actions: Iterable[BaseAction] = actions_registry

    for action in actions:
        try:
            yield action.render_model_js(request=request,
                                         context=context)
        except Exception as e:
            logger.exception('Error rendering JavaScript for action model '
                             '%r: %s',
                             action, e)

    # Render all the action view construction.
    page_state = PageState.for_request(request)

    yield from page_state.iter_content(
        point_name='rb-action-views',
        request=request,
        context=context)


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
    encoded = json.dumps(context['js_view_data'],
                         sort_keys=True)[1:-1]

    if encoded:
        encoded += ','

    return mark_safe(encoded)
