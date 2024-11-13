"""Unit tests for reviewboard.themes.ui.registry.UIThemeRegistry.

Version Added:
    7.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from reviewboard.testing import TestCase
from reviewboard.themes.ui.default import DarkUITheme, SystemUITheme
from reviewboard.themes.ui.registry import UIThemeRegistry

if TYPE_CHECKING:
    from djblets.util.typing import JSONDict


class UIThemeRegistryTests(TestCase):
    """Unit tests for UIThemeRegistry.

    Version Added:
        7.0
    """

    ######################
    # Instance variables #
    ######################

    #: The registry used in tests.
    registry: UIThemeRegistry

    def setUp(self) -> None:
        super().setUp()

        self.registry = UIThemeRegistry()

    def test_get_theme(self) -> None:
        """Testing UIThemeRegistry.get_theme"""
        self.assertIsInstance(self.registry.get_theme('dark'), DarkUITheme)

    def test_get_theme_with_default(self) -> None:
        """Testing UIThemeRegistry.get_theme with ID 'default'"""
        self.assertIsInstance(self.registry.get_theme('default'),
                              SystemUITheme)

    def test_get_default_theme_id(self) -> None:
        """Testing UIThemeRegistry.get_default_theme_id"""
        self.assertEqual(self.registry.get_default_theme_id(), 'system')

    def test_get_default_theme_id_with_siteconfig(self) -> None:
        """Testing UIThemeRegistry.get_default_theme_id with custom default
        in siteconfig
        """
        siteconfig_settings: JSONDict = {
            'default_ui_theme': 'system',
        }

        with self.siteconfig_settings(siteconfig_settings):
            self.assertEqual(self.registry.get_default_theme_id(),
                             'system')

    def test_get_default_theme_id_with_siteconfig_not_found(self) -> None:
        """Testing UIThemeRegistry.get_default_theme_id with custom default
        in siteconfig not found in registry
        """
        siteconfig_settings: JSONDict = {
            'default_ui_theme': 'xxx',
        }

        with self.siteconfig_settings(siteconfig_settings):
            self.assertEqual(self.registry.get_default_theme_id(), 'system')
