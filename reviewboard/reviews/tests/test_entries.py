"""Unit tests for review request page entries."""

from __future__ import unicode_literals

import logging
from datetime import datetime, timedelta

from django.contrib.auth.models import AnonymousUser, User
from django.template import RequestContext
from django.test.client import RequestFactory
from django.utils import six, timezone
from django.utils.timezone import utc
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.changedescs.models import ChangeDescription
from reviewboard.reviews.detail import (BaseReviewRequestPageEntry,
                                        ChangeEntry,
                                        InitialStatusUpdatesEntry,
                                        ReviewEntry,
                                        ReviewRequestPageData,
                                        StatusUpdatesEntryMixin)
from reviewboard.reviews.models import GeneralComment, StatusUpdate
from reviewboard.testing import TestCase


class BaseReviewRequestPageEntryTests(SpyAgency, TestCase):
    """Unit tests for BaseReviewRequestPageEntry."""

    def test_init_with_no_updated_timestamp(self):
        """Testing BaseReviewRequestPageEntry.__init__ without an
        updated_timestamp specified
        """
        entry = BaseReviewRequestPageEntry(
            entry_id='test',
            added_timestamp=datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc),
            collapsed=False)

        self.assertEqual(entry.updated_timestamp,
                         datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))

    def test_render_to_string(self):
        """Testing BaseReviewRequestPageEntry.render_to_string"""
        entry = BaseReviewRequestPageEntry(
            entry_id='test',
            added_timestamp=None,
            collapsed=False)
        entry.template_name = 'reviews/entries/base.html'

        request = RequestFactory().request()
        request.user = AnonymousUser()

        html = entry.render_to_string(request, RequestContext(request, {
            'last_visited': timezone.now(),
        }))

        self.assertNotEqual(html, '')

    def test_render_to_string_with_entry_pos_main(self):
        """Testing BaseReviewRequestPageEntry.render_to_string with
        entry_pos=ENTRY_POS_MAIN
        """
        entry = BaseReviewRequestPageEntry(
            entry_id='test',
            added_timestamp=None,
            collapsed=False)
        entry.template_name = 'reviews/entries/base.html'
        entry.entry_pos = BaseReviewRequestPageEntry.ENTRY_POS_MAIN

        request = RequestFactory().request()
        request.user = AnonymousUser()

        html = entry.render_to_string(request, RequestContext(request, {
            'last_visited': timezone.now(),
        }))
        self.assertIn('<div class="box-statuses">', html)

    def test_render_to_string_with_entry_pos_initial(self):
        """Testing BaseReviewRequestPageEntry.render_to_string with
        entry_pos=ENTRY_POS_INITIAL
        """
        entry = BaseReviewRequestPageEntry(
            entry_id='test',
            added_timestamp=None,
            collapsed=False)
        entry.template_name = 'reviews/entries/base.html'
        entry.entry_pos = BaseReviewRequestPageEntry.ENTRY_POS_INITIAL

        request = RequestFactory().request()
        request.user = AnonymousUser()

        html = entry.render_to_string(request, RequestContext(request, {
            'last_visited': timezone.now(),
        }))
        self.assertNotIn('<div class="box-statuses">', html)

    def test_render_to_string_with_new_entry(self):
        """Testing BaseReviewRequestPageEntry.render_to_string with
        entry_is_new=True
        """
        entry = BaseReviewRequestPageEntry(
            entry_id='test',
            added_timestamp=datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc),
            collapsed=False)
        entry.template_name = 'reviews/entries/base.html'

        request = RequestFactory().request()
        request.user = User.objects.create(username='test-user')

        html = entry.render_to_string(request, RequestContext(request, {
            'last_visited': datetime(2017, 9, 7, 10, 0, 0, tzinfo=utc),
        }))

        self.assertIn(
            'class="review-request-page-entry new-review-request-page-entry',
            html)

    def test_render_to_string_without_new_entry(self):
        """Testing BaseReviewRequestPageEntry.render_to_string with
        entry_is_new=False
        """
        entry = BaseReviewRequestPageEntry(
            entry_id='test',
            added_timestamp=datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc),
            collapsed=False)
        entry.template_name = 'reviews/entries/base.html'

        request = RequestFactory().request()
        request.user = User.objects.create(username='test-user')

        html = entry.render_to_string(request, RequestContext(request, {
            'last_visited': datetime(2017, 9, 7, 18, 0, 0, tzinfo=utc),
        }))

        self.assertNotEqual(html, '')
        self.assertNotIn(
            'class="review-request-page-entry new-review-request-page-entry"',
            html)

    def test_render_to_string_with_no_template(self):
        """Testing BaseReviewRequestPageEntry.render_to_string with
        template_name=None
        """
        entry = BaseReviewRequestPageEntry(
            entry_id='test',
            added_timestamp=None,
            collapsed=False)

        request = RequestFactory().request()
        request.user = AnonymousUser()

        html = entry.render_to_string(request, RequestContext(request, {
            'last_visited': timezone.now(),
        }))
        self.assertEqual(html, '')

    def test_render_to_string_with_has_content_false(self):
        """Testing BaseReviewRequestPageEntry.render_to_string with
        has_content=False
        """
        entry = BaseReviewRequestPageEntry(
            entry_id='test',
            added_timestamp=None,
            collapsed=False)
        entry.template_name = 'reviews/entries/base.html'
        entry.has_content = False

        request = RequestFactory().request()
        request.user = AnonymousUser()

        html = entry.render_to_string(request, RequestContext(request, {
            'last_visited': timezone.now(),
        }))
        self.assertEqual(html, '')

    def test_render_to_string_with_exception(self):
        """Testing BaseReviewRequestPageEntry.render_to_string with
        exception
        """
        entry = BaseReviewRequestPageEntry(
            entry_id='test',
            added_timestamp=None,
            collapsed=False)
        entry.template_name = 'reviews/entries/NOT_FOUND.html'

        self.spy_on(logging.exception)

        request = RequestFactory().request()
        request.user = AnonymousUser()

        html = entry.render_to_string(request, RequestContext(request, {
            'last_visited': timezone.now(),
        }))

        self.assertEqual(html, '')
        self.assertTrue(logging.exception.spy.called)
        self.assertEqual(logging.exception.spy.calls[0].args[0],
                         'Error rendering template for %s (ID=%s): %s')

    def test_is_entry_new_with_timestamp(self):
        """Testing BaseReviewRequestPageEntry.is_entry_new with timestamp"""
        entry = BaseReviewRequestPageEntry(
            entry_id='test',
            added_timestamp=datetime(2017, 9, 7, 15, 36, 0, tzinfo=utc),
            collapsed=False)

        user = User.objects.create(username='test-user')

        self.assertTrue(entry.is_entry_new(
            last_visited=datetime(2017, 9, 7, 10, 0, 0, tzinfo=utc),
            user=user))
        self.assertFalse(entry.is_entry_new(
            last_visited=datetime(2017, 9, 7, 16, 0, 0, tzinfo=utc),
            user=user))
        self.assertFalse(entry.is_entry_new(
            last_visited=datetime(2017, 9, 7, 15, 36, 0, tzinfo=utc),
            user=user))

    def test_is_entry_new_without_timestamp(self):
        """Testing BaseReviewRequestPageEntry.is_entry_new without timestamp
        """
        entry = BaseReviewRequestPageEntry(
            entry_id='test',
            added_timestamp=None,
            collapsed=False)

        self.assertFalse(entry.is_entry_new(
            last_visited=datetime(2017, 9, 7, 10, 0, 0, tzinfo=utc),
            user=User.objects.create(username='test-user')))


