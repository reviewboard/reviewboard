"""Unit tests for reviewboard.admin.validation."""

from __future__ import unicode_literals

from django.forms import ValidationError

from reviewboard.admin.validation import validate_bug_tracker
from reviewboard.testing.testcase import TestCase


class ValidationTests(TestCase):
    """Unit tests for reviewboard.admin.validation."""

    def test_validate_bug_tracker(self):
        """Testing validate_bug_tracker"""
        # Invalid - invalid format specification types
        with self.assertRaises(ValidationError):
            validate_bug_tracker('%20')

        with self.assertRaises(ValidationError):
            validate_bug_tracker('%d')

        # Invalid - too many format specification types
        with self.assertRaises(ValidationError):
            validate_bug_tracker('%s %s')

        # Invalid - no format specification types
        with self.assertRaises(ValidationError):
            validate_bug_tracker('www.a.com')

        # Valid - Escaped %'s, with a valid format specification type
        try:
            validate_bug_tracker('%%20%s')
        except ValidationError:
            self.fail('validate_bug_tracker() raised a ValidationError when '
                      'no error was expected.')
