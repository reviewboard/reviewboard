from __future__ import unicode_literals

import os

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models import (Comment, Review, ReviewRequest,
                                        ReviewRequestDraft, Screenshot)
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class ViewTests(TestCase):
    """Tests for views in reviewboard.reviews.views."""

    fixtures = ['test_users', 'test_scmtools', 'test_site']

    def setUp(self):
        super(ViewTests, self).setUp()

        self.siteconfig = SiteConfiguration.objects.get_current()
        self.siteconfig.set('auth_require_sitewide_login', False)
        self.siteconfig.save()

    def test_review_detail_redirect_no_slash(self):
        """Testing review_detail view redirecting with no trailing slash"""
        response = self.client.get('/r/1')
        self.assertEqual(response.status_code, 301)

    def test_review_detail(self):
        """Testing review_detail view"""
        review_request = self.create_review_request(publish=True)

        response = self.client.get('/r/%d/' % review_request.id)
        self.assertEqual(response.status_code, 200)

        request = self._get_context_var(response, 'review_request')
        self.assertEqual(request.pk, review_request.pk)

    def test_review_detail_context(self):
        """Testing review_detail view's context"""
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

        request = self._get_context_var(response, 'review_request')
        self.assertEqual(request.submitter.username, username)
        self.assertEqual(request.summary, summary)
        self.assertEqual(request.description, description)
        self.assertEqual(request.testing_done, testing_done)
        self.assertEqual(request.pk, review_request.pk)

    def test_review_detail_diff_comment_ordering(self):
        """Testing review_detail and ordering of diff comments on a review"""
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
        comments = list(Comment.objects.filter(
            review__review_request=review_request))
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_3)
        self.assertEqual(comments[2].text, comment_text_2)

        # Now figure out the order on the page.
        response = self.client.get('/r/%d/' % review_request.pk)
        self.assertEqual(response.status_code, 200)

        entries = response.context['entries']
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        comments = entry['comments']['diff_comments']
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].text, comment_text_1)

        replies = comments[0].public_replies()
        self.assertEqual(len(replies), 2)
        self.assertEqual(replies[0].text, comment_text_3)
        self.assertEqual(replies[1].text, comment_text_2)

    def test_review_detail_file_attachment_visibility(self):
        """Testing visibility of file attachments on review requests"""
        caption_1 = 'File Attachment 1'
        caption_2 = 'File Attachment 2'
        caption_3 = 'File Attachment 3'
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'

        user1 = User.objects.get(username='doc')
        review_request = ReviewRequest.objects.create(user1, None)

        # Add two file attachments. One active, one inactive.
        filename = os.path.join(settings.STATIC_ROOT,
                                'rb', 'images', 'trophy.png')
        f = open(filename, 'r')
        file = SimpleUploadedFile(f.name, f.read(), content_type='image/png')
        f.close()

        file1 = FileAttachment.objects.create(caption=caption_1,
                                              file=file,
                                              mimetype='image/png')
        file2 = FileAttachment.objects.create(caption=caption_2,
                                              file=file,
                                              mimetype='image/png')
        review_request.file_attachments.add(file1)
        review_request.inactive_file_attachments.add(file2)
        review_request.publish(user1)

        # Create one on a draft with a new file attachment.
        draft = ReviewRequestDraft.create(review_request)
        file3 = FileAttachment.objects.create(caption=caption_3,
                                              file=file,
                                              mimetype='image/png')
        draft.file_attachments.add(file3)

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
        self.assertEqual(len(entries), 1)
        entry = entries[0]

        comments = entry['comments']['file_attachment_comments']
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_2)

    def test_review_detail_screenshot_visibility(self):
        """Testing visibility of screenshots on review requests"""
        caption_1 = 'Screenshot 1'
        caption_2 = 'Screenshot 2'
        caption_3 = 'Screenshot 3'
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'

        user1 = User.objects.get(username='doc')
        review_request = ReviewRequest.objects.create(user1, None)

        # Add two screenshots. One active, one inactive.
        screenshot1 = Screenshot.objects.create(caption=caption_1,
                                                image='')
        screenshot2 = Screenshot.objects.create(caption=caption_2,
                                                image='')
        review_request.screenshots.add(screenshot1)
        review_request.inactive_screenshots.add(screenshot2)
        review_request.publish(user1)

        # Create one on a draft with a new screenshot.
        draft = ReviewRequestDraft.create(review_request)
        screenshot3 = Screenshot.objects.create(caption=caption_3,
                                                image='')
        draft.screenshots.add(screenshot3)

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
        self.assertEqual(len(entries), 1)
        entry = entries[0]

        # Make sure we loaded the reviews and all data correctly.
        comments = entry['comments']['screenshot_comments']
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_2)

    def test_review_detail_sitewide_login(self):
        """Testing review_detail view with site-wide login enabled"""
        self.siteconfig.set('auth_require_sitewide_login', True)
        self.siteconfig.save()

        self.create_review_request(publish=True)

        response = self.client.get('/r/1/')
        self.assertEqual(response.status_code, 302)

    def test_new_review_request(self):
        """Testing new_review_request view"""
        response = self.client.get('/r/new')
        self.assertEqual(response.status_code, 301)

        response = self.client.get('/r/new/')
        self.assertEqual(response.status_code, 302)

        self.client.login(username='grumpy', password='grumpy')

        response = self.client.get('/r/new/')
        self.assertEqual(response.status_code, 200)

    # Bug 892
    def test_interdiff(self):
        """Testing the diff viewer with interdiffs"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request, revision=1)
        self.create_filediff(
            diffset,
            source_file='/diffutils.py',
            dest_file='/diffutils.py',
            source_revision='6bba278',
            dest_detail='465d217',
            diff=(
                b'diff --git a/diffutils.py b/diffutils.py\n'
                b'index 6bba278..465d217 100644\n'
                b'--- a/diffutils.py\n'
                b'+++ b/diffutils.py\n'
                b'@@ -1,3 +1,4 @@\n'
                b'+# diffutils.py\n'
                b' import fnmatch\n'
                b' import os\n'
                b' import re\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/readme',
            dest_file='/readme',
            source_revision='d6613f5',
            dest_detail='5b50866',
            diff=(
                b'diff --git a/readme b/readme\n'
                b'index d6613f5..5b50866 100644\n'
                b'--- a/readme\n'
                b'+++ b/readme\n'
                b'@@ -1 +1,3 @@\n'
                b' Hello there\n'
                b'+\n'
                b'+Oh hi!\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/newfile',
            dest_file='/newfile',
            source_revision='PRE-CREATION',
            dest_detail='',
            diff=(
                b'diff --git a/new_file b/new_file\n'
                b'new file mode 100644\n'
                b'index 0000000..ac30bd3\n'
                b'--- /dev/null\n'
                b'+++ b/new_file\n'
                b'@@ -0,0 +1 @@\n'
                b'+This is a new file!\n'
            ))

        diffset = self.create_diffset(review_request, revision=2)
        self.create_filediff(
            diffset,
            source_file='/diffutils.py',
            dest_file='/diffutils.py',
            source_revision='6bba278',
            dest_detail='465d217',
            diff=(
                b'diff --git a/diffutils.py b/diffutils.py\n'
                b'index 6bba278..465d217 100644\n'
                b'--- a/diffutils.py\n'
                b'+++ b/diffutils.py\n'
                b'@@ -1,3 +1,4 @@\n'
                b'+# diffutils.py\n'
                b' import fnmatch\n'
                b' import os\n'
                b' import re\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/readme',
            dest_file='/readme',
            source_revision='d6613f5',
            dest_detail='5b50867',
            diff=(
                b'diff --git a/readme b/readme\n'
                b'index d6613f5..5b50867 100644\n'
                b'--- a/readme\n'
                b'+++ b/readme\n'
                b'@@ -1 +1,3 @@\n'
                b' Hello there\n'
                b'+----------\n'
                b'+Oh hi!\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/newfile',
            dest_file='/newfile',
            source_revision='PRE-CREATION',
            dest_detail='',
            diff=(
                b'diff --git a/new_file b/new_file\n'
                b'new file mode 100644\n'
                b'index 0000000..ac30bd4\n'
                b'--- /dev/null\n'
                b'+++ b/new_file\n'
                b'@@ -0,0 +1 @@\n'
                b'+This is a diffent version of this new file!\n'
            ))

        response = self.client.get('/r/1/diff/1-2/')

        # Useful for debugging any actual errors here.
        if response.status_code != 200:
            print('Error: %s' % self._get_context_var(response, 'error'))
            print(self._get_context_var(response, 'trace'))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self._get_context_var(response, 'diff_context')['num_diffs'],
            2)

        files = self._get_context_var(response, 'files')
        self.assertTrue(files)
        self.assertEqual(len(files), 2)

        self.assertEqual(files[0]['depot_filename'], '/newfile')
        self.assertIn('interfilediff', files[0])

        self.assertEqual(files[1]['depot_filename'], '/readme')
        self.assertIn('interfilediff', files[1])

    # Bug 847
    def test_interdiff_new_file(self):
        """Testing the diff viewer with interdiffs containing new files"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request, revision=1)
        self.create_filediff(
            diffset,
            source_file='/diffutils.py',
            dest_file='/diffutils.py',
            source_revision='6bba278',
            dest_detail='465d217',
            diff=(
                b'diff --git a/diffutils.py b/diffutils.py\n'
                b'index 6bba278..465d217 100644\n'
                b'--- a/diffutils.py\n'
                b'+++ b/diffutils.py\n'
                b'@@ -1,3 +1,4 @@\n'
                b'+# diffutils.py\n'
                b' import fnmatch\n'
                b' import os\n'
                b' import re\n'
            ))

        diffset = self.create_diffset(review_request, revision=2)
        self.create_filediff(
            diffset,
            source_file='/diffutils.py',
            dest_file='/diffutils.py',
            source_revision='6bba278',
            dest_detail='465d217',
            diff=(
                b'diff --git a/diffutils.py b/diffutils.py\n'
                b'index 6bba278..465d217 100644\n'
                b'--- a/diffutils.py\n'
                b'+++ b/diffutils.py\n'
                b'@@ -1,3 +1,4 @@\n'
                b'+# diffutils.py\n'
                b' import fnmatch\n'
                b' import os\n'
                b' import re\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/newfile',
            dest_file='/newfile',
            source_revision='PRE-CREATION',
            dest_detail='',
            diff=(
                b'diff --git a/new_file b/new_file\n'
                b'new file mode 100644\n'
                b'index 0000000..ac30bd4\n'
                b'--- /dev/null\n'
                b'+++ b/new_file\n'
                b'@@ -0,0 +1 @@\n'
                b'+This is a diffent version of this new file!\n'
            ))

        response = self.client.get('/r/1/diff/1-2/')

        # Useful for debugging any actual errors here.
        if response.status_code != 200:
            print('Error: %s' % self._get_context_var(response, 'error'))
            print(self._get_context_var(response, 'trace'))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self._get_context_var(response, 'diff_context')['num_diffs'],
            2)

        files = self._get_context_var(response, 'files')
        self.assertTrue(files)
        self.assertEqual(len(files), 1)

        self.assertEqual(files[0]['depot_filename'], '/newfile')
        self.assertIn('interfilediff', files[0])

    def test_review_request_etag_with_issues(self):
        """Testing review request ETags with issue status toggling"""
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

    # Bug #3384
    def test_diff_raw_content_disposition_attachment(self):
        """Testing /diff/raw/ Content-Disposition: attachment; ..."""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)

        self.create_diffset(review_request=review_request)

        response = self.client.get('/r/%d/diff/raw/' % review_request.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'],
                         'attachment; filename=diffset')

    # Bug #3704
    def test_diff_raw_multiple_content_disposition(self):
        """Testing /diff/raw/ multiple Content-Disposition issue"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)

        # Create a diffset with a comma in its name.
        self.create_diffset(review_request=review_request, name='test, comma')

        response = self.client.get('/r/%d/diff/raw/' % review_request.pk)
        filename = response['Content-Disposition']\
                           [len('attachment; filename='):]
        self.assertFalse(',' in filename)

    # Bug #4080
    def test_bug_url_with_custom_scheme(self):
        """Testing whether bug url with non-HTTP scheme loads correctly"""
        # Create a repository with a bug tracker that uses a non-standard
        # url scheme.
        repository = self.create_repository(public=True,
                                            bug_tracker='scheme://bugid=%s')
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        url = reverse('bug_url', args=(review_request.pk, '1'))
        response = self.client.get(url)

        # Test if we redirected to the correct url with correct bugID.
        self.assertEqual(response['Location'], 'scheme://bugid=1')

    def test_preview_review_request_email_access_with_debug(self):
        """Testing preview_review_request_email access with DEBUG=True"""
        review_request = self.create_review_request(publish=True)

        with self.settings(DEBUG=True):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-request-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'format': 'text',
                    }))

        self.assertEqual(response.status_code, 200)

    def test_preview_review_request_email_access_without_debug(self):
        """Testing preview_review_request_email access with DEBUG=False"""
        review_request = self.create_review_request(publish=True)

        with self.settings(DEBUG=False):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-request-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'format': 'text',
                    }))

        self.assertEqual(response.status_code, 404)

    def test_preview_review_request_email_with_valid_change_id(self):
        """Testing preview_review_request_email access with valid change ID"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)

        self.create_diffset(review_request, draft=True)
        review_request.publish(review_request.submitter)

        with self.settings(DEBUG=True):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-request-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'format': 'text',
                        'changedesc_id': review_request.changedescs.get().pk,
                    }))

        self.assertEqual(response.status_code, 200)

    def test_preview_review_request_email_with_invalid_change_id(self):
        """Testing preview_review_request_email access with invalid change ID
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)

        self.create_diffset(review_request, draft=True)
        review_request.publish(review_request.submitter)

        with self.settings(DEBUG=True):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-request-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'format': 'text',
                        'changedesc_id': 100,
                    }))

        self.assertEqual(response.status_code, 404)

    def test_preview_review_email_access_with_debug(self):
        """Testing preview_review_email access with DEBUG=True"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        with self.settings(DEBUG=True):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'review_id': review.pk,
                        'format': 'text',
                    }))

        self.assertEqual(response.status_code, 200)

    def test_preview_review_email_access_without_debug(self):
        """Testing preview_review_email access with DEBUG=False"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        with self.settings(DEBUG=False):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'review_id': review.pk,
                        'format': 'text',
                    }))

        self.assertEqual(response.status_code, 404)

    def test_preview_review_reply_email_access_with_debug(self):
        """Testing preview_review_reply_email access with DEBUG=True"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)
        reply = self.create_reply(review, publish=True)

        with self.settings(DEBUG=True):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-reply-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'review_id': review.pk,
                        'reply_id': reply.pk,
                        'format': 'text',
                    }))

        self.assertEqual(response.status_code, 200)

    def test_preview_review_reply_email_access_without_debug(self):
        """Testing preview_review_reply_email access with DEBUG=False"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)
        reply = self.create_reply(review, publish=True)

        with self.settings(DEBUG=False):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-reply-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'review_id': review.pk,
                        'reply_id': reply.pk,
                        'format': 'text',
                    }))

        self.assertEqual(response.status_code, 404)

    def test_view_screenshot_access_with_valid_id(self):
        """Testing view_screenshot access with valid screenshot for review
        request
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_view_screenshot_access_with_valid_id_and_draft(self):
        """Testing view_screenshot access with valid screenshot for review
        request draft
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request, draft=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_view_screenshot_access_with_valid_inactive_id(self):
        """Testing view_screenshot access with valid inactive screenshot for
        review request
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request, active=False)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_view_screenshot_access_with_valid_inactive_id_and_draft(self):
        """Testing view_screenshot access with valid inactive screenshot for
        review request draft
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request, draft=True,
                                            active=False)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_view_screenshot_access_with_invalid_id(self):
        """Testing view_screenshot access with invalid screenshot for review
        request
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)

        review_request2 = self.create_review_request(publish=True)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_view_screenshot_access_with_invalid_id_and_draft(self):
        """Testing view_screenshot access with invalid screenshot for review
        request draft
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request, draft=True)

        review_request2 = self.create_review_request(publish=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_view_screenshot_access_with_invalid_inactive_id(self):
        """Testing view_screenshot access with invalid inactive screenshot
        for review request
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request, active=False)

        review_request2 = self.create_review_request(publish=True)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_view_screenshot_access_with_invalid_inactive_id_and_draft(self):
        """Testing view_screenshot access with invalid inactive screenshot
        for review request draft
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request, draft=True,
                                            active=False)

        review_request2 = self.create_review_request(publish=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_review_file_attachment_access_with_valid_id(self):
        """Testing review_file_attachment access with valid attachment for
        review request
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_review_file_attachment_access_with_valid_id_and_draft(self):
        """Testing review_file_attachment access with valid attachment for
        review request draft
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request, draft=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_review_file_attachment_access_with_invalid_id(self):
        """Testing review_file_attachment access with invalid attachment for
        review request
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request)

        review_request2 = self.create_review_request(publish=True)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_review_file_attachment_access_with_invalid_id_and_draft(self):
        """Testing review_file_attachment access with invalid attachment for
        review request draft
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request, draft=True)

        review_request2 = self.create_review_request(publish=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_review_file_attachment_access_with_valid_inactive_id(self):
        """Testing review_file_attachment access with valid inactive
        attachment for review request
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request, active=False)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_review_file_attachment_access_with_valid_inactive_id_draft(self):
        """Testing review_file_attachment access with valid inactive
        attachment for review request draft
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request, draft=True,
                                                 active=False)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_review_file_attachment_access_with_invalid_inactive_id(self):
        """Testing review_file_attachment access with invalid inactive
        attachment for review request
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request, active=False)

        review_request2 = self.create_review_request(publish=True)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_review_file_attachment_access_invalid_inactive_id_draft(self):
        """Testing review_file_attachment access with invalid inactive
        attachment for review request draft
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request, draft=True,
                                                 active=False)

        review_request2 = self.create_review_request(publish=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_review_file_attachment_access_with_valid_diff_against_id(self):
        """Testing review_file_attachment access with valid diff-against
        attachment for review request
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request)
        attachment2 = self.create_file_attachment(review_request)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                    'file_attachment_diff_id': attachment2.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_review_file_attachment_access_valid_diff_against_id_draft(self):
        """Testing review_file_attachment access with valid diff-against
        attachment for review request draft
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request)
        attachment2 = self.create_file_attachment(review_request, draft=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                    'file_attachment_diff_id': attachment2.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_review_file_attachment_access_with_invalid_diff_against_id(self):
        """Testing review_file_attachment access with invalid diff-against
        attachment for review request
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request)

        review_request2 = self.create_review_request(publish=True)
        attachment2 = self.create_file_attachment(review_request2)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                    'file_attachment_diff_id': attachment2.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_review_file_attachment_access_invalid_diff_against_id_draft(self):
        """Testing review_file_attachment access with invalid diff-against
        attachment for review request draft
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request)

        review_request2 = self.create_review_request(publish=True)
        attachment2 = self.create_file_attachment(review_request2, draft=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                    'file_attachment_diff_id': attachment2.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def _get_context_var(self, response, varname):
        for context in response.context:
            if varname in context:
                return context[varname]

        return None


class UserInfoboxTests(TestCase):
    def test_unicode(self):
        """Testing user_infobox with a user with non-ascii characters"""
        user = User.objects.create_user('test', 'test@example.com')
        user.first_name = 'Test\u21b9'
        user.last_name = 'User\u2729'
        user.save()

        self.client.get(local_site_reverse('user-infobox', args=['test']))
