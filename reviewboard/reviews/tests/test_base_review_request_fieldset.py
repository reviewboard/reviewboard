from __future__ import unicode_literals

import kgb
from djblets.registries.errors import ItemLookupError

from reviewboard.reviews.fields import (BaseReviewRequestField,
                                        BaseReviewRequestFieldSet,
                                        field_registry,
                                        logger)
from reviewboard.testing import TestCase


class MyField(BaseReviewRequestFieldSet):
    field_id = 'test-field'


class BaseReviewRequestFieldSetTests(kgb.SpyAgency, TestCase):
    """Unit tests for BaseReviewRequestFieldSet."""

    def test_is_empty_with_classes(self):
        """Testing BaseReviewRequestFieldSet.is_empty with registered
        field_classes
        """
        class MyFieldset(BaseReviewRequestFieldSet):
            field_classes = [MyField]

        self.assertFalse(MyFieldset.is_empty())

    def test_is_empty_without_classes(self):
        """Testing BaseReviewRequestFieldSet.is_empty without registered
        field_classes
        """
        class MyFieldset(BaseReviewRequestFieldSet):
            pass

        self.assertTrue(MyFieldset.is_empty())

    def test_add_field(self):
        """Testing BaseReviewRequestFieldSet.add_field"""
        class MyFieldset(BaseReviewRequestFieldSet):
            pass

        try:
            MyFieldset.add_field(MyField)

            self.assertEqual(MyFieldset.field_classes, [MyField])
            self.assertIn(MyField, field_registry)
        finally:
            try:
                field_registry.unregister(MyField)
            except Exception:
                pass

    def test_remove_field(self):
        """Testing BaseReviewRequestFieldSet.remove_field"""
        class MyFieldset(BaseReviewRequestFieldSet):
            pass

        try:
            MyFieldset.add_field(MyField)
            MyFieldset.remove_field(MyField)

            self.assertEqual(MyFieldset.field_classes, [])
            self.assertNotIn(MyField, field_registry)
        finally:
            try:
                field_registry.unregister(MyField)
            except Exception:
                pass

    def test_remove_field_with_unregistered(self):
        """Testing BaseReviewRequestFieldSet.remove_field with unregistered
        field
        """
        class MyFieldset(BaseReviewRequestFieldSet):
            pass

        self.spy_on(logger.error)

        with self.assertRaises(ItemLookupError):
            MyFieldset.remove_field(MyField)

        self.assertSpyCalledWith(
            logger.error,
            'Failed to unregister unknown review request field "%s"',
            'test-field')

    def test_should_render_with_visible_fields(self):
        """Testing BaseReviewRequestFieldSet.should_render with visible fields
        """
        class HiddenField(BaseReviewRequestField):
            should_render = False

        class VisibleField(BaseReviewRequestField):
            should_render = True

        class MyFieldset(BaseReviewRequestFieldSet):
            field_classes = [HiddenField, VisibleField]

        user = self.create_user()
        review_request = self.create_review_request(submitter=user)
        fieldset = MyFieldset(review_request_details=review_request)

        self.assertTrue(fieldset.should_render)

    def test_should_render_without_visible_fields(self):
        """Testing BaseReviewRequestFieldSet.should_render without visible
        fields
        """
        class HiddenField(BaseReviewRequestField):
            should_render = False

        class MyFieldset(BaseReviewRequestFieldSet):
            field_classes = [HiddenField]

        user = self.create_user()
        review_request = self.create_review_request(submitter=user)
        fieldset = MyFieldset(review_request_details=review_request)

        self.assertFalse(fieldset.should_render)

    def test_should_render_with_field_error(self):
        """Testing BaseReviewRequestFieldSet.should_render with
        error in Field.should_render
        """
        e = Exception('oh no')

        class HiddenField(BaseReviewRequestField):
            @property
            def should_render(self):
                raise e

        class VisibleField(BaseReviewRequestField):
            should_render = True

        class MyFieldset(BaseReviewRequestFieldSet):
            field_classes = [HiddenField, VisibleField]

        self.spy_on(logger.exception)

        user = self.create_user()
        review_request = self.create_review_request(submitter=user)
        fieldset = MyFieldset(review_request_details=review_request)

        self.assertTrue(fieldset.should_render)
        self.assertSpyCalledWith(
            logger.exception,
            'Failed to call %s.should_render: %s',
            'HiddenField',
            e)

    def test_build_fields(self):
        class MyField1(BaseReviewRequestField):
            pass

        class MyField2(BaseReviewRequestField):
            pass

        class MyField3(BaseReviewRequestField):
            pass

        class MyFieldset(BaseReviewRequestFieldSet):
            def build_fields(self):
                review_request_details = self.review_request_details

                return [
                    MyField1(review_request_details=review_request_details),
                    MyField2(review_request_details=review_request_details),
                    MyField3(review_request_details=review_request_details),
                    MyField2(review_request_details=review_request_details),
                    MyField1(review_request_details=review_request_details),
                ]

        user = self.create_user()
        review_request = self.create_review_request(submitter=user)
        fieldset = MyFieldset(review_request_details=review_request)

        fields = fieldset.build_fields()

        self.assertEqual(len(fields), 5)
        self.assertIsInstance(fields[0], MyField1)
        self.assertIsInstance(fields[1], MyField2)
        self.assertIsInstance(fields[2], MyField3)
        self.assertIsInstance(fields[3], MyField2)
        self.assertIsInstance(fields[4], MyField1)
