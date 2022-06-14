"""Unit tests for reviewboard.codesafety.checkers.base.BaseCodeSafetyChecker.
"""

import kgb
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy

from reviewboard.codesafety.checkers.base import BaseCodeSafetyChecker
from reviewboard.testing import TestCase


class MyCodeSafetyChecker(BaseCodeSafetyChecker):
    checker_id = 'my-checker'
    summary = 'This is a test'
    result_labels = {
        'error1': gettext_lazy('Error #1'),
        'warning1': 'Warning #1',
    }


class BaseCodeSafetyCheckerTests(kgb.SpyAgency, TestCase):
    """Unit tests for BaseCodeSafetyChecker."""

    def setUp(self):
        super(BaseCodeSafetyCheckerTests, self).setUp()

        self.checker = MyCodeSafetyChecker()

    def test_get_result_labels(self):
        """Testing BaseCodeSafetyChecker.get_result_labels"""

        self.assertEqual(
            self.checker.get_result_labels(['warning1', 'error1', 'unknown']),
            ['Warning #1', 'Error #1', 'unknown'])

    def test_render_file_alert_html(self):
        """Testing BaseCodeSafetyChecker.render_file_alert_html"""
        class TemplateMyCodeSafetyChecker(MyCodeSafetyChecker):
            file_alert_html_template_name = 'my-alert.html'

        self.spy_on(render_to_string,
                    op=kgb.SpyOpReturn('<html>result</html>'))

        checker = TemplateMyCodeSafetyChecker()
        html = checker.render_file_alert_html(
            error_ids='error1',
            warning_ids='warning1')

        self.assertEqual(html, '<html>result</html>')

    def test_render_file_alert_html_without_template(self):
        """Testing BaseCodeSafetyChecker.render_file_alert_html without
        template
        """
        self.assertIsNone(self.checker.render_file_alert_html(
            error_ids='error1',
            warning_ids='warning1'))

    def test_get_file_alert_context_data(self):
        """Testing BaseCodeSafetyChecker.get_file_alert_context_data"""
        self.assertEqual(
            self.checker.get_file_alert_context_data(
                error_ids=['error1', 'error2'],
                warning_ids=['warning1', 'warning2']),
            {
                'error_ids': ['error1', 'error2'],
                'error_labels': ['Error #1', 'error2'],
                'warning_ids': ['warning1', 'warning2'],
                'warning_labels': ['Warning #1', 'warning2'],
            })
