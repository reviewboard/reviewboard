"""Unit tests for reviewboard.accounts.backends.BaseAuthBackend."""

from __future__ import unicode_literals

import re

from reviewboard.accounts.backends import INVALID_USERNAME_CHAR_REGEX
from reviewboard.testing import TestCase


class BaseAuthBackendTests(TestCase):
    """Unit tests for reviewboard.accounts.backends.BaseAuthBackend."""

    def test_invalid_username_char_regex(self):
        """Testing BaseAuthBackend.INVALID_USERNAME_CHAR_REGEX"""
        cases = [
            ('spaces  ', 'spaces'),
            ('spa ces', 'spaces'),
            ('CASES', 'cases'),
            ('CaSeS', 'cases'),
            ('Spec!al', 'specal'),
            ('email@example.com', 'email@example.com'),
            ('da-shes', 'da-shes'),
            ('un_derscores', 'un_derscores'),
            ('mu ^lt&^ipl Es', 'multiples'),
        ]

        for orig, new in cases:
            self.assertEqual(
                re.sub(INVALID_USERNAME_CHAR_REGEX, '', orig).lower(),
                new)
