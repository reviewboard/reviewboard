"""Tests for reviewboard.review.signals."""

from __future__ import unicode_literals

from django.utils import six
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.deprecation import RemovedInReviewBoard40Warning
from reviewboard.reviews.models import ReviewRequest
from reviewboard.reviews.signals import (review_request_closed,
                                         review_request_closing)
from reviewboard.testing import TestCase


class DeprecatedSignalArgsTests(SpyAgency, TestCase):
    """Tests for deprecated signal arguments."""

    @add_fixtures(['test_users'])
    def test_review_request_closed(self):
        """Testing review_request_closing signal has deprecated type argument
        """
        def review_request_closed_cb(close_type, **kwargs):
            pass

        self.spy_on(review_request_closed_cb)
        review_request_closed.connect(review_request_closed_cb,
                                      sender=ReviewRequest)

        review_request = self.create_review_request(publish=True)

        try:
            review_request.close(ReviewRequest.SUBMITTED)
        finally:
            review_request_closed.disconnect(review_request_closed_cb)

        self.assertTrue(review_request_closed_cb.spy.called)

    @add_fixtures(['test_users'])
    def test_review_request_closing(self):
        """Testing review_request_closing signal has deprecated type argument
        """
        def review_request_closing_cb(close_type, **kwargs):
            pass

        self.spy_on(review_request_closing_cb)
        review_request_closing.connect(review_request_closing_cb,
                                       sender=ReviewRequest)

        review_request = self.create_review_request(publish=True)

        try:
            review_request.close(ReviewRequest.SUBMITTED)
        finally:
            review_request_closing.disconnect(review_request_closing_cb)

        self.assertTrue(review_request_closing_cb.spy.called)
