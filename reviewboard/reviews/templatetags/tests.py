from __future__ import unicode_literals

import logging

from django.template import Context, Template
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.reviews.fields import (BaseReviewRequestField,
                                        BaseReviewRequestFieldSet,
                                        register_review_request_fieldset,
                                        unregister_review_request_fieldset)
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
