"""Default UI themes for Review Board.

Version Added:
    7.0
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _

from reviewboard.themes.ui.base import BaseUITheme, InkColorScheme


class LightUITheme(BaseUITheme):
    """A light mode theme.

    This is the traditional light appearance used for Review Board.

    Version Added:
        7.0
    """

    theme_id = 'light'
    name = _('Light mode')
    ink_color_scheme = InkColorScheme.LIGHT


class DarkUITheme(BaseUITheme):
    """A dark mode theme.

    Version Added:
        7.0
    """

    theme_id = 'dark'
    name = _('Dark mode')
    ink_color_scheme = InkColorScheme.DARK


class SystemUITheme(BaseUITheme):
    """A theme using the current system appearance.

    This will auto-select light mode or dark mode based on the
    browser-specified preference.

    Version Added:
        7.0
    """

    theme_id = 'system'
    name = _('System theme')
    ink_color_scheme = InkColorScheme.SYSTEM
