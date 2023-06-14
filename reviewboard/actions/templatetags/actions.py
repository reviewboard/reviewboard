"""Template tags for actions.

Version Added:
    6.0
"""

import json
import logging
from typing import Iterable, List

from django.template import Context, Library
from django.utils.safestring import SafeText, mark_safe

from reviewboard.actions import BaseAction, actions_registry


logger = logging.getLogger(__name__)
register = Library()


@register.simple_tag(takes_context=True)
def actions_html(
    context: Context,
    attachment: str,
) -> SafeText:
    """Render the actions HTML for the given attachment point.

    Version Added:
        6.0

    Args:
        context (django.template.Context):
            The current template rendering context.

    Returns:
        django.utils.safestring.SafeText:
        The rendered HTML.
    """
    request = context['request']
    actions: Iterable[BaseAction] = \
        actions_registry.get_for_attachment(attachment)
    rendered: List[str] = []

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
) -> SafeText:
    """Render all the child actions of the current menu.

    Version Added:
        6.0

    Args:
        context (django.template.Context):
            The current template rendering context.

    Returns:
        django.utils.safestring.SafeText:
        The rendered HTML.
    """
    request = context['request']
    actions: Iterable[BaseAction] = context['children']
    rendered: List[str] = []

    for child in actions:
        try:
            rendered.append(child.render(request=request, context=context))
        except Exception:
            logger.exception('Error rendering child action %s',
                             child.action_id)

    return mark_safe(''.join(rendered))


@register.simple_tag(takes_context=True)
def actions_js(
    context: Context,
) -> SafeText:
    """Render the actions JavaScript.

    Version Added:
        6.0

    Args:
        context (django.template.Context):
            The current template rendering context.

    Returns:
        django.utils.safestring.SafeText:
        The rendered JavaScript.
    """
    request = context['request']
    actions: Iterable[BaseAction] = actions_registry
    rendered: List[str] = []

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
) -> SafeText:
    """Render the JS model data for an action.

    Version Added:
        6.0

    Args:
        context (django.template.Context):
            The current template rendering context.

        action (reviewboard.actions.base.BaseAction):
            The action to render.

    Returns:
        django.utils.safestring.SafeText:
        The rendered JavaScript.
    """
    return mark_safe(json.dumps(
        action.get_js_model_data(context=context)))


@register.simple_tag(takes_context=True)
def action_js_view_data_items(
    context: Context,
    action: BaseAction,
) -> SafeText:
    """Render the JS view data for an action.

    Version Added:
        6.0

    Args:
        context (django.template.Context):
            The current template rendering context.

        action (reviewboard.actions.base.BaseAction):
            The action to render.

    Returns:
        django.utils.safestring.SafeText:
        The rendered JavaScript.
    """
    encoded = json.dumps(action.get_js_view_data(context=context))[1:-1]

    if encoded:
        encoded += ','

    return mark_safe(encoded)

