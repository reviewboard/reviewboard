import logging

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from reviewboard.extensions.hooks import (CommentDetailDisplayHook,
                                          NavigationBarHook)
from reviewboard.site.urlresolvers import local_site_reverse


logger = logging.getLogger(__name__)
register = template.Library()


@register.simple_tag(takes_context=True)
def navigation_bar_hooks(context):
    """Displays all registered navigation bar entries."""
    html = []

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
                        template_name='extensions/navbar_entry.html',
                        context=context.flatten()))
                    context.pop()
        except Exception as e:
            extension = hook.extension
            logger.error('Error when running NavigationBarHook.'
                         'get_entries function in extension: "%s": %s',
                         extension.id, e, exc_info=True)

    return mark_safe(''.join(html))


@register.simple_tag(takes_context=True)
def comment_detail_display_hook(context, comment, render_mode):
    """Displays all additional detail from CommentDetailDisplayHooks."""
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
            logger.error('Error when running CommentDetailDisplayHook with '
                         'render mode "%s" in extension: %s: %s',
                         render_mode, extension.id, e, exc_info=True)

    return mark_safe(''.join(html))
