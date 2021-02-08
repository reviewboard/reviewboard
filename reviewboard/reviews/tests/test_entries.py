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
from reviewboard.reviews.models import (BaseComment, GeneralComment,
                                        StatusUpdate)
from reviewboard.testing import TestCase


class BaseReviewRequestPageEntryTests(SpyAgency, TestCase):
    """Unit tests for BaseReviewRequestPageEntry."""

    fixtures = ['test_users']

    def setUp(self):
        super(BaseReviewRequestPageEntryTests, self).setUp()

        self.review_request = self.create_review_request()

        self.request = RequestFactory().request()
        self.request.user = AnonymousUser()

        self.data = ReviewRequestPageData(review_request=self.review_request,
                                          request=self.request)

    def test_init_with_no_updated_timestamp(self):
        """Testing BaseReviewRequestPageEntry.__init__ without an
        updated_timestamp specified
        """
        entry = BaseReviewRequestPageEntry(
            data=self.data,
            entry_id='test',
            added_timestamp=datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))

        self.assertEqual(entry.updated_timestamp,
                         datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))

    def test_render_to_string(self):
        """Testing BaseReviewRequestPageEntry.render_to_string"""
        entry = BaseReviewRequestPageEntry(data=self.data,
                                           entry_id='test',
                                           added_timestamp=None)
        entry.template_name = 'reviews/entries/base.html'

        html = entry.render_to_string(
            self.request,
            RequestContext(self.request, {
                'last_visited': timezone.now(),
            }))

        self.assertNotEqual(html, '')

    def test_render_to_string_with_entry_pos_main(self):
        """Testing BaseReviewRequestPageEntry.render_to_string with
        entry_pos=ENTRY_POS_MAIN
        """
        entry = BaseReviewRequestPageEntry(data=self.data,
                                           entry_id='test',
                                           added_timestamp=None)
        entry.template_name = 'reviews/entries/base.html'
        entry.entry_pos = BaseReviewRequestPageEntry.ENTRY_POS_MAIN

        html = entry.render_to_string(
            self.request,
            RequestContext(self.request, {
                'last_visited': timezone.now(),
            }))
        self.assertIn('<div class="box-statuses">', html)

    def test_render_to_string_with_entry_pos_initial(self):
        """Testing BaseReviewRequestPageEntry.render_to_string with
        entry_pos=ENTRY_POS_INITIAL
        """
        entry = BaseReviewRequestPageEntry(data=self.data,
                                           entry_id='test',
                                           added_timestamp=None)
        entry.template_name = 'reviews/entries/base.html'
        entry.entry_pos = BaseReviewRequestPageEntry.ENTRY_POS_INITIAL

        html = entry.render_to_string(
            self.request,
            RequestContext(self.request, {
                'last_visited': timezone.now(),
            }))
        self.assertNotIn('<div class="box-statuses">', html)

    def test_render_to_string_with_new_entry(self):
        """Testing BaseReviewRequestPageEntry.render_to_string with
        entry_is_new=True
        """
        entry = BaseReviewRequestPageEntry(
            data=self.data,
            entry_id='test',
            added_timestamp=datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))
        entry.template_name = 'reviews/entries/base.html'

        self.request.user = User.objects.create_user(username='test-user',
                                                     email='user@example.com')

        html = entry.render_to_string(
            self.request,
            RequestContext(self.request, {
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
            data=self.data,
            entry_id='test',
            added_timestamp=datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))
        entry.template_name = 'reviews/entries/base.html'

        self.request.user = User.objects.create_user(username='test-user',
                                                     email='user@example.com')

        html = entry.render_to_string(
            self.request,
            RequestContext(self.request, {
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
        entry = BaseReviewRequestPageEntry(data=self.data,
                                           entry_id='test',
                                           added_timestamp=None)

        html = entry.render_to_string(
            self.request,
            RequestContext(self.request, {
                'last_visited': timezone.now(),
            }))
        self.assertEqual(html, '')

    def test_render_to_string_with_has_content_false(self):
        """Testing BaseReviewRequestPageEntry.render_to_string with
        has_content=False
        """
        entry = BaseReviewRequestPageEntry(data=self.data,
                                           entry_id='test',
                                           added_timestamp=None)
        entry.template_name = 'reviews/entries/base.html'
        entry.has_content = False

        html = entry.render_to_string(
            self.request,
            RequestContext(self.request, {
                'last_visited': timezone.now(),
            }))
        self.assertEqual(html, '')

    def test_render_to_string_with_exception(self):
        """Testing BaseReviewRequestPageEntry.render_to_string with
        exception
        """
        entry = BaseReviewRequestPageEntry(data=self.data,
                                           entry_id='test',
                                           added_timestamp=None)
        entry.template_name = 'reviews/entries/NOT_FOUND.html'

        from reviewboard.reviews.detail import logger

        self.spy_on(logger.exception)

        html = entry.render_to_string(
            self.request,
            RequestContext(self.request, {
                'last_visited': timezone.now(),
            }))

        self.assertEqual(html, '')
        self.assertTrue(logger.exception.spy.called)
        self.assertEqual(logger.exception.spy.calls[0].args[0],
                         'Error rendering template for %s (ID=%s): %s')

    def test_is_entry_new_with_timestamp(self):
        """Testing BaseReviewRequestPageEntry.is_entry_new with timestamp"""
        entry = BaseReviewRequestPageEntry(
            data=self.data,
            entry_id='test',
            added_timestamp=datetime(2017, 9, 7, 15, 36, 0, tzinfo=utc))

        user = User.objects.create_user(username='test-user',
                                        email='user@example.com')

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
        entry = BaseReviewRequestPageEntry(data=self.data,
                                           entry_id='test',
                                           added_timestamp=None)

        self.assertFalse(entry.is_entry_new(
            last_visited=datetime(2017, 9, 7, 10, 0, 0, tzinfo=utc),
            user=User.objects.create_user(username='test-user',
                                          email='user@example.com')))

    def test_collapsed_with_older_than_last_visited(self):
        """Testing BaseReviewRequestPageEntry.collapsed with entry older than
        last visited
        """
        self.data.latest_changedesc_timestamp = \
            self.review_request.time_added + timedelta(days=5)
        self.data.last_visited = datetime(2017, 9, 7, 10, 0, 0, tzinfo=utc)

        entry = BaseReviewRequestPageEntry(
            data=self.data,
            entry_id='test',
            added_timestamp=self.data.last_visited - timedelta(days=2),
            updated_timestamp=self.data.last_visited - timedelta(days=1))
        self.assertTrue(entry.collapsed)

    def test_collapsed_with_newer_than_last_visited(self):
        """Testing BaseReviewRequestPageEntry.collapsed with entry newer than
        last visited
        """
        self.data.last_visited = datetime(2017, 9, 7, 10, 0, 0, tzinfo=utc)

        entry = BaseReviewRequestPageEntry(
            data=self.data,
            entry_id='test',
            added_timestamp=self.data.last_visited,
            updated_timestamp=self.data.last_visited + timedelta(days=1))
        self.assertFalse(entry.collapsed)

    def test_collapsed_without_last_visited(self):
        """Testing BaseReviewRequestPageEntry.collapsed without last visited
        timestamp
        """
        entry = BaseReviewRequestPageEntry(
            data=self.data,
            entry_id='test',
            added_timestamp=datetime(2017, 9, 6, 10, 0, 0, tzinfo=utc),
            updated_timestamp=datetime(2017, 9, 7, 10, 0, 0, tzinfo=utc))
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_older_than_changedesc(self):
        """Testing BaseReviewRequestPageEntry.collapsed with older than latest
        Change Description
        """
        self.data.latest_changedesc_timestamp = \
            self.review_request.time_added + timedelta(days=5)
        self.data.last_visited = \
            self.review_request.time_added + timedelta(days=10)

        entry = BaseReviewRequestPageEntry(
            data=self.data,
            entry_id='test',
            added_timestamp=(self.data.latest_changedesc_timestamp -
                             timedelta(days=2)),
            updated_timestamp=(self.data.latest_changedesc_timestamp -
                               timedelta(days=1)))
        self.assertTrue(entry.collapsed)

    def test_collapsed_with_newer_than_changedesc(self):
        """Testing BaseReviewRequestPageEntry.collapsed with newer than latest
        Change Description
        """
        self.data.latest_changedesc_timestamp = self.review_request.time_added
        self.data.last_visited = \
            self.review_request.time_added + timedelta(days=10)

        entry = BaseReviewRequestPageEntry(
            data=self.data,
            entry_id='test',
            added_timestamp=self.data.latest_changedesc_timestamp,
            updated_timestamp=(self.data.latest_changedesc_timestamp +
                               timedelta(days=1)))
        self.assertFalse(entry.collapsed)


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

    def test_add_update_with_not_yet_run(self):
        """Testing StatusUpdatesEntryMixin.add_update with NOT_YET_RUN"""
        status_update = StatusUpdate(state=StatusUpdate.NOT_YET_RUN)
        entry = StatusUpdatesEntryMixin()
        entry.add_update(status_update)

        self.assertEqual(entry.status_updates, [status_update])
        self.assertEqual(status_update.header_class,
                         'status-update-state-not-yet-run')

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
    def test_add_update_html_rendering_with_timeout_can_retry(self):
        """Testing StatusUpdatesEntryMixin.add_update HTML rendering with
        timeout and retry
        """
        review_request = self.create_review_request()
        status_update = StatusUpdate(state=StatusUpdate.TIMEOUT,
                                     description='My description.',
                                     summary='My summary.',
                                     review_request=review_request)
        status_update.extra_data['can_retry'] = True
        status_update.save()
        entry = StatusUpdatesEntryMixin()
        entry.add_update(status_update)

        self.assertHTMLEqual(
            status_update.summary_html,
            ('<div class="status-update-summary-entry'
             ' status-update-state-failure">\n'
             ' <span class="summary">My summary.</span>\n'
             ' timed out.\n'
             ' <input class="status-update-request-run"'
             '        data-status-update-id="1"'
             '        type="button" value="Retry" />'
             '</div>'))

    @add_fixtures(['test_users'])
    def test_add_update_html_rendering_with_not_yet_run(self):
        """Testing StatusUpdatesEntryMixin.add_update HTML rendering with not
        yet run
        """
        review_request = self.create_review_request()
        status_update = StatusUpdate(state=StatusUpdate.NOT_YET_RUN,
                                     description='My description.',
                                     summary='My summary.',
                                     review_request=review_request)
        status_update.save()
        entry = StatusUpdatesEntryMixin()
        entry.add_update(status_update)

        self.assertHTMLEqual(
            status_update.summary_html,
            ('<div class="status-update-summary-entry'
             ' status-update-state-not-yet-run">\n'
             ' <span class="summary">My summary.</span>\n'
             ' not yet run.\n'
             ' <input class="status-update-request-run"'
             '        data-status-update-id="1"'
             '        type="button" value="Run" />'
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
            entry.add_update(StatusUpdate(state=StatusUpdate.NOT_YET_RUN))

        for i in range(5):
            entry.add_update(StatusUpdate(state=StatusUpdate.ERROR))

        for i in range(6):
            entry.add_update(StatusUpdate(state=StatusUpdate.TIMEOUT))

        entry.finalize()

        self.assertEqual(
            entry.state_summary,
            '1 failed, 2 succeeded, 3 pending, 4 not yet run, '
            '5 failed with error, 6 timed out')

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

    def test_finalize_with_not_yet_run(self):
        """Testing StatusUpdatesEntryMixin.finalize with NOT_YET_RUN"""
        entry = StatusUpdatesEntryMixin()
        entry.add_update(StatusUpdate(state=StatusUpdate.NOT_YET_RUN))
        entry.finalize()

        self.assertEqual(entry.state_summary, '1 not yet run')
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
        entry.add_update(StatusUpdate(state=StatusUpdate.NOT_YET_RUN))
        entry.finalize()

        self.assertEqual(entry.state_summary,
                         '1 failed, 1 succeeded, 1 pending, 1 not yet run')
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
        entry.data = data
        entry.populate_status_updates(status_updates)

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
        entry.data = data
        entry.populate_status_updates(status_updates)

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
            timestamp=datetime(2017, 9, 14, 15, 40, 0, tzinfo=utc),
            state=StatusUpdate.DONE_FAILURE)

        self.data = ReviewRequestPageData(
            review_request=self.review_request,
            request=self.request,
            last_visited=self.review_request.time_added + timedelta(days=10))

    def test_added_timestamp(self):
        """Testing InitialStatusUpdatesEntry.added_timestamp"""
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = InitialStatusUpdatesEntry(data=self.data)

        self.assertEqual(entry.added_timestamp,
                         datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))

    def test_updated_timestamp(self):
        """Testing InitialStatusUpdatesEntry.updated_timestamp"""
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = InitialStatusUpdatesEntry(data=self.data)

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

    def test_is_entry_new_with_timestamp(self):
        """Testing InitialStatusUpdatesEntry.is_entry_new"""
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        user = User.objects.create_user(username='test-user',
                                        email='user@example.com')
        entry = InitialStatusUpdatesEntry(data=self.data)

        self.assertFalse(entry.is_entry_new(
            last_visited=self.review_request.last_updated - timedelta(days=1),
            user=user))

    def test_collapsed_with_no_changedescs_and_last_visited(self):
        """Testing InitialStatusUpdatesEntry.collapsed with no Change
        Descriptions and page previously visited
        """
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertTrue(len(self.data.changedescs) == 0)

        entry = InitialStatusUpdatesEntry(data=self.data)
        self.assertTrue(entry.collapsed)

    def test_collapsed_with_no_changedescs_and_not_last_visited(self):
        """Testing InitialStatusUpdatesEntry.collapsed with no Change
        Descriptions and page not previously visited
        """
        self.data.last_visited = None

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertTrue(len(self.data.changedescs) == 0)

        entry = InitialStatusUpdatesEntry(data=self.data)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_changedescs_and_last_visited(self):
        """Testing InitialStatusUpdatesEntry.collapsed with Change Descriptions
        and page previously visited
        """
        self.review_request.changedescs.create(public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertTrue(len(self.data.changedescs) > 0)

        entry = InitialStatusUpdatesEntry(data=self.data)
        self.assertTrue(entry.collapsed)

    def test_collapsed_with_changedescs_and_no_last_visited(self):
        """Testing InitialStatusUpdatesEntry.collapsed with Change Descriptions
        and page not previously visited
        """
        self.data.last_visited = None
        self.review_request.changedescs.create(public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertTrue(len(self.data.changedescs) > 0)

        entry = InitialStatusUpdatesEntry(data=self.data)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_pending_status_updates(self):
        """Testing InitialStatusUpdatesEntry.collapsed with pending status
        updates
        """
        self.status_update.state = StatusUpdate.PENDING
        self.status_update.review = None
        self.status_update.save(update_fields=('state', 'review'))

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = InitialStatusUpdatesEntry(data=self.data)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_not_yet_run_status_updates(self):
        """Testing InitialStatusUpdatesEntry.collapsed with not yet run status
        updates
        """
        self.status_update.state = StatusUpdate.NOT_YET_RUN
        self.status_update.review = None
        self.status_update.save(update_fields=('state', 'review'))

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = InitialStatusUpdatesEntry(data=self.data)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_status_update_timestamp_gt_last_visited(self):
        """Testing InitialStatusUpdatesEntry.collapsed with status update
        timestamp newer than last visited
        """
        # To update the status update's timestamp, we need to perform an
        # update() call on the queryset and reload.
        StatusUpdate.objects.filter(pk=self.status_update.pk).update(
            timestamp=self.data.last_visited + timedelta(days=1))
        self.status_update = StatusUpdate.objects.get(pk=self.status_update.pk)

        self.assertTrue(self.status_update.timestamp > self.data.last_visited)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = InitialStatusUpdatesEntry(data=self.data)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_status_update_timestamp_lt_last_visited(self):
        """Testing InitialStatusUpdatesEntry.collapsed with status update
        timestamp newer than last visited
        """
        # To update the status update's timestamp, we need to perform an
        # update() call on the queryset and reload.
        StatusUpdate.objects.filter(pk=self.status_update.pk).update(
            timestamp=self.data.last_visited - timedelta(days=1))
        self.status_update = StatusUpdate.objects.get(pk=self.status_update.pk)

        self.assertTrue(self.status_update.timestamp < self.data.last_visited)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = InitialStatusUpdatesEntry(data=self.data)
        self.assertTrue(entry.collapsed)

    def test_collapsed_with_status_updates_and_no_reviews(self):
        """Testing InitialStatusUpdatesEntry.collapsed with status updates
        and no reviews
        """
        self.status_update.state = StatusUpdate.DONE_SUCCESS
        self.status_update.review = None
        self.status_update.save(update_fields=('state', 'review'))

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = InitialStatusUpdatesEntry(data=self.data)
        self.assertTrue(entry.collapsed)

    def test_collapsed_with_status_updates_and_draft_comment_replies(self):
        """Testing InitialStatusUpdatesEntry.collapsed with status updates
        containing draft comment replies
        """
        self.request.user = self.review_request.submitter

        self.assertEqual(self.status_update.state, StatusUpdate.DONE_FAILURE)

        reply = self.create_reply(self.review, user=self.request.user)
        self.create_general_comment(reply, reply_to=self.general_comment)

        self.review_request.changedescs.create(public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertIn(self.review.pk, self.data.draft_reply_comments)

        entry = InitialStatusUpdatesEntry(data=self.data)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_status_updates_and_draft_body_top_replies(self):
        """Testing InitialStatusUpdatesEntry.collapsed with status updates
        containing draft replies to body_top
        """
        self.request.user = self.review_request.submitter

        self.assertEqual(self.status_update.state, StatusUpdate.DONE_FAILURE)

        self.create_reply(self.review,
                          user=self.request.user,
                          body_top_reply_to=self.review)

        self.review_request.changedescs.create(public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertIn(self.review.pk, self.data.draft_body_top_replies)

        entry = InitialStatusUpdatesEntry(data=self.data)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_status_updates_and_draft_body_bottom_replies(self):
        """Testing InitialStatusUpdatesEntry.collapsed with status updates
        containing draft replies to body_bottom
        """
        self.request.user = self.review_request.submitter

        self.assertEqual(self.status_update.state, StatusUpdate.DONE_FAILURE)

        self.create_reply(self.review,
                          user=self.request.user,
                          body_bottom_reply_to=self.review)

        self.review_request.changedescs.create(public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertIn(self.review.pk, self.data.draft_body_bottom_replies)

        entry = InitialStatusUpdatesEntry(data=self.data)
        self.assertFalse(entry.collapsed)


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

        self.changedesc = self.review_request.changedescs.create(
            timestamp=self.review.timestamp + timedelta(days=10),
            public=True)

        self.data = ReviewRequestPageData(
            review_request=self.review_request,
            request=self.request,
            last_visited=self.changedesc.timestamp)

    def test_added_timestamp(self):
        """Testing ReviewEntry.added_timestamp"""
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ReviewEntry(data=self.data,
                            review=self.review)

        self.assertEqual(entry.added_timestamp,
                         datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))

    def test_updated_timestamp(self):
        """Testing ReviewEntry.updated_timestamp"""
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ReviewEntry(data=self.data,
                            review=self.review)

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

        entry = ReviewEntry(data=self.data,
                            review=self.review)

        self.assertEqual(entry.updated_timestamp,
                         datetime(2017, 9, 14, 15, 40, 0, tzinfo=utc))

    def test_get_dom_element_id(self):
        """Testing ReviewEntry.get_dom_element_id"""
        entry = ReviewEntry(data=self.data,
                            review=self.review)

        self.assertEqual(entry.get_dom_element_id(), 'review123')

    def test_collapsed_with_open_issues(self):
        """Testing ReviewEntry.collapsed with open issues"""
        self.create_general_comment(self.review,
                                    issue_opened=True,
                                    issue_status=BaseComment.OPEN)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ReviewEntry(data=self.data,
                            review=self.review)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_open_issues_verifying_resolved(self):
        """Testing ReviewEntry.collapsed with open issues marked Verifying
        Resolved
        """
        self.create_general_comment(
            self.review,
            issue_opened=True,
            issue_status=BaseComment.VERIFYING_RESOLVED)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ReviewEntry(data=self.data,
                            review=self.review)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_open_issues_verifying_dropped(self):
        """Testing ReviewEntry.collapsed with open issues marked Verifying
        Dropped
        """
        self.create_general_comment(self.review,
                                    issue_opened=True,
                                    issue_status=BaseComment.VERIFYING_DROPPED)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ReviewEntry(data=self.data,
                            review=self.review)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_dropped_issues(self):
        """Testing ReviewEntry.collapsed with dropped issues"""
        self.create_general_comment(self.review,
                                    issue_opened=True,
                                    issue_status=BaseComment.DROPPED)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ReviewEntry(data=self.data,
                            review=self.review)
        self.assertTrue(entry.collapsed)

    def test_collapsed_with_resolved_issues(self):
        """Testing ReviewEntry.collapsed with resolved issues"""
        self.create_general_comment(self.review,
                                    issue_opened=True,
                                    issue_status=BaseComment.RESOLVED)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ReviewEntry(data=self.data,
                            review=self.review)
        self.assertTrue(entry.collapsed)

    def test_collapsed_with_draft_reply_comments(self):
        """Testing ReviewEntry.collapsed with draft reply comments"""
        self.request.user = self.review_request.submitter

        comment = self.create_general_comment(self.review)

        reply = self.create_reply(self.review, user=self.request.user)
        self.create_general_comment(reply, reply_to=comment)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertIn(self.review.pk, self.data.draft_reply_comments)

        entry = ReviewEntry(data=self.data,
                            review=self.review)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_draft_body_top_replies(self):
        """Testing ReviewEntry.collapsed with draft replies to body_top"""
        self.request.user = self.review_request.submitter

        self.create_reply(self.review,
                          user=self.request.user,
                          body_top_reply_to=self.review)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertIn(self.review.pk, self.data.draft_body_top_replies)

        entry = ReviewEntry(data=self.data,
                            review=self.review)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_draft_body_bottom_replies(self):
        """Testing ReviewEntry.collapsed with draft replies to body_bottom"""
        self.request.user = self.review_request.submitter

        self.create_reply(self.review,
                          user=self.request.user,
                          body_bottom_reply_to=self.review)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertIn(self.review.pk, self.data.draft_body_bottom_replies)

        entry = ReviewEntry(data=self.data,
                            review=self.review)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_reply_older_than_last_visited(self):
        """Testing ReviewEntry.collapsed with reply older than last visited"""
        reply = self.create_reply(
            self.review,
            publish=True,
            timestamp=self.review.timestamp + timedelta(days=2))

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()
        self.data.last_visited = reply.timestamp + timedelta(days=1)

        entry = ReviewEntry(data=self.data,
                            review=self.review)
        self.assertTrue(entry.collapsed)

    def test_collapsed_with_reply_newer_than_last_visited(self):
        """Testing ReviewEntry.collapsed with reply newer than last visited"""
        reply = self.create_reply(
            self.review,
            publish=True,
            timestamp=self.review.timestamp + timedelta(days=2))

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()
        self.data.last_visited = reply.timestamp - timedelta(days=1)

        entry = ReviewEntry(data=self.data,
                            review=self.review)
        self.assertFalse(entry.collapsed)

    def test_get_js_model_data(self):
        """Testing ReviewEntry.get_js_model_data"""
        self.review.ship_it = True
        self.review.publish()

        entry = ReviewEntry(data=self.data,
                            review=self.review)

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

        entry = ReviewEntry(data=self.data,
                            review=self.review)
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
        entry = ReviewEntry(data=self.data,
                            review=self.review)

        self.assertFalse(entry.has_issues)
        self.assertEqual(entry.issue_open_count, 0)

        entry.add_comment('general_comments', GeneralComment())

        self.assertFalse(entry.has_issues)
        self.assertEqual(entry.issue_open_count, 0)

    def test_add_comment_with_open_issues(self):
        """Testing ReviewEntry.add_comment with comment opening an issue"""
        entry = ReviewEntry(data=self.data,
                            review=self.review)

        self.assertFalse(entry.has_issues)
        self.assertEqual(entry.issue_open_count, 0)

        entry.add_comment('general_comments',
                          GeneralComment(issue_opened=True,
                                         issue_status=GeneralComment.OPEN))

        self.assertTrue(entry.has_issues)
        self.assertEqual(entry.issue_open_count, 1)

    def test_add_comment_with_open_issues_and_viewer_is_owner(self):
        """Testing ReviewEntry.add_comment with comment opening an issue and
        the review request owner is viewing the page
        """
        self.request.user = self.review_request.submitter
        entry = ReviewEntry(data=self.data,
                            review=self.review)

        self.assertFalse(entry.has_issues)
        self.assertEqual(entry.issue_open_count, 0)

        entry.add_comment('general_comments',
                          GeneralComment(issue_opened=True,
                                         issue_status=GeneralComment.OPEN))

        self.assertTrue(entry.has_issues)
        self.assertEqual(entry.issue_open_count, 1)

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
                                  review=status_update_review,
                                  state=StatusUpdate.DONE_FAILURE)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entries = list(ReviewEntry.build_entries(self.data))

        self.assertEqual(len(entries), 2)

        # These will actually be in database query order (newest to oldest),
        # not the order shown on the page.
        entry = entries[0]
        self.assertEqual(entry.review, review2)
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

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)

        self.assertEqual(entry.added_timestamp,
                         datetime(2017, 9, 7, 17, 0, 0, tzinfo=utc))

    def test_updated_timestamp(self):
        """Testing ChangeEntry.updated_timestamp"""
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)

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

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)

        self.assertEqual(entry.updated_timestamp,
                         datetime(2017, 9, 14, 15, 40, 0, tzinfo=utc))

    def test_get_dom_element_id(self):
        """Testing ChangeEntry.get_dom_element_id"""
        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)

        self.assertEqual(entry.get_dom_element_id(), 'changedesc123')

    def test_collapsed_with_older_than_latest_changedesc(self):
        """Testing ChangeEntry.collapsed with older than latest Change
        Description
        """
        self.review_request.changedescs.create(
            timestamp=self.changedesc.timestamp + timedelta(days=1),
            public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)
        self.assertTrue(entry.collapsed)

    def test_collapsed_with_latest_changedesc(self):
        """Testing ChangeEntry.collapsed with older than latest Change
        Description
        """
        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertEqual(self.changedesc.timestamp,
                         self.data.latest_changedesc_timestamp)

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_status_updates_and_no_reviews(self):
        """Testing ChangeEntry.collapsed with status updates and no reviews"""
        self.create_status_update(self.review_request,
                                  change_description=self.changedesc,
                                  state=StatusUpdate.DONE_SUCCESS)

        self.review_request.changedescs.create(
            timestamp=self.changedesc.timestamp + timedelta(days=1),
            public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)
        self.assertTrue(entry.collapsed)

    def test_collapsed_with_status_updates_and_draft_comment_replies(self):
        """Testing ChangeEntry.collapsed with status updates containing draft
        comment replies
        """
        self.request.user = self.review_request.submitter

        review = self.create_review(self.review_request, publish=True)
        comment = self.create_general_comment(review)

        self.create_status_update(self.review_request,
                                  review=review,
                                  change_description=self.changedesc,
                                  state=StatusUpdate.DONE_FAILURE)

        reply = self.create_reply(review, user=self.request.user)
        self.create_general_comment(reply, reply_to=comment)

        self.review_request.changedescs.create(
            timestamp=self.changedesc.timestamp + timedelta(days=1),
            public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertIn(review.pk, self.data.draft_reply_comments)

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_pending_status_updates(self):
        """Testing ChangeEntry.collapsed with pending status updates"""
        self.request.user = self.review_request.submitter

        self.create_status_update(self.review_request,
                                  change_description=self.changedesc,
                                  state=StatusUpdate.PENDING)

        self.review_request.changedescs.create(
            timestamp=self.changedesc.timestamp + timedelta(days=1),
            public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_not_yet_run_status_updates(self):
        """Testing ChangeEntry.collapsed with not yet run status updates"""
        self.request.user = self.review_request.submitter

        self.create_status_update(self.review_request,
                                  change_description=self.changedesc,
                                  state=StatusUpdate.NOT_YET_RUN)

        self.review_request.changedescs.create(
            timestamp=self.changedesc.timestamp + timedelta(days=1),
            public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_status_update_timestamp_gt_last_visited(self):
        """Testing ChangeEntry.collapsed with status update timestamp newer
        than last visited
        """
        self.request.user = self.review_request.submitter
        self.data.last_visited = self.changedesc.timestamp + timedelta(days=1)

        status_update = self.create_status_update(
            self.review_request,
            change_description=self.changedesc,
            state=StatusUpdate.DONE_SUCCESS,
            timestamp=self.data.last_visited + timedelta(days=1))

        self.assertTrue(status_update.timestamp > self.data.last_visited)

        self.review_request.changedescs.create(
            timestamp=self.changedesc.timestamp + timedelta(days=1),
            public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_status_update_timestamp_lt_last_visited(self):
        """Testing ChangeEntry.collapsed with status update timestamp older
        than last visited
        """
        self.request.user = self.review_request.submitter
        self.data.last_visited = self.changedesc.timestamp + timedelta(days=1)

        status_update = self.create_status_update(
            self.review_request,
            change_description=self.changedesc,
            state=StatusUpdate.DONE_SUCCESS,
            timestamp=self.data.last_visited - timedelta(days=1))

        self.assertTrue(status_update.timestamp < self.data.last_visited)

        self.review_request.changedescs.create(
            timestamp=self.changedesc.timestamp + timedelta(days=1),
            public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)
        self.assertTrue(entry.collapsed)

    def test_collapsed_with_status_updates_and_draft_body_top_replies(self):
        """Testing ChangeEntry.collapsed with status updates containing draft
        comment replies to body_top
        """
        self.request.user = self.review_request.submitter

        review = self.create_review(self.review_request, publish=True)
        self.create_status_update(self.review_request,
                                  review=review,
                                  change_description=self.changedesc,
                                  state=StatusUpdate.DONE_FAILURE)

        self.create_reply(review,
                          user=self.request.user,
                          body_top_reply_to=review)

        self.review_request.changedescs.create(
            timestamp=self.changedesc.timestamp + timedelta(days=1),
            public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertIn(review.pk, self.data.draft_body_top_replies)

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)
        self.assertFalse(entry.collapsed)

    def test_collapsed_with_status_updates_and_draft_body_bottom_replies(self):
        """Testing ChangeEntry.collapsed with status updates containing draft
        comment replies to body_bottom
        """
        self.request.user = self.review_request.submitter

        review = self.create_review(self.review_request, publish=True)
        self.create_status_update(self.review_request,
                                  review=review,
                                  change_description=self.changedesc,
                                  state=StatusUpdate.DONE_FAILURE)

        self.create_reply(review,
                          user=self.request.user,
                          body_bottom_reply_to=review)

        self.review_request.changedescs.create(
            timestamp=self.changedesc.timestamp + timedelta(days=1),
            public=True)

        self.data.query_data_pre_etag()
        self.data.query_data_post_etag()

        self.assertIn(review.pk, self.data.draft_body_bottom_replies)

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)
        self.assertFalse(entry.collapsed)

    def test_get_js_model_data(self):
        """Testing ChangeEntry.get_js_model_data for standard ChangeDescription
        """
        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)

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

        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)
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
        entry = ChangeEntry(data=self.data,
                            changedesc=self.changedesc)

        user = User.objects.create_user(username='test-user',
                                        email='user@example.com')

        self.assertTrue(entry.is_entry_new(
            last_visited=self.changedesc.timestamp - timedelta(days=1),
            user=user))
        self.assertFalse(entry.is_entry_new(
            last_visited=self.changedesc.timestamp,
            user=user))
        self.assertFalse(entry.is_entry_new(
            last_visited=self.changedesc.timestamp + timedelta(days=1),
            user=user))