class StatusUpdatesEntryMixinTests(TestCase):
    """Unit tests for StatusUpdatesEntryMixin."""

    def test_add_update_with_done_failure(self):
        """Testing StatusUpdatesEntryMixin.add_update with DONE_FAILURE"""
        status_update = StatusUpdate(state=StatusUpdate.DONE_FAILURE)
        entry = StatusUpdatesEntryMixin()
        entry.add_update(status_update)

        self.assertEqual(entry.status_updates, [status_update])
        self.assertEqual(status_update.header_class,
                         'status-update-state-failure')

    def test_add_update_with_error(self):
        """Testing StatusUpdatesEntryMixin.add_update with ERROR"""
        status_update = StatusUpdate(state=StatusUpdate.ERROR)
        entry = StatusUpdatesEntryMixin()
        entry.add_update(status_update)

        self.assertEqual(entry.status_updates, [status_update])
        self.assertEqual(status_update.header_class,
                         'status-update-state-failure')

    def test_add_update_with_timeout(self):
        """Testing StatusUpdatesEntryMixin.add_update with TIMEOUT"""
        status_update = StatusUpdate(state=StatusUpdate.TIMEOUT)
        entry = StatusUpdatesEntryMixin()
        entry.add_update(status_update)

        self.assertEqual(entry.status_updates, [status_update])
        self.assertEqual(status_update.header_class,
                         'status-update-state-failure')

    def test_add_update_with_pending(self):
        """Testing StatusUpdatesEntryMixin.add_update with PENDING"""
        status_update = StatusUpdate(state=StatusUpdate.PENDING)
        entry = StatusUpdatesEntryMixin()
        entry.add_update(status_update)

        self.assertEqual(entry.status_updates, [status_update])
        self.assertEqual(status_update.header_class,
                         'status-update-state-pending')

    def test_add_update_with_done_success(self):
        """Testing StatusUpdatesEntryMixin.add_update with DONE_SUCCESS"""
        status_update = StatusUpdate(state=StatusUpdate.DONE_SUCCESS)
        entry = StatusUpdatesEntryMixin()
        entry.add_update(status_update)

        self.assertEqual(entry.status_updates, [status_update])
        self.assertEqual(status_update.header_class,
                         'status-update-state-success')

    def test_add_update_html_rendering(self):
        """Testing StatusUpdatesEntryMixin.add_update HTML rendering"""
        status_update = StatusUpdate(state=StatusUpdate.DONE_SUCCESS,
                                     description='My description.',
                                     summary='My summary.')
        entry = StatusUpdatesEntryMixin()
        entry.add_update(status_update)

        self.assertHTMLEqual(
            status_update.summary_html,
            ('<div class="status-update-summary-entry'
             ' status-update-state-success">\n'
             ' <span class="summary">My summary.</span>\n'
             ' My description.\n'
             '</div>'))

    def test_add_update_html_rendering_with_url(self):
        """Testing StatusUpdatesEntryMixin.add_update HTML rendering with URL
        """
        status_update = StatusUpdate(state=StatusUpdate.DONE_SUCCESS,
                                     description='My description.',
                                     summary='My summary.',
                                     url='https://example.com/')
        entry = StatusUpdatesEntryMixin()
        entry.add_update(status_update)

        self.assertHTMLEqual(
            status_update.summary_html,
            ('<div class="status-update-summary-entry'
             ' status-update-state-success">\n'
             ' <span class="summary">My summary.</span>\n'
             ' My description.\n'
             ' <a href="https://example.com/">https://example.com/</a>'
             '</div>'))

    def test_add_update_html_rendering_with_url_and_text(self):
        """Testing StatusUpdatesEntryMixin.add_update HTML rendering with URL
        and URL text
        """
        status_update = StatusUpdate(state=StatusUpdate.DONE_SUCCESS,
                                     description='My description.',
                                     summary='My summary.',
                                     url='https://example.com/',
                                     url_text='My URL')
        entry = StatusUpdatesEntryMixin()
        entry.add_update(status_update)

        self.assertHTMLEqual(
            status_update.summary_html,
            ('<div class="status-update-summary-entry'
             ' status-update-state-success">\n'
             ' <span class="summary">My summary.</span>\n'
             ' My description.\n'
             ' <a href="https://example.com/">My URL</a>'
             '</div>'))

    def test_add_update_html_rendering_with_timeout(self):
        """Testing StatusUpdatesEntryMixin.add_update HTML rendering with
        timeout
        """
        status_update = StatusUpdate(state=StatusUpdate.TIMEOUT,
                                     description='My description.',
                                     summary='My summary.')
        entry = StatusUpdatesEntryMixin()
        entry.add_update(status_update)

        self.assertHTMLEqual(
            status_update.summary_html,
            ('<div class="status-update-summary-entry'
             ' status-update-state-failure">\n'
             ' <span class="summary">My summary.</span>\n'
             ' timed out.\n'
             '</div>'))

    @add_fixtures(['test_users'])
    def test_add_comment(self):
        """Testing StatusUpdatesEntryMixin.add_comment"""
        review_request = self.create_review_request()
        review = self.create_review(review_request)
        comment = self.create_general_comment(review)

        # This is needed by the entry's add_comment(). It's normally built when
        # creating the entries and their data.
        comment.review_obj = review

        status_update = self.create_status_update(
            review_request=review_request,
            review=review)

        entry = StatusUpdatesEntryMixin()
        entry.add_update(status_update)
        entry.add_comment('general_comments', comment)

        self.assertEqual(status_update.comments['general_comments'], [comment])

    def test_finalize_with_all_states(self):
        """Testing StatusUpdatesEntryMixin.finalize with all states"""
        entry = StatusUpdatesEntryMixin()

        entry.add_update(StatusUpdate(state=StatusUpdate.DONE_FAILURE))

        for i in range(2):
            entry.add_update(StatusUpdate(state=StatusUpdate.DONE_SUCCESS))

        for i in range(3):
            entry.add_update(StatusUpdate(state=StatusUpdate.PENDING))

        for i in range(4):
            entry.add_update(StatusUpdate(state=StatusUpdate.ERROR))

        for i in range(5):
            entry.add_update(StatusUpdate(state=StatusUpdate.TIMEOUT))

        entry.finalize()

        self.assertEqual(
            entry.state_summary,
            '1 failed, 2 succeeded, 3 pending, 4 failed with error, '
            '5 timed out')

    def test_finalize_with_done_failure(self):
        """Testing StatusUpdatesEntryMixin.finalize with DONE_FAILURE"""
        entry = StatusUpdatesEntryMixin()
        entry.add_update(StatusUpdate(state=StatusUpdate.DONE_FAILURE))
        entry.finalize()

        self.assertEqual(entry.state_summary, '1 failed')
        self.assertEqual(entry.state_summary_class,
                         'status-update-state-failure')

    def test_finalize_with_error(self):
        """Testing StatusUpdatesEntryMixin.finalize with ERROR"""
        entry = StatusUpdatesEntryMixin()
        entry.add_update(StatusUpdate(state=StatusUpdate.ERROR))
        entry.finalize()

        self.assertEqual(entry.state_summary, '1 failed with error')
        self.assertEqual(entry.state_summary_class,
                         'status-update-state-failure')

    def test_finalize_with_timeout(self):
        """Testing StatusUpdatesEntryMixin.finalize with TIMEOUT"""
        entry = StatusUpdatesEntryMixin()
        entry.add_update(StatusUpdate(state=StatusUpdate.TIMEOUT))
        entry.finalize()

        self.assertEqual(entry.state_summary, '1 timed out')
        self.assertEqual(entry.state_summary_class,
                         'status-update-state-failure')

    def test_finalize_with_pending(self):
        """Testing StatusUpdatesEntryMixin.finalize with PENDING"""
        entry = StatusUpdatesEntryMixin()
        entry.add_update(StatusUpdate(state=StatusUpdate.PENDING))
        entry.finalize()

        self.assertEqual(entry.state_summary, '1 pending')
        self.assertEqual(entry.state_summary_class,
                         'status-update-state-pending')

    def test_finalize_with_done_success(self):
        """Testing StatusUpdatesEntryMixin.finalize with DONE_SUCCESS"""
        entry = StatusUpdatesEntryMixin()
        entry.add_update(StatusUpdate(state=StatusUpdate.DONE_SUCCESS))
        entry.finalize()

        self.assertEqual(entry.state_summary, '1 succeeded')
        self.assertEqual(entry.state_summary_class,
                         'status-update-state-success')

    def test_finalize_with_failures_take_precedence(self):
        """Testing StatusUpdatesEntryMixin.finalize with failures taking
        precedence over PENDING and DONE_SUCCESS
        """
        entry = StatusUpdatesEntryMixin()
        entry.add_update(StatusUpdate(state=StatusUpdate.DONE_FAILURE))
        entry.add_update(StatusUpdate(state=StatusUpdate.PENDING))
        entry.add_update(StatusUpdate(state=StatusUpdate.DONE_SUCCESS))
        entry.finalize()

        self.assertEqual(entry.state_summary,
                         '1 failed, 1 succeeded, 1 pending')
        self.assertEqual(entry.state_summary_class,
                         'status-update-state-failure')

    def test_finalize_with_pending_take_precedence(self):
        """Testing StatusUpdatesEntryMixin.finalize with PENDING taking
        precedence SUCCESS
        """
        entry = StatusUpdatesEntryMixin()
        entry.add_update(StatusUpdate(state=StatusUpdate.PENDING))
        entry.add_update(StatusUpdate(state=StatusUpdate.DONE_SUCCESS))
        entry.finalize()

        self.assertEqual(entry.state_summary, '1 succeeded, 1 pending')
        self.assertEqual(entry.state_summary_class,
                         'status-update-state-pending')

    @add_fixtures(['test_users'])
    def test_populate_status_updates(self):
        """Testing StatusUpdatesEntryMixin.populate_status_updates"""
        review_request = self.create_review_request()
        review = self.create_review(review_request, public=True)
        comment = self.create_general_comment(review)

        # This state is normally set in ReviewRequestPageData.
        comment._type = 'general_comments'
        comment.review_obj = review

        status_updates = [
            StatusUpdate(state=StatusUpdate.PENDING),
            StatusUpdate(state=StatusUpdate.DONE_FAILURE,
                         review=review)
        ]

        request = RequestFactory().get('/r/1/')
        request.user = AnonymousUser()

        data = ReviewRequestPageData(review_request=review_request,
                                     request=request)
        data.review_comments[review.pk] = [comment]

        entry = StatusUpdatesEntryMixin()
        entry.collapsed = True
        entry.populate_status_updates(status_updates, data)

        self.assertTrue(entry.collapsed)
        self.assertEqual(entry.status_updates, status_updates)

        status_update = entry.status_updates[0]
        self.assertIsNone(status_update.review)
        self.assertEqual(
            status_update.comments,
            {
                'diff_comments': [],
                'screenshot_comments': [],
                'file_attachment_comments': [],
                'general_comments': [],
            })

        status_update = entry.status_updates[1]
        self.assertEqual(status_update.review, review)
        self.assertEqual(
            status_update.comments,
            {
                'diff_comments': [],
                'screenshot_comments': [],
                'file_attachment_comments': [],
                'general_comments': [comment],
            })

    @add_fixtures(['test_users'])
    def test_populate_status_updates_with_draft_replies(self):
        """Testing StatusUpdatesEntryMixin.populate_status_updates with
        draft replies
        """
        review_request = self.create_review_request()
        review = self.create_review(review_request, public=True)
        comment = self.create_general_comment(review)

        reply = self.create_reply(review)
        reply_comment = self.create_general_comment(reply, reply_to=comment)

        # This state is normally set in ReviewRequestPageData.
        comment._type = 'general_comments'
        comment.review_obj = review

        status_updates = [
            StatusUpdate(state=StatusUpdate.PENDING),
            StatusUpdate(state=StatusUpdate.DONE_FAILURE,
                         review=review)
        ]

        request = RequestFactory().get('/r/1/')
        request.user = AnonymousUser()

        data = ReviewRequestPageData(review_request=review_request,
                                     request=request)
        data.review_comments[review.pk] = [comment]
        data.draft_reply_comments[review.pk] = [reply_comment]

        entry = StatusUpdatesEntryMixin()
        entry.collapsed = True
        entry.populate_status_updates(status_updates, data)

        self.assertFalse(entry.collapsed)
        self.assertEqual(entry.status_updates, status_updates)

        status_update = entry.status_updates[0]
        self.assertIsNone(status_update.review)
        self.assertEqual(
            status_update.comments,
            {
                'diff_comments': [],
                'screenshot_comments': [],
                'file_attachment_comments': [],
                'general_comments': [],
            })

        status_update = entry.status_updates[1]
        self.assertEqual(status_update.review, review)
        self.assertEqual(
            status_update.comments,
            {
                'diff_comments': [],
                'screenshot_comments': [],
                'file_attachment_comments': [],
                'general_comments': [comment],
            })


