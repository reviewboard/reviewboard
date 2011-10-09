from django import template
from django.conf import settings
from django.template.loader import render_to_string
from djblets.util.decorators import basictag

from reviewboard.extensions.hooks import DiffViewerActionHook, \
                                         NavigationBarHook, \
                                         ReviewRequestActionHook, \
                                         ReviewRequestDropdownActionHook


register = template.Library()


def action_hooks(context, hookcls, action_key="action",
                 template_name="extensions/action.html"):
    """Displays all registered action hooks from the specified ActionHook."""
    s = ""

    for hook in hookcls.hooks:
        action_info = hook.get_action_info(context)

        if action_info:
            new_context = {
                'MEDIA_URL': settings.MEDIA_URL,
                'MEDIA_SERIAL': settings.MEDIA_SERIAL,
                action_key: action_info
            }
            context.update(new_context)

            s += render_to_string(template_name, new_context)

    return s


@register.tag
@basictag(takes_context=True)
def diffviewer_action_hooks(context):
    """Displays all registered action hooks for the diff viewer."""
    return action_hooks(context, DiffViewerActionHook)


@register.tag
@basictag(takes_context=True)
def review_request_action_hooks(context):
    """Displays all registered action hooks for review requests."""
    return action_hooks(context, ReviewRequestActionHook)


@register.tag
@basictag(takes_context=True)
def review_request_dropdown_action_hooks(context):
    """Displays all registered action hooks for review requests."""
    return action_hooks(context,
                        ReviewRequestDropdownActionHook,
                        "actions",
                        "extensions/action_dropdown.html")


@register.tag
@basictag(takes_context=True)
def navigation_bar_hooks(context):
    """Displays all registered navigation bar entries."""
    s = ""

    for hook in NavigationBarHook.hooks:
        nav_info = hook.get_entry(context)

        if nav_info:
            new_context = {
                'entry': nav_info,
            }
            new_context.update(context)

            s += render_to_string("extensions/navbar_entry.html", new_context)

    return s
