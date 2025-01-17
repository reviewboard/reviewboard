"""Unit tests for reviewboard.accounts.user_details.UserBadge.

Version Added:
    7.1
"""

from __future__ import annotations

from reviewboard.accounts.user_details import UserBadge
from reviewboard.testing import TestCase


class UserBadgeTests(TestCase):
    """Unit tests for UserBadge.

    Version Added:
        7.1
    """

    def test_render_to_string(self) -> None:
        """Testing UserBadge.render_to_string"""
        user = self.create_user()
        badge = UserBadge(user=user,
                          label='My Badge')

        self.assertHTMLEqual(
            badge.render_to_string(),
            '<span class="rb-c-user-badge">My Badge</span>')

    def test_render_to_string_with_css_class(self) -> None:
        """Testing UserBadge.render_to_string with css_class"""
        user = self.create_user()
        badge = UserBadge(user=user,
                          label='My Badge',
                          css_class='class1 class2')

        self.assertHTMLEqual(
            badge.render_to_string(),
            '<span class="rb-c-user-badge class1 class2">My Badge</span>')
