"""Unit tests for reviewboard.themes.ui.base.BaseUITheme.

Version Added:
    7.0
"""

from __future__ import annotations

from reviewboard.testing import TestCase
from reviewboard.themes.ui.base import BaseUITheme, InkColorScheme


class BaseUIThemeTests(TestCase):
    """Unit tests for BaseUITheme.

    Version Added:
        7.0
    """

    def test_get_html_attrs(self) -> None:
        """Testing BaseUITheme.get_html_attrs"""
        class MyUITheme(BaseUITheme):
            theme_id = 'test'
            name = 'Test'
            ink_color_scheme = InkColorScheme.SYSTEM

        self.assertEqual(
            MyUITheme().get_html_attrs(request=self.create_http_request()),
            {
                'data-ink-color-scheme': 'system',
                'data-theme': 'test',
            })
