"""Unit tests for reviewboard.codesafety.checkers.trojan_source."""

from django.utils.safestring import SafeString

from reviewboard.codesafety._unicode_confusables import COMMON_CONFUSABLES_MAP
from reviewboard.codesafety.checkers.trojan_source import \
    TrojanSourceCodeSafetyChecker
from reviewboard.testing import TestCase


class TrojanSourceCodeSafetyCheckerTests(TestCase):
    """Unit tests for reviewboard.codesafety.checkers.trojan_source."""

    def setUp(self):
        super(TrojanSourceCodeSafetyCheckerTests, self).setUp()

        self.checker = TrojanSourceCodeSafetyChecker()

    def test_check_content_with_bidi(self):
        """Testing TrojanSourceCodeSafetyChecker.check_content with
        bi-directional characters
        """
        for c in ('\u202A', '\u202B', '\u202C', '\u202D', '\u202E',
                  '\u2066', '\u2067', '\u2068', '\u2069'):
            self.assertEqual(
                self.checker.check_content(content_items=[{
                    'path': 'test.c',
                    'lines': ['/* Test %s */' % c],
                }]),
                {
                    'warnings': {'bidi'},
                })

    def test_check_content_with_confusables(self):
        """Testing TrojanSourceCodeSafetyChecker.check_content with
        confusable characters
        """
        # Test a few select basic characters.
        for c in (b'\xef\xbc\xa8',
                  b'\xe1\x97\xb0'):
            self.assertEqual(
                self.checker.check_content(content_items=[{
                    'path': 'test.c',
                    'lines': ['def foo%s' % c.decode('utf-8')],
                }]),
                {
                    'warnings': {'confusable'},
                })

        # Test a few select surrogate pairs.
        for c in (b'\xf0\x9d\x97\x95',
                  b'\xf0\x90\x8a\x96'):
            self.assertEqual(
                self.checker.check_content(content_items=[{
                    'path': 'test.c',
                    'lines': ['def foo%s' % c.decode('utf-8')],
                }]),
                {
                    'warnings': {'confusable'},
                })

        # For good measure, run through the entire map.
        for c in COMMON_CONFUSABLES_MAP.keys():
            self.assertEqual(
                self.checker.check_content(content_items=[{
                    'path': 'test.c',
                    'lines': ['def foo%s' % c],
                }]),
                {
                    'warnings': {'confusable'},
                })

    def test_check_content_with_zero_width(self):
        """Testing TrojanSourceCodeSafetyChecker.check_content with
        zero-width spaces
        """
        for c in ('\u200B', '\u200C'):
            self.assertEqual(
                self.checker.check_content(content_items=[{
                    'path': 'test.c',
                    'lines': ['def is_%sadmin():' % c],
                }]),
                {
                    'warnings': {'zws'},
                })

    def test_check_content_with_bidi_and_zero_width(self):
        """Testing TrojanSourceCodeSafetyChecker.check_content with
        bi-directional and zero-width characters
        """
        self.assertEqual(
            self.checker.check_content(content_items=[
                {
                    'path': 'test.py',
                    'lines': ['def is_\u200Badmin'],
                },
                {
                    'path': 'test.c',
                    'lines': [
                        '/*\u202E } \u2066if (isAdmin)\u2069 \u2066 admins */',
                    ],
                },
            ]),
            {
                'warnings': {'bidi', 'zws'},
            })

    def test_update_line_html_with_bidi(self):
        """Testing TrojanSourceCodeSafetyChecker.update_line_html with
        bi-directional characters
        """
        html = self.checker.update_line_html(
            '<span>/*</span> <span>\u202D admin</span><span>*/</span>:')

        self.assertIsInstance(html, SafeString)
        self.assertEqual(
            html,
            '<span>/*</span> <span><span class="rb-o-duc"'
            ' data-codepoint="202D" data-char="&#x202D;"'
            ' title="Unicode Character: Left-To-Right Override"></span> '
            'admin</span><span>*/</span>:')

    def test_update_line_html_with_confusables(self):
        """Testing TrojanSourceCodeSafetyChecker.update_line_html with
        confusables
        """
        datasets = [
            # 1-length characters
            {
                'char': '\uFF28',
                'codepoint': 'FF28',
                'title': 'Fullwidth Latin Capital Letter H',
                'expected_duc': True,
            },
            {
                'char': '\u15F0',
                'codepoint': '15F0',
                'title': 'Canadian Syllabics Carrier Go',
                'expected_duc': True,
            },

            # Surrogate pairs
            {
                'char': '\U0001d5d5',
                'codepoint': '1D5D5',
                'title': 'Mathematical Sans-Serif Bold Capital B',
                'expected_duc': True,
            },
            {
                'char': '\U00010296',
                'codepoint': '10296',
                'title': 'Lycian Letter S',
                'expected_duc': True,
            },

            # Non-confusable surrogate pair
            {
                'char': '\U0001f7e3',
                'codepoint': None,
                'title': None,
                'expected_duc': False,
            },
        ]

        for dataset in datasets:
            line = (
                '<span>def</span> <span>is_%sadmin</span><span>()</span>:'
                % dataset['char']
            )
            html = self.checker.update_line_html(line)

            self.assertIsInstance(html, SafeString)

            if dataset['expected_duc']:
                self.assertEqual(
                    html,
                    '<span>def</span> <span>is_<span class="rb-o-duc"'
                    ' data-codepoint="%(codepoint)s"'
                    ' data-char="&#x%(codepoint)s;"'
                    ' title="Unicode Character: %(title)s"></span>'
                    'admin</span><span>()</span>:'
                    % dataset)
            else:
                self.assertEqual(html, line)

    def test_update_line_html_with_zero_width(self):
        """Testing TrojanSourceCodeSafetyChecker.update_line_html with
        zero-width spaces
        """
        datasets = [
            {
                'char': '\u200B',
                'codepoint': '200B',
                'title': 'Zero Width Space',
            },
            {
                'char': '\u200C',
                'codepoint': '200C',
                'title': 'Zero Width Non-Joiner',
            },
        ]

        for dataset in datasets:
            html = self.checker.update_line_html(
                '<span>def</span> <span>is_%sadmin</span><span>()</span>:'
                % dataset['char'])

            self.assertIsInstance(html, SafeString)
            self.assertEqual(
                html,
                '<span>def</span> <span>is_<span class="rb-o-duc"'
                ' data-codepoint="%(codepoint)s" data-char="&#x%(codepoint)s;"'
                ' title="Unicode Character: %(title)s"></span>'
                'admin</span><span>()</span>:'
                % dataset)

    def test_render_file_alert_html_with_bidi(self):
        """Testing TrojanSourceCodeSafetyChecker.render_file_alert_html with
        bi-directional characters
        """
        html = self.checker.render_file_alert_html(
            error_ids=[],
            warning_ids=['bidi'])

        self.assertIsNotNone(html)
        self.assertIn(
            '<h4 class="rb-c-alert__heading">\n\n'
            '   Bi-directional Unicode Characters',
            html)
        self.assertNotIn(
            '<h4 class="rb-c-alert__heading">\n\n'
            '   Confusable/homoglyph Unicode Characters',
            html)
        self.assertNotIn(
            '<h4 class="rb-c-alert__heading">\n\n'
            '   Zero-width Spaces',
            html)

    def test_render_file_alert_html_with_confusable(self):
        """Testing TrojanSourceCodeSafetyChecker.render_file_alert_html with
        confusables
        """
        html = self.checker.render_file_alert_html(
            error_ids=[],
            warning_ids=['confusable'])

        self.assertIsNotNone(html)
        self.assertIn(
            '<h4 class="rb-c-alert__heading">\n\n'
            '   Confusable/homoglyph Unicode Characters',
            html)
        self.assertNotIn(
            '<h4 class="rb-c-alert__heading">\n\n'
            '   Bi-directional Unicode Characters',
            html)
        self.assertNotIn(
            '<h4 class="rb-c-alert__heading">\n\n'
            '   Zero-width Spaces',
            html)

    def test_render_file_alert_html_with_zero_width(self):
        """Testing TrojanSourceCodeSafetyChecker.render_file_alert_html with
        zero-width spaces
        """
        html = self.checker.render_file_alert_html(
            error_ids=[],
            warning_ids=['zws'])

        self.assertIsNotNone(html)
        self.assertIn(
            '<h4 class="rb-c-alert__heading">\n\n'
            '   Zero-width Spaces',
            html)
        self.assertNotIn(
            '<h4 class="rb-c-alert__heading">\n\n'
            '   Bi-directional Unicode Characters',
            html)
        self.assertNotIn(
            '<h4 class="rb-c-alert__heading">\n\n'
            '   Confusable/homoglyph Unicode Characters',
            html)

    def test_render_file_alert_html_with_all(self):
        """Testing TrojanSourceCodeSafetyChecker.render_file_alert_html with
        all issues
        """
        html = self.checker.render_file_alert_html(
            error_ids=[],
            warning_ids=['bidi', 'confusable', 'zws'])

        self.assertIsNotNone(html)
        self.assertIn(
            '<h4 class="rb-c-alert__heading">\n\n'
            '   Bi-directional Unicode Characters',
            html)
        self.assertIn(
            '<h4 class="rb-c-alert__heading">\n\n'
            '   Confusable/homoglyph Unicode Characters',
            html)
        self.assertIn(
            '<h4 class="rb-c-alert__heading">\n\n'
            '   Zero-width Spaces',
            html)
