from __future__ import unicode_literals

import logging

from django.template import Context, Template
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.reviews.fields import (BaseReviewRequestField,
                                        BaseReviewRequestFieldSet,
                                        register_review_request_fieldset,
                                        unregister_review_request_fieldset)
from reviewboard.reviews.models import Comment
from reviewboard.testing import TestCase


class ReviewTagTests(SpyAgency, TestCase):
    """Tests for reviewboard.reviews.templatetags."""

    @add_fixtures(['test_users'])
    def test_render_instantiated_fields(self):
        """Testing for_review_request_field does not try to render
        uninstantiated fields
        """
        # exception_id will be a unique value (the ID of the field set) that
        # causes the exception; no other exception should have this value.
        exception_id = None

        class TestField(BaseReviewRequestField):
            field_id = 'test_field'

            def __init__(self, *args, **kwargs):
                raise Exception(exception_id)

        class TestFieldSet(BaseReviewRequestFieldSet):
            fieldset_id = 'test_fieldset'

        register_review_request_fieldset(TestFieldSet)
        TestFieldSet.add_field(TestField)

        review_request = self.create_review_request()

        self.spy_on(logging.exception)

        fieldset = TestFieldSet(review_request)
        exception_id = id(fieldset)

        try:
            t = Template(
                '{% load reviewtags %}'
                '{% for_review_request_field review_request fieldset %}'
                'Never reached.'
                '{% end_for_review_request_field %}'
            )

            result = t.render(Context({
                'review_request': review_request,
                'fieldset': TestFieldSet(review_request),
            }))

            self.assertEqual(result, '')
        finally:
            unregister_review_request_fieldset(TestFieldSet)

        # There should only be one logging.exception call, from the failed
        # instantiation of the TestField.
        self.assertEqual(len(logging.exception.spy.calls), 1)
        self.assertEqual(len(logging.exception.spy.calls[0].args), 3)
        self.assertEqual(
            logging.exception.spy.calls[0].args[2].args,
            (exception_id,))

    def test_diff_comment_line_numbers_with_delete_single_lines(self):
        """Testing diff_comment_line_numbers with delete chunk and single
        commented line
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=1),
            'chunks': [
                {
                    'change': 'delete',
                    'lines': [
                        (10, 20, 'deleted line', [], '', '', [], False),
                        # ...
                        (50, 60, 'deleted line', [], '', '', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Line 30 (original)')

    def test_diff_comment_line_numbers_with_delete_mutiple_lines(self):
        """Testing diff_comment_line_numbers with delete chunk and multiple
        commented lines
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=2),
            'chunks': [
                {
                    'change': 'delete',
                    'lines': [
                        (10, 20, 'deleted line', [], '', '', [], False),
                        # ...
                        (50, 60, 'deleted line', [], '', '', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30-31 (original)')

    def test_diff_comment_line_numbers_with_replace_single_line(self):
        """Testing diff_comment_line_numbers with replace chunk and single
        commented line
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=1),
            'chunks': [
                {
                    'change': 'replace',
                    'lines': [
                        (10, 20, 'foo', [], 20, 'replaced line', [], False),
                        # ...
                        (50, 60, 'foo', [], 60, 'replaced line', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result,
                         'Line 30 (original), 30 (patched)')

    def test_diff_comment_line_numbers_with_replace_multiple_lines(self):
        """Testing diff_comment_line_numbers with replace chunk and multiple
        commented lines
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=2),
            'chunks': [
                {
                    'change': 'replace',
                    'lines': [
                        (10, 20, 'foo', [], 20, 'replaced line', [], False),
                        # ...
                        (50, 60, 'foo', [], 60, 'replaced line', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result,
                         'Lines 30-31 (original), 30-31 (patched)')

    def test_diff_comment_line_numbers_with_insert_single_line(self):
        """Testing diff_comment_line_numbers with insert chunk and single
        comented line
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=1),
            'chunks': [
                {
                    'change': 'insert',
                    'lines': [
                        (10, '', '', [], 20, 'inserted line', [], False),
                        # ...
                        (50, '', '', [], 60, 'inserted line', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30 (patched)')

    def test_diff_comment_line_numbers_with_insert_multiple_lines(self):
        """Testing diff_comment_line_numbers with insert chunk and multiple
        commented lines
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=2),
            'chunks': [
                {
                    'change': 'insert',
                    'lines': [
                        (10, '', '', [], 20, 'inserted line', [], False),
                        # ...
                        (50, '', '', [], 60, 'inserted line', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30-31 (patched)')

    def test_diff_comment_line_numbers_with_fake_equal_orig(self):
        """Testing diff_comment_line_numbers with fake equal from original
        side of interdiff
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=2),
            'chunks': [
                {
                    'change': 'equal',
                    'lines': [
                        (10, '', '', [], 20, 'inserted line', [], False),
                        # ...
                        (50, '', '', [], 60, 'inserted line', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30-31 (patched)')

    def test_diff_comment_line_numbers_with_fake_equal_patched(self):
        """Testing diff_comment_line_numbers with fake equal from patched
        side of interdiff
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=2),
            'chunks': [
                {
                    'change': 'equal',
                    'lines': [
                        (10, 20, 'deleted line', [], '', '', [], False),
                        # ...
                        (50, 60, 'deleted line', [], '', '', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30-31 (original)')

    def test_diff_comment_line_numbers_with_spanning_inserts_deletes(self):
        """Testing diff_comment_line_numbers with spanning delete and insert"""
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=50),
            'chunks': [
                {
                    'change': 'delete',
                    'lines': [
                        (10, 20, 'deleted line', [], '', '', [], False),
                        # ...
                        (50, 60, 'deleted line', [], '', '', [], False),
                    ],
                },
                {
                    'change': 'insert',
                    'lines': [
                        (51, '', '', [], 61, 'inserted line', [], False),
                        # ...
                        (100, '', '', [], 110, 'inserted line', [], False),
                    ],
                },
                {
                    'change': 'equal',
                    'lines': [
                        (101, 61, 'equal line', [], 111, 'equal line', [],
                         False),
                        # ...
                        (200, 160, 'equal line', [], 210, 'equal line', [],
                         False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30-60 (original), 61-79 (patched)')

    def test_diff_comment_line_numbers_with_spanning_deletes_inserts(self):
        """Testing diff_comment_line_numbers with spanning insert and delete"""
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=50),
            'chunks': [
                {
                    'change': 'insert',
                    'lines': [
                        (10, '', '', [], 20, 'inserted line', [], False),
                        # ...
                        (50, '', '', [], 60, 'inserted line', [], False),
                    ],
                },
                {
                    'change': 'delete',
                    'lines': [
                        (51, 61, 'inserted line', [], '', '', [], False),
                        # ...
                        (100, 110, 'inserted line', [], '', '', [], False),
                    ],
                },
                {
                    'change': 'equal',
                    'lines': [
                        (101, 111, 'equal line', [], 61, 'equal line', [],
                         False),
                        # ...
                        (200, 210, 'equal line', [], 160, 'equal line', [],
                         False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 61-79 (original), 30-60 (patched)')

    def test_diff_comment_line_numbers_with_spanning_last_chunk(self):
        """Testing diff_comment_line_numbers with spanning chunks through last
        chunk
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=50),
            'chunks': [
                {
                    'change': 'delete',
                    'lines': [
                        (10, 20, 'deleted line', [], '', '', [], False),
                        # ...
                        (50, 60, 'deleted line', [], '', '', [], False),
                    ],
                },
                {
                    'change': 'insert',
                    'lines': [
                        (51, '', '', [], 61, 'inserted line', [], False),
                        # ...
                        (100, '', '', [], 110, 'inserted line', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30-60 (original), 61-79 (patched)')
