"""Unit tests for reviewboard.reviews.views.ReviewRequestDetailView."""

from __future__ import unicode_literals

from datetime import timedelta

from django.contrib.auth.models import User
from django.test.html import parse_html
from django.utils import six
from djblets.extensions.hooks import TemplateHook
from djblets.extensions.models import RegisteredExtension
from djblets.siteconfig.models import SiteConfiguration
from kgb import SpyAgency

from reviewboard.extensions.base import Extension, get_extension_manager
from reviewboard.reviews.detail import InitialStatusUpdatesEntry, ReviewEntry
from reviewboard.reviews.fields import get_review_request_fieldsets
from reviewboard.reviews.models import Comment, GeneralComment, Review
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class ReviewRequestDetailViewTests(SpyAgency, TestCase):
    """Unit tests for reviewboard.reviews.views.ReviewRequestDetailView."""

    fixtures = ['test_users', 'test_scmtools', 'test_site']

    def test_get(self):
        """Testing ReviewRequestDetailView.get"""
        review_request = self.create_review_request(publish=True)

        response = self.client.get('/r/%d/' % review_request.id)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['review_request'].pk,
                         review_request.pk)

    def test_context(self):
        """Testing ReviewRequestDetailView context variables"""
        # Make sure this request is made while logged in, to catch the
        # login-only pieces of the review_detail view.
        self.client.login(username='admin', password='admin')

        username = 'admin'
        summary = 'This is a test summary'
        description = 'This is my description'
        testing_done = 'Some testing'

        review_request = self.create_review_request(
            publish=True,
            submitter=username,
            summary=summary,
            description=description,
            testing_done=testing_done)

        response = self.client.get('/r/%s/' % review_request.pk)
        self.assertEqual(response.status_code, 200)

        review_request = response.context['review_request']
        self.assertEqual(review_request.submitter.username, username)
        self.assertEqual(review_request.summary, summary)
        self.assertEqual(review_request.description, description)
        self.assertEqual(review_request.testing_done, testing_done)
        self.assertEqual(review_request.pk, review_request.pk)

    def test_diff_comment_ordering(self):
        """Testing ReviewRequestDetailView and ordering of diff comments on a
        review
        """
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'
        comment_text_3 = 'Comment text 3'

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        # Create the users who will be commenting.
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='dopey')

        # Create the master review.
        main_review = self.create_review(review_request, user=user1)
        main_comment = self.create_diff_comment(main_review, filediff,
                                                text=comment_text_1)
        main_review.publish()

        # First reply
        reply1 = self.create_reply(
            main_review,
            user=user1,
            timestamp=(main_review.timestamp + timedelta(days=1)))
        self.create_diff_comment(reply1, filediff, text=comment_text_2,
                                 reply_to=main_comment)

        # Second reply
        reply2 = self.create_reply(
            main_review,
            user=user2,
            timestamp=(main_review.timestamp + timedelta(days=2)))
        self.create_diff_comment(reply2, filediff, text=comment_text_3,
                                 reply_to=main_comment)

        # Publish them out of order.
        reply2.publish()
        reply1.publish()

        # Make sure they published in the order expected.
        self.assertTrue(reply1.timestamp > reply2.timestamp)

        # Make sure they're looked up in the order expected.
        comments = list(
            Comment.objects
            .filter(review__review_request=review_request)
            .order_by('timestamp')
        )
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_3)
        self.assertEqual(comments[2].text, comment_text_2)

        # Now figure out the order on the page.
        response = self.client.get('/r/%d/' % review_request.pk)
        self.assertEqual(response.status_code, 200)

        entries = response.context['entries']
        initial_entries = entries['initial']
        self.assertEqual(len(initial_entries), 1)
        self.assertIsInstance(initial_entries[0], InitialStatusUpdatesEntry)

        main_entries = entries['main']
        self.assertEqual(len(main_entries), 1)
        entry = main_entries[0]
        self.assertIsInstance(entry, ReviewEntry)
        comments = entry.comments['diff_comments']
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].text, comment_text_1)

        replies = comments[0].public_replies()
        self.assertEqual(len(replies), 2)
        self.assertEqual(replies[0].text, comment_text_3)
        self.assertEqual(replies[1].text, comment_text_2)

    def test_general_comment_ordering(self):
        """Testing ReviewRequestDetailView and ordering of general comments on
        a review
        """
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'
        comment_text_3 = 'Comment text 3'
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        # Create the users who will be commenting.
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='dopey')

        # Create the master review.
        main_review = self.create_review(review_request, user=user1)
        main_comment = self.create_general_comment(main_review,
                                                   text=comment_text_1)
        main_review.publish()

        # First reply
        reply1 = self.create_reply(
            main_review,
            user=user1,
            timestamp=(main_review.timestamp + timedelta(days=1)))
        self.create_general_comment(reply1, text=comment_text_2,
                                    reply_to=main_comment)

        # Second reply
        reply2 = self.create_reply(
            main_review,
            user=user2,
            timestamp=(main_review.timestamp + timedelta(days=2)))
        self.create_general_comment(reply2, text=comment_text_3,
                                    reply_to=main_comment)

        # Publish them out of order.
        reply2.publish()
        reply1.publish()

        # Make sure they published in the order expected.
        self.assertTrue(reply1.timestamp > reply2.timestamp)

        # Make sure they're looked up in the order expected.
        comments = list(
            GeneralComment.objects
            .filter(review__review_request=review_request)
            .order_by('timestamp')
        )
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_3)
        self.assertEqual(comments[2].text, comment_text_2)

    def test_file_attachments_visibility(self):
        """Testing ReviewRequestDetailView default visibility of file
        attachments
        """
        caption_1 = 'File Attachment 1'
        caption_2 = 'File Attachment 2'
        caption_3 = 'File Attachment 3'
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'

        user1 = User.objects.get(username='doc')
        review_request = self.create_review_request()

        # Add two file attachments. One active, one inactive.
        file1 = self.create_file_attachment(review_request, caption=caption_1)
        file2 = self.create_file_attachment(review_request, caption=caption_2,
                                            active=False)
        review_request.publish(user1)

        # Create a third file attachment on a draft.
        self.create_file_attachment(review_request, caption=caption_3,
                                    draft=True)

        # Create the review with comments for each screenshot.
        review = Review.objects.create(review_request=review_request,
                                       user=user1)
        review.file_attachment_comments.create(file_attachment=file1,
                                               text=comment_text_1)
        review.file_attachment_comments.create(file_attachment=file2,
                                               text=comment_text_2)
        review.publish()

        # Check that we can find all the objects we expect on the page.
        self.client.login(username='doc', password='doc')
        response = self.client.get('/r/%d/' % review_request.pk)
        self.assertEqual(response.status_code, 200)

        file_attachments = response.context['file_attachments']
        self.assertEqual(len(file_attachments), 2)
        self.assertEqual(file_attachments[0].caption, caption_1)
        self.assertEqual(file_attachments[1].caption, caption_3)

        # Make sure that other users won't see the draft one.
        self.client.logout()
        response = self.client.get('/r/%d/' % review_request.pk)
        self.assertEqual(response.status_code, 200)

        file_attachments = response.context['file_attachments']
        self.assertEqual(len(file_attachments), 1)
        self.assertEqual(file_attachments[0].caption, caption_1)

        # Make sure we loaded the reviews and all data correctly.
        entries = response.context['entries']
        initial_entries = entries['initial']
        self.assertEqual(len(initial_entries), 1)
        self.assertIsInstance(initial_entries[0], InitialStatusUpdatesEntry)

        main_entries = entries['main']
        self.assertEqual(len(main_entries), 1)
        entry = main_entries[0]
        self.assertIsInstance(entry, ReviewEntry)

        comments = entry.comments['file_attachment_comments']
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_2)

    def test_screenshots_visibility(self):
        """Testing ReviewRequestDetailView default visibility of screenshots"""
        caption_1 = 'Screenshot 1'
        caption_2 = 'Screenshot 2'
        caption_3 = 'Screenshot 3'
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'

        user1 = User.objects.get(username='doc')
        review_request = self.create_review_request()

        # Add two screenshots. One active, one inactive.
        screenshot1 = self.create_screenshot(review_request, caption=caption_1)
        screenshot2 = self.create_screenshot(review_request, caption=caption_2,
                                             active=False)
        review_request.publish(user1)

        # Add a third screenshot on a draft.
        self.create_screenshot(review_request, caption=caption_3, draft=True)

        # Create the review with comments for each screenshot.
        user1 = User.objects.get(username='doc')
        review = Review.objects.create(review_request=review_request,
                                       user=user1)
        review.screenshot_comments.create(screenshot=screenshot1,
                                          text=comment_text_1,
                                          x=10,
                                          y=10,
                                          w=20,
                                          h=20)
        review.screenshot_comments.create(screenshot=screenshot2,
                                          text=comment_text_2,
                                          x=0,
                                          y=0,
                                          w=10,
                                          h=10)
        review.publish()

        # Check that we can find all the objects we expect on the page.
        self.client.login(username='doc', password='doc')
        response = self.client.get('/r/%d/' % review_request.pk)
        self.assertEqual(response.status_code, 200)

        screenshots = response.context['screenshots']
        self.assertEqual(len(screenshots), 2)
        self.assertEqual(screenshots[0].caption, caption_1)
        self.assertEqual(screenshots[1].caption, caption_3)

        # Make sure that other users won't see the draft one.
        self.client.logout()
        response = self.client.get('/r/%d/' % review_request.pk)
        self.assertEqual(response.status_code, 200)

        screenshots = response.context['screenshots']
        self.assertEqual(len(screenshots), 1)
        self.assertEqual(screenshots[0].caption, caption_1)

        entries = response.context['entries']
        initial_entries = entries['initial']
        self.assertEqual(len(initial_entries), 1)
        self.assertIsInstance(initial_entries[0], InitialStatusUpdatesEntry)

        main_entries = entries['main']
        self.assertEqual(len(main_entries), 1)
        entry = main_entries[0]
        self.assertIsInstance(entry, ReviewEntry)

        # Make sure we loaded the reviews and all data correctly.
        comments = entry.comments['screenshot_comments']
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_2)

    def test_with_anonymous_and_requires_site_wide_login(self):
        """Testing ReviewRequestDetailView with anonymous user and site-wide
        login required
        """
        with self.siteconfig_settings({'auth_require_sitewide_login': True},
                                      reload_settings=False):
            self.create_review_request(publish=True)

            response = self.client.get('/r/1/')
            self.assertEqual(response.status_code, 302)

    def test_etag_with_issues(self):
        """Testing ReviewRequestDetailView ETags with issue status toggling"""
        self.client.login(username='doc', password='doc')

        # Some objects we need.
        user = User.objects.get(username='doc')

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        # Create a review.
        review = self.create_review(review_request, user=user)
        comment = self.create_diff_comment(review, filediff,
                                           issue_opened=True)
        review.publish()

        # Get the etag
        response = self.client.get(review_request.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        etag1 = response['ETag']
        self.assertNotEqual(etag1, '')

        # Change the issue status
        comment.issue_status = Comment.RESOLVED
        comment.save()

        # Check the etag again
        response = self.client.get(review_request.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        etag2 = response['ETag']
        self.assertNotEqual(etag2, '')

        # Make sure they're not equal
        self.assertNotEqual(etag1, etag2)

    def test_review_request_box_template_hooks(self):
        """Testing ReviewRequestDetailView template hooks for the review
        request box
        """
        class ContentTemplateHook(TemplateHook):
            def initialize(self, name, content):
                super(ContentTemplateHook, self).initialize(name)
                self.content = content

            def render_to_string(self, request,  context):
                return self.content

        class TestExtension(Extension):
            registration = RegisteredExtension.objects.create(
                class_name='test-extension',
                name='test-extension',
                enabled=True,
                installed=True)

        extension = TestExtension(get_extension_manager())
        review_request = self.create_review_request(publish=True)
        hooks = []

        for name in ('before-review-request-summary',
                     'review-request-summary-pre',
                     'review-request-summary-post',
                     'after-review-request-summary-post',
                     'before-review-request-fields',
                     'after-review-request-fields',
                     'before-review-request-extra-panes',
                     'review-request-extra-panes-pre',
                     'review-request-extra-panes-post',
                     'after-review-request-extra-panes'):
            hooks.append(ContentTemplateHook(extension, name,
                                             '[%s here]' % name))

        # Turn off some parts of the page, to simplify the resulting HTML
        # and shorten render/parse times.
        self.spy_on(get_review_request_fieldsets,
                    call_fake=lambda *args, **kwargs: [])

        response = self.client.get(
            local_site_reverse('review-request-detail',
                               args=[review_request.display_id]))
        self.assertEqual(response.status_code, 200)

        parsed_html = six.text_type(
            parse_html(response.content.decode('utf-8')))
        self.assertIn(
            '<div class="review-request-body">\n'
            '[before-review-request-summary here]',
            parsed_html)
        self.assertIn(
            '<div class="review-request-section review-request-summary">\n'
            '[review-request-summary-pre here]',
            parsed_html)
        self.assertIn(
            '</time>\n</p>[review-request-summary-post here]\n</div>',
            parsed_html)
        self.assertIn(
            '[before-review-request-fields here]'
            '<table class="review-request-section"'
            ' id="review-request-details">',
            parsed_html)
        self.assertIn(
            '</div>'
            '[after-review-request-fields here] '
            '[before-review-request-extra-panes here]'
            '<div id="review-request-extra">\n'
            '[review-request-extra-panes-pre here]',
            parsed_html)
        self.assertIn(
            '</div>[review-request-extra-panes-post here]\n'
            '</div>[after-review-request-extra-panes here]\n'
            '</div>',
            parsed_html)