class InitialStatusUpdatesEntryTests(TestCase):
    """Unit tests for InitialStatusUpdatesEntry."""

    fixtures = ['test_users']

    def setUp(self):
        super(InitialStatusUpdatesEntryTests, self).setUp()

        self.request = RequestFactory().get('/r/1/')
        self.request.user = AnonymousUser()

        self.review_request = self.create_review_request(
            time_added=datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))
        self.review = self.create_review(
            self.review_request,
            public=True,
            timestamp=datetime(2017, 9, 14, 15, 40, 0, tzinfo=utc))
        self.general_comment = self.create_general_comment(self.review,
                                                           issue_opened=False)
        self.status_update = self.create_status_update(
            self.review_request,
            review=self.review,
            timestamp=datetime(2017, 9, 14, 15, 40, 0, tzinfo=utc))

        self.data = ReviewRequestPageData(review_request=self.review_request,
                                          request=self.request)

    def test_added_timestamp(self):
        """Testing InitialStatusUpdatesEntry.added_timestamp"""
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = InitialStatusUpdatesEntry(review_request=self.review_request,
                                          collapsed=False,
                                          data=self.data)

        self.assertEqual(entry.added_timestamp,
                         datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))

    def test_updated_timestamp(self):
        """Testing InitialStatusUpdatesEntry.updated_timestamp"""
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = InitialStatusUpdatesEntry(review_request=self.review_request,
                                          collapsed=False,
                                          data=self.data)

        self.assertEqual(entry.updated_timestamp,
                         datetime(2017, 9, 14, 15, 40, 0, tzinfo=utc))

    def test_build_entries(self):
        """Testing InitialStatusUpdatesEntry.build_entries"""
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entries = list(InitialStatusUpdatesEntry.build_entries(self.data))
        self.assertEqual(len(entries), 1)

        entry = entries[0]
        self.assertEqual(entry.added_timestamp,
                         datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))
        self.assertEqual(entry.updated_timestamp,
                         datetime(2017, 9, 14, 15, 40, 0, tzinfo=utc))
        self.assertFalse(entry.collapsed)
        self.assertEqual(entry.status_updates, [self.status_update])
        self.assertEqual(
            entry.status_updates_by_review,
            {
                self.review.pk: self.status_update,
            })
        self.assertEqual(
            entry.status_updates[0].comments,
            {
                'diff_comments': [],
                'screenshot_comments': [],
                'file_attachment_comments': [],
                'general_comments': [self.general_comment],
            })

    def test_build_entries_with_changedesc(self):
        """Testing InitialStatusUpdatesEntry.build_entries with
        ChangeDescription following this entry
        """
        self.review_request.changedescs.create(public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entries = list(InitialStatusUpdatesEntry.build_entries(self.data))
        self.assertEqual(len(entries), 1)

        entry = entries[0]
        self.assertTrue(entry.collapsed)
        self.assertEqual(entry.status_updates, [self.status_update])
        self.assertEqual(
            entry.status_updates_by_review,
            {
                self.review.pk: self.status_update,
            })

        status_update = entry.status_updates[0]
        self.assertEqual(status_update.review, self.review)
        self.assertIsNone(status_update.change_description)
        self.assertEqual(
            status_update.comments,
            {
                'diff_comments': [],
                'screenshot_comments': [],
                'file_attachment_comments': [],
                'general_comments': [self.general_comment],
            })


class ReviewEntryTests(TestCase):
    """Unit tests for ReviewEntry."""

    fixtures = ['test_users']

    def setUp(self):
        super(ReviewEntryTests, self).setUp()

        self.request = RequestFactory().get('/r/1/')
        self.request.user = AnonymousUser()

        self.review_request = self.create_review_request()
        self.review = self.create_review(
            self.review_request,
            id=123,
            public=True,
            timestamp=datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))
        self.data = ReviewRequestPageData(review_request=self.review_request,
                                          request=self.request)

    def test_added_timestamp(self):
        """Testing ReviewEntry.added_timestamp"""
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ReviewEntry(request=self.request,
                            review_request=self.review_request,
                            review=self.review,
                            collapsed=False,
                            data=self.data)

        self.assertEqual(entry.added_timestamp,
                         datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))

    def test_updated_timestamp(self):
        """Testing ReviewEntry.updated_timestamp"""
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ReviewEntry(request=self.request,
                            review_request=self.review_request,
                            review=self.review,
                            collapsed=False,
                            data=self.data)

        self.assertEqual(entry.updated_timestamp,
                         datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))

    def test_updated_timestamp_with_replies(self):
        """Testing ReviewEntry.updated_timestamp with replies"""
        self.create_reply(self.review,
                          timestamp=datetime(2017, 9, 14, 15, 40, 0,
                                             tzinfo=utc),
                          publish=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ReviewEntry(request=self.request,
                            review_request=self.review_request,
                            review=self.review,
                            collapsed=False,
                            data=self.data)

        self.assertEqual(entry.updated_timestamp,
                         datetime(2017, 9, 14, 15, 40, 0, tzinfo=utc))

    def test_get_dom_element_id(self):
        """Testing ReviewEntry.get_dom_element_id"""
        entry = ReviewEntry(request=self.request,
                            review_request=self.review_request,
                            review=self.review,
                            collapsed=False,
                            data=self.data)

        self.assertEqual(entry.get_dom_element_id(), 'review123')

    def test_get_js_model_data(self):
        """Testing ReviewEntry.get_js_model_data"""
        self.review.ship_it = True
        self.review.publish()

        entry = ReviewEntry(request=self.request,
                            review_request=self.review_request,
                            review=self.review,
                            collapsed=False,
                            data=self.data)

        self.assertEqual(entry.get_js_model_data(), {
            'reviewData': {
                'id': self.review.pk,
                'bodyTop': 'Test Body Top',
                'bodyBottom': 'Test Body Bottom',
                'public': True,
                'shipIt': True,
            },
        })

    @add_fixtures(['test_scmtools'])
    def test_get_js_model_data_with_diff_comments(self):
        """Testing ReviewEntry.get_js_model_data with diff comments"""
        self.review_request.repository = self.create_repository()
        diffset = self.create_diffset(self.review_request)
        filediff = self.create_filediff(diffset)

        comment1 = self.create_diff_comment(self.review, filediff)
        comment2 = self.create_diff_comment(self.review, filediff)
        self.review.publish()

        # This is needed by the entry's add_comment(). It's normally built when
        # creating the entries and their data.
        comment1.review_obj = self.review
        comment2.review_obj = self.review

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ReviewEntry(request=self.request,
                            review_request=self.review_request,
                            review=self.review,
                            collapsed=False,
                            data=self.data)
        entry.add_comment('diff_comments', comment1)
        entry.add_comment('diff_comments', comment2)

        self.assertEqual(entry.get_js_model_data(), {
            'reviewData': {
                'id': self.review.pk,
                'bodyTop': 'Test Body Top',
                'bodyBottom': 'Test Body Bottom',
                'public': True,
                'shipIt': False,
            },
            'diffCommentsData': [
                (six.text_type(comment1.pk), six.text_type(filediff.pk)),
                (six.text_type(comment2.pk), six.text_type(filediff.pk)),
            ],
        })

    def test_add_comment_with_no_open_issues(self):
        """Testing ReviewEntry.add_comment with comment not opening an issue"""
        self.request.user = self.review_request.submitter
        entry = ReviewEntry(request=self.request,
                            review_request=self.review_request,
                            review=self.review,
                            collapsed=True,
                            data=self.data)

        self.assertFalse(entry.has_issues)
        self.assertEqual(entry.issue_open_count, 0)

        entry.add_comment('general_comments', GeneralComment())

        self.assertFalse(entry.has_issues)
        self.assertEqual(entry.issue_open_count, 0)
        self.assertTrue(entry.collapsed)

    def test_add_comment_with_open_issues(self):
        """Testing ReviewEntry.add_comment with comment opening an issue"""
        entry = ReviewEntry(request=self.request,
                            review_request=self.review_request,
                            review=self.review,
                            collapsed=True,
                            data=self.data)

        self.assertFalse(entry.has_issues)
        self.assertEqual(entry.issue_open_count, 0)

        entry.add_comment('general_comments',
                          GeneralComment(issue_opened=True,
                                         issue_status=GeneralComment.OPEN))

        self.assertTrue(entry.has_issues)
        self.assertEqual(entry.issue_open_count, 1)
        self.assertTrue(entry.collapsed)

    def test_add_comment_with_open_issues_and_viewer_is_owner(self):
        """Testing ReviewEntry.add_comment with comment opening an issue and
        the review request owner is viewing the page
        """
        self.request.user = self.review_request.submitter
        entry = ReviewEntry(request=self.request,
                            review_request=self.review_request,
                            review=self.review,
                            collapsed=True,
                            data=self.data)

        self.assertFalse(entry.has_issues)
        self.assertEqual(entry.issue_open_count, 0)

        entry.add_comment('general_comments',
                          GeneralComment(issue_opened=True,
                                         issue_status=GeneralComment.OPEN))

        self.assertTrue(entry.has_issues)
        self.assertEqual(entry.issue_open_count, 1)
        self.assertFalse(entry.collapsed)

    def test_build_entries(self):
        """Testing ReviewEntry.build_entries"""
        review1 = self.create_review(
            self.review_request,
            timestamp=self.review.timestamp - timedelta(days=2),
            public=True)
        review2 = self.review

        comment = self.create_general_comment(review1)

        # These shouldn't show up in the results.
        self.create_review(
            self.review_request,
            timestamp=self.review.timestamp - timedelta(days=1),
            public=False)
        self.create_reply(review1)

        status_update_review = self.create_review(self.review_request,
                                                  public=True)
        self.create_general_comment(status_update_review)
        self.create_status_update(self.review_request,
                                  review=status_update_review)

        # Create a change description to test collapsing.
        self.review_request.changedescs.create(
            timestamp=review2.timestamp - timedelta(days=1),
            public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entries = list(ReviewEntry.build_entries(self.data))

        self.assertEqual(len(entries), 2)

        # These will actually be in database query order (newest to oldest),
        # not the order shown on the page.
        entry = entries[0]
        self.assertEqual(entry.review, review2)
        self.assertFalse(entry.collapsed)
        self.assertEqual(
            entry.comments,
            {
                'diff_comments': [],
                'screenshot_comments': [],
                'file_attachment_comments': [],
                'general_comments': [],
            })

        entry = entries[1]
        self.assertEqual(entry.review, review1)
        self.assertTrue(entry.collapsed)
        self.assertEqual(
            entry.comments,
            {
                'diff_comments': [],
                'screenshot_comments': [],
                'file_attachment_comments': [],
                'general_comments': [comment],
            })


class ChangeEntryTests(TestCase):
    """Unit tests for ChangeEntry."""

    fixtures = ['test_users']

    def setUp(self):
        super(ChangeEntryTests, self).setUp()

        self.request = RequestFactory().get('/r/1/')
        self.request.user = AnonymousUser()

        self.review_request = self.create_review_request()
        self.changedesc = ChangeDescription.objects.create(
            id=123,
            public=True,
            timestamp=datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))
        self.review_request.changedescs.add(self.changedesc)
        self.data = ReviewRequestPageData(review_request=self.review_request,
                                          request=self.request)

    def test_added_timestamp(self):
        """Testing ChangeEntry.added_timestamp"""
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ChangeEntry(request=self.request,
                            review_request=self.review_request,
                            changedesc=self.changedesc,
                            collapsed=False,
                            data=self.data)

        self.assertEqual(entry.added_timestamp,
                         datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))

    def test_updated_timestamp(self):
        """Testing ChangeEntry.updated_timestamp"""
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ChangeEntry(request=self.request,
                            review_request=self.review_request,
                            changedesc=self.changedesc,
                            collapsed=False,
                            data=self.data)

        self.assertEqual(entry.updated_timestamp,
                         datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))

    def test_updated_timestamp_with_status_update(self):
        """Testing ChangeEntry.updated_timestamp with status updates"""
        self.create_status_update(
            self.review_request,
            change_description=self.changedesc,
            timestamp=datetime(2017, 9, 14, 15, 40, 0, tzinfo=utc))

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ChangeEntry(request=self.request,
                            review_request=self.review_request,
                            changedesc=self.changedesc,
                            collapsed=False,
                            data=self.data)

        self.assertEqual(entry.updated_timestamp,
                         datetime(2017, 9, 14, 15, 40, 0, tzinfo=utc))

    def test_get_dom_element_id(self):
        """Testing ChangeEntry.get_dom_element_id"""
        entry = ChangeEntry(request=self.request,
                            review_request=self.review_request,
                            changedesc=self.changedesc,
                            collapsed=False,
                            data=self.data)

        self.assertEqual(entry.get_dom_element_id(), 'changedesc123')

    def test_get_js_model_data(self):
        """Testing ChangeEntry.get_js_model_data for standard ChangeDescription
        """
        entry = ChangeEntry(request=self.request,
                            review_request=self.review_request,
                            changedesc=self.changedesc,
                            collapsed=False,
                            data=self.data)

        self.assertEqual(entry.get_js_model_data(), {
            'pendingStatusUpdates': False,
        })

    @add_fixtures(['test_scmtools'])
    def test_get_js_model_data_with_status_updates(self):
        """Testing ChangeEntry.get_js_model_data for ChangeDescription with
        status updates
        """
        self.review_request.repository = self.create_repository()
        diffset = self.create_diffset(self.review_request)
        filediff = self.create_filediff(diffset)

        review = self.create_review(self.review_request,
                                    body_top='Body top',
                                    body_bottom='Body bottom',
                                    ship_it=True)
        comment1 = self.create_diff_comment(review, filediff)
        comment2 = self.create_diff_comment(review, filediff)
        review.publish()

        # This is needed by the entry's add_comment(). It's normally built when
        # creating the entries and their data.
        comment1.review_obj = review
        comment2.review_obj = review

        status_update = self.create_status_update(
            self.review_request,
            review=review,
            change_description=self.changedesc)

        entry = ChangeEntry(request=self.request,
                            review_request=self.review_request,
                            changedesc=self.changedesc,
                            collapsed=False,
                            data=self.data)
        entry.add_update(status_update)
        entry.add_comment('diff_comments', comment1)
        entry.add_comment('diff_comments', comment2)

        self.assertEqual(entry.get_js_model_data(), {
            'reviewsData': [
                {
                    'id': review.pk,
                    'bodyTop': 'Body top',
                    'bodyBottom': 'Body bottom',
                    'public': True,
                    'shipIt': True,
                },
            ],
            'diffCommentsData': [
                (six.text_type(comment1.pk), six.text_type(filediff.pk)),
                (six.text_type(comment2.pk), six.text_type(filediff.pk)),
            ],
            'pendingStatusUpdates': False,
        })

    def test_build_entries(self):
        """Testing ChangeEntry.build_entries"""
        changedesc1 = self.changedesc
        changedesc2 = self.review_request.changedescs.create(
            timestamp=changedesc1.timestamp + timedelta(days=1),
            public=True)

        review = self.create_review(self.review_request, public=True)
        comment = self.create_general_comment(review)
        status_update = self.create_status_update(
            self.review_request,
            review=review,
            change_description=changedesc2)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entries = list(ChangeEntry.build_entries(self.data))

        # These will actually be in database query order (newest to oldest),
        # not the order shown on the page.
        entry = entries[0]
        self.assertEqual(entry.changedesc, changedesc2)
        self.assertFalse(entry.collapsed)
        self.assertEqual(entry.status_updates, [status_update])
        self.assertEqual(
            entry.status_updates_by_review,
            {
                review.pk: status_update,
            })
        self.assertEqual(
            entry.status_updates[0].comments,
            {
                'diff_comments': [],
                'screenshot_comments': [],
                'file_attachment_comments': [],
                'general_comments': [comment],
            })

        entry = entries[1]
        self.assertEqual(entry.changedesc, changedesc1)
        self.assertTrue(entry.collapsed)
        self.assertEqual(entry.status_updates, [])

    def test_is_entry_new_with_timestamp(self):
        """Testing ChangeEntry.is_entry_new with timestamp"""
        entry = ChangeEntry(
            request=self.request,
            review_request=self.review_request,
            changedesc=self.changedesc,
            collapsed=False,
            data=self.data)

        user = User.objects.create(username='test-user')

        self.assertTrue(entry.is_entry_new(
            last_visited=self.changedesc.timestamp - timedelta(days=1),
            user=user))
        self.assertFalse(entry.is_entry_new(
            last_visited=self.changedesc.timestamp,
            user=user))
        self.assertFalse(entry.is_entry_new(
            last_visited=self.changedesc.timestamp + timedelta(days=1),
            user=user))
