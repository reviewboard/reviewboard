"""Template tags for extensions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from reviewboard.extensions.hooks import (CommentDetailDisplayHook,
                                          NavigationBarHook)
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from django.template import Context
    from django.utils.safestring import SafeString

    from reviewboard.reviews.models import BaseComment


logger = logging.getLogger(__name__)
register = template.Library()


@register.simple_tag(takes_context=True)
def navigation_bar_hooks(
    context: Context,
    *,
    sidebar: bool = False,
) -> SafeString:
    """Display all registered navigation bar entries.

    Version Changed:
        7.0.3:
        * Added the ``sidebar`` argument.

    Args:
        context (django.template.Context):
            The current template render context.

        sidebar (bool, optional):
            Whether the navigation bar entries are being rendered in sidebar
            form. If ``False``, the navigation bar entries are being rendered
            in the topbar.

            Version Added:
                7.0.3

    Returns:
        django.utils.safestring.SafeString:
        The rendered navigation bar entries.
    """
    html = []

    if sidebar:
        template_name = 'extensions/navbar_entry_sidebar.html'
    else:
        template_name = 'extensions/navbar_entry.html'

    for hook in NavigationBarHook.hooks:
        try:
            for nav_info in hook.get_entries(context):
                if nav_info:
                    url_name = nav_info.get('url_name', None)

                    if url_name:
                        nav_info['url'] = local_site_reverse(
                            url_name, request=context.get('request'))

                    context.push()
                    context['entry'] = nav_info

                    html.append(render_to_string(
                        template_name=template_name,
                        context=context.flatten()))
                    context.pop()
        except Exception as e:
            extension = hook.extension
            logger.exception(
                'Error when running NavigationBarHook.get_entries function in '
                'extension: "%s": %s',
                extension.id, e)

    return mark_safe(''.join(html))


@register.simple_tag(takes_context=True)
def comment_detail_display_hook(
    context: Context,
    comment: BaseComment,
    render_mode: str,
) -> SafeString:
    """Display all additional detail from CommentDetailDisplayHooks.

    Args:
        context (django.template.Context):
            The current template render context.

        comment (reviewboard.reviews.models.BaseComment):
            The comment being rendered.

        render_mode (str):
            The current render mode. This will be one of "review",
            "text-email", or "html-email", depending on where the comment is
            being rendered.

    Returns:
        django.utils.safestring.SafeString:
        The rendered navigation bar entries.
    """
    assert render_mode in ('review', 'text-email', 'html-email')

    html = []

    for hook in CommentDetailDisplayHook.hooks:
        try:
            if render_mode == 'review':
                html.append(hook.render_review_comment_detail(comment))
            elif render_mode in ('text-email', 'html-email'):
                html.append(hook.render_email_comment_detail(
                    comment, render_mode == 'html-email'))
        except Exception as e:
            extension = hook.extension
            logger.exception(
                'Error when running CommentDetailDisplayHook with render mode '
                '"%s" in extension: %s: %s',
                render_mode, extension.id, e)

    return mark_safe(''.join(html))
