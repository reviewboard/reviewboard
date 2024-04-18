"""Context processors for theme-related state.

Version Added:
    7.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.html import format_html_join

from reviewboard.themes.ui.registry import ui_theme_registry

if TYPE_CHECKING:
    from django.http import HttpRequest


def theme(
    request: HttpRequest,
) -> dict[str, object]:
    """Return template context variables for theme information.

    Version Added:
        7.0

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

    Returns:
        dict:
        The context variables for the page.
    """
    if request.user.is_authenticated:
        profile = request.user.get_profile()
        ui_theme_id = profile.ui_theme_id
    else:
        profile = None
        ui_theme_id = 'default'

    ui_theme = (ui_theme_registry.get_theme(ui_theme_id) or
                ui_theme_registry.get_theme('default'))
    assert ui_theme is not None

    return {
        'ui_theme_attrs_html': format_html_join(
            ' ',
            '{}="{}"',
            ui_theme.get_html_attrs(request=request).items()),
    }
