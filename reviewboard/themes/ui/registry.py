"""Registries for Review Board UI theme support.

Version Added:
    7.0
"""

from __future__ import annotations

from typing import Iterator, Optional, cast

from djblets.siteconfig.models import SiteConfiguration

from reviewboard.registries.registry import OrderedRegistry
from reviewboard.themes.ui.base import BaseUITheme


class UIThemeRegistry(OrderedRegistry[BaseUITheme]):
    """Registry for managing available Review Board UI themes.

    This provides functionality for looking up available UI themes,
    determining a default theme, and registering new themes.

    Version Added:
        7.0
    """

    DEFAULT_THEME_ID = 'light'

    lookup_attrs = ['theme_id']

    def get_theme(
        self,
        theme_id: str,
    ) -> Optional[BaseUITheme]:
        """Return a theme with the specified ID.

        A special value of "default" will always return the default theme
        ID.

        Args:
            theme_id (str):
                The ID of the theme to return.

        Returns:
            reviewboard.themes.ui.base.BaseUITheme:
            The theme instance, or ``None`` if not found.
        """
        if theme_id == 'default':
            theme_id = self.get_default_theme_id()

        return self.get('theme_id', theme_id)

    def get_default_theme_id(self) -> str:
        """Return the ID of the default theme for the UI.

        If the site configuration contains a ``default_ui_theme`` value,
        then that theme ID will be returned, if found in the registry.

        This will always fall back to :py:attr:`DEFAULT_THEME_ID` if a
        configured value is not found.

        Returns:
            str:
            The default theme ID.
        """
        siteconfig = SiteConfiguration.objects.get_current()
        default_theme_id = cast(str, siteconfig.get('default_ui_theme'))

        if (default_theme_id and
            self.get('theme_id', default_theme_id) is not None):
            # The configured default is valid.
            return default_theme_id

        return self.DEFAULT_THEME_ID

    def get_defaults(self) -> Iterator[BaseUITheme]:
        """Return defaults for the registry.

        Yields:
            type:
            Each default UI theme.
        """
        from reviewboard.themes.ui.default import (
            DarkUITheme,
            LightUITheme,
            SystemUITheme,
        )

        yield from (
            LightUITheme(),
            DarkUITheme(),
            SystemUITheme(),
        )


#: The main registry for UI themes.
#:
#: Version Added:
#:     7.0
ui_theme_registry = UIThemeRegistry()
