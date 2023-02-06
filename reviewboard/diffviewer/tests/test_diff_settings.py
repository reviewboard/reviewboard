"""Unit tests for reviewboard.diffviewer.settings.DiffSettings.

Version Added:
    5.0.2
"""

from reviewboard.diffviewer.settings import DiffSettings
from reviewboard.testing import TestCase


class DiffSettingsTests(TestCase):
    """Unit tests for reviewboard.diffviewer.settings.DiffSettings."""

    def test_create(self):
        """Testing DiffSettings.create"""
        siteconfig_settings = {
            'code_safety_checkers': {
                'trojan_code': {
                    'enable_confusables': True,
                },
            },
            'diffviewer_context_num_lines': 10,
            'diffviewer_custom_pygments_lexers': {
                '.foo': 'SomeLexer',
            },
            'diffviewer_include_space_patterns': ['*.a', '*.b'],
            'diffviewer_paginate_by': 20,
            'diffviewer_paginate_orphans': 5,
            'diffviewer_syntax_highlighting': True,
            'diffviewer_syntax_highlighting_threshold': 10_000,
        }

        with self.siteconfig_settings(siteconfig_settings):
            diff_settings = DiffSettings.create()

        self.assertEqual(diff_settings.code_safety_configs, {
            'trojan_code': {
                'enable_confusables': True,
            },
        })
        self.assertEqual(diff_settings.context_num_lines, 10)
        self.assertEqual(diff_settings.custom_pygments_lexers, {
            '.foo': 'SomeLexer',
        })
        self.assertEqual(diff_settings.include_space_patterns,
                         ['*.a', '*.b'])
        self.assertEqual(diff_settings.paginate_by, 20)
        self.assertEqual(diff_settings.paginate_orphans, 5)
        self.assertTrue(diff_settings.syntax_highlighting)
        self.assertEqual(diff_settings.syntax_highlighting_threshold,
                         10_000)

    def test_create_with_siteconfig_syntax_highlighting_true(self):
        """Testing DiffSettings.create with
        siteconfig.diffviewer_syntax_highlighting=True
        """
        siteconfig_settings = {
            'diffviewer_syntax_highlighting': True,
        }

        with self.siteconfig_settings(siteconfig_settings):
            diff_settings = DiffSettings.create()

        self.assertTrue(diff_settings.syntax_highlighting)

    def test_create_with_siteconfig_syntax_highlighting_false(self):
        """Testing DiffSettings.create with
        siteconfig.diffviewer_syntax_highlighting=False
        """
        siteconfig_settings = {
            'diffviewer_syntax_highlighting': False
        }

        with self.siteconfig_settings(siteconfig_settings):
            diff_settings = DiffSettings.create()

        self.assertFalse(diff_settings.syntax_highlighting)

    def test_create_with_siteconfig_syntax_highlighting_true_user_true(self):
        """Testing DiffSettings.create with
        siteconfig.diffviewer_syntax_highlighting=True and
        Profile.syntax_highlighting=True
        """
        user = self.create_user()
        profile = user.get_profile()
        profile.syntax_highlighting = True

        siteconfig_settings = {
            'diffviewer_syntax_highlighting': True,
        }

        with self.siteconfig_settings(siteconfig_settings):
            diff_settings = DiffSettings.create(user=user)

        self.assertTrue(diff_settings.syntax_highlighting)

    def test_create_with_siteconfig_syntax_highlighting_true_user_false(self):
        """Testing DiffSettings.create with
        siteconfig.diffviewer_syntax_highlighting=True and
        Profile.syntax_highlighting=False
        """
        user = self.create_user()
        profile = user.get_profile()
        profile.syntax_highlighting = False

        siteconfig_settings = {
            'diffviewer_syntax_highlighting': True,
        }

        with self.siteconfig_settings(siteconfig_settings):
            diff_settings = DiffSettings.create(user=user)

        self.assertFalse(diff_settings.syntax_highlighting)

    def test_state_hash(self):
        """Testing DiffSettings.state_hash"""
        siteconfig_settings = {
            'code_safety_checkers': {
                'trojan_code': {
                    'enable_confusables': True,
                },
            },
            'diffviewer_context_num_lines': 10,
            'diffviewer_custom_pygments_lexers': {
                '.foo': 'SomeLexer',
            },
            'diffviewer_include_space_patterns': ['*.a', '*.b'],
            'diffviewer_paginate_by': 20,
            'diffviewer_paginate_orphans': 5,
            'diffviewer_syntax_highlighting': True,
            'diffviewer_syntax_highlighting_threshold': 10_000,
        }

        with self.siteconfig_settings(siteconfig_settings):
            diff_settings = DiffSettings.create()

        self.assertEqual(
            diff_settings.state_hash,
            '178099a49bf920fd46866042e9013d90d8ad31edf986325cdd641d2e1de4e01f')
