"""Unit tests for reviewboard.reviews.views.ReviewRequestViewMixin."""

from __future__ import unicode_literals

from datetime import datetime

import pytz
from django.utils import timezone

from reviewboard.reviews.models import ReviewRequest
from reviewboard.reviews.views import ReviewRequestViewMixin
from reviewboard.testing import TestCase


_local_timezone = pytz.timezone('US/Pacific')


class ReviewRequestViewMixinTests(TestCase):
    """Unit tests for reviewboard.reviews.views.ReviewRequestViewMixin."""

    fixtures = ['test_users']

    def test_get_review_request_status_html_with_submitted(self):
        """Testing ReviewRequestViewMixin.get_review_request_status_html
        with status=SUBMITTED
        """
        review_request = self.create_review_request(
            status=ReviewRequest.SUBMITTED,
            time_added=datetime(2018, 2, 10, 9, 23, 12, tzinfo=timezone.utc))

        mixin = ReviewRequestViewMixin()
        mixin.review_request = review_request

        with timezone.override(_local_timezone):
            html = mixin.get_review_request_status_html(
                review_request_details=review_request,
                close_info={
                    'timestamp': datetime(2018, 2, 12, 14, 56, 00,
                                          tzinfo=timezone.utc),
                })

        self.assertHTMLEqual(
            html,
            'Created Feb. 10, 2018 and submitted '
            '<time class="timesince" datetime="2018-02-12T06:56:00-08:00">'
            'Feb. 12, 2018, 6:56 a.m.</time>')

    def test_get_review_request_status_html_with_submitted_no_timestamp(self):
        """Testing ReviewRequestViewMixin.get_review_request_status_html
        with status=SUBMITTED and no timestamp
        """
        review_request = self.create_review_request(
            status=ReviewRequest.SUBMITTED,
            time_added=datetime(2018, 2, 10, 9, 23, 12, tzinfo=timezone.utc))

        mixin = ReviewRequestViewMixin()
        mixin.review_request = review_request

        with timezone.override(_local_timezone):
            html = mixin.get_review_request_status_html(
                review_request_details=review_request,
                close_info={
                    'timestamp': None,
                })

        self.assertEqual(html, 'Created Feb. 10, 2018 and submitted')

    def test_get_review_request_status_html_with_discarded(self):
        """Testing ReviewRequestViewMixin.get_review_request_status_html
        with status=DISCARDED
        """
        review_request = self.create_review_request(
            status=ReviewRequest.DISCARDED,
            time_added=datetime(2018, 2, 10, 9, 23, 12, tzinfo=timezone.utc))

        mixin = ReviewRequestViewMixin()
        mixin.review_request = review_request

        with timezone.override(_local_timezone):
            html = mixin.get_review_request_status_html(
                review_request_details=review_request,
                close_info={
                    'timestamp': datetime(2018, 2, 12, 14, 56, 00,
                                          tzinfo=timezone.utc),
                })

        self.assertHTMLEqual(
            html,
            'Created Feb. 10, 2018 and discarded '
            '<time class="timesince" datetime="2018-02-12T06:56:00-08:00">'
            'Feb. 12, 2018, 6:56 a.m.</time>')

    def test_get_review_request_status_html_with_discarded_no_timestamp(self):
        """Testing ReviewRequestViewMixin.get_review_request_status_html
        with status=DISCARDED and no timestamp
        """
        review_request = self.create_review_request(
            status=ReviewRequest.DISCARDED,
            time_added=datetime(2018, 2, 10, 9, 23, 12, tzinfo=timezone.utc))

        mixin = ReviewRequestViewMixin()
        mixin.review_request = review_request

        with timezone.override(_local_timezone):
            html = mixin.get_review_request_status_html(
                review_request_details=review_request,
                close_info={
                    'timestamp': None,
                })

        self.assertEqual(html, 'Created Feb. 10, 2018 and discarded')

    def test_get_review_request_status_html_with_pending_review(self):
        """Testing ReviewRequestViewMixin.get_review_request_status_html
        with status=PENDING_REVIEW
        """
        review_request = self.create_review_request(
            status=ReviewRequest.PENDING_REVIEW,
            time_added=datetime(2018, 2, 10, 9, 23, 12, tzinfo=timezone.utc),
            last_updated=datetime(2018, 2, 10, 15, 19, 23,
                                  tzinfo=timezone.utc))

        mixin = ReviewRequestViewMixin()
        mixin.review_request = review_request

        with timezone.override(_local_timezone):
            html = mixin.get_review_request_status_html(
                review_request_details=review_request,
                close_info={})

        self.assertHTMLEqual(
            html,
            'Created Feb. 10, 2018 and updated '
            '<time class="timesince" datetime="2018-02-10T07:19:23-08:00">'
            'Feb. 10, 2018, 7:19 a.m.</time>')

    def test_get_review_request_status_html_with_extra_info(self):
        """Testing ReviewRequestViewMixin.get_review_request_status_html
        with extra_info
        """
        review_request = self.create_review_request(
            status=ReviewRequest.PENDING_REVIEW,
            time_added=datetime(2018, 2, 10, 9, 23, 12, tzinfo=timezone.utc),
            last_updated=datetime(2018, 2, 10, 15, 19, 23,
                                  tzinfo=timezone.utc))

        mixin = ReviewRequestViewMixin()
        mixin.review_request = review_request

        with timezone.override(_local_timezone):
            html = mixin.get_review_request_status_html(
                review_request_details=review_request,
                close_info={},
                extra_info=[
                    {
                        'text': '{var} updated at {timestamp}',
                        'timestamp': datetime(2018, 2, 11, 23, 32, 00,
                                              tzinfo=timezone.utc),
                        'extra_vars': {
                            'var': 'Thingie',
                        },
                    },
                ])

        self.assertHTMLEqual(
            html,
            'Created Feb. 10, 2018 and updated '
            '<time class="timesince" datetime="2018-02-10T07:19:23-08:00">'
            'Feb. 10, 2018, 7:19 a.m.</time>'
            ' &mdash; '
            'Thingie updated at '
            '<time class="timesince" datetime="2018-02-11T15:32:00-08:00">'
            'Feb. 11, 2018, 3:32 p.m.</time>')
