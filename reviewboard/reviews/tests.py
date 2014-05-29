from __future__ import print_function, unicode_literals

from datetime import timedelta
import logging
import os

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.utils import six
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.accounts.models import Profile, LocalSiteProfile
from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.forms import DefaultReviewerForm, GroupForm
from reviewboard.reviews.markdown_utils import (markdown_escape,
                                                markdown_unescape)
from reviewboard.reviews.models import (Comment,
                                        DefaultReviewer,
                                        Group,
                                        ReviewRequest,
                                        ReviewRequestDraft,
                                        Review,
                                        Screenshot)
from reviewboard.scmtools.core import Commit
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class ReviewRequestManagerTests(TestCase):
    """Tests ReviewRequestManager functions."""
    fixtures = ['test_users']

    def test_public(self):
        """Testing ReviewRequest.objects.public"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        self.create_review_request(summary='Test 1',
                                   publish=True,
                                   submitter=user1)
        self.create_review_request(summary='Test 2',
                                   submitter=user2)
        self.create_review_request(summary='Test 3',
                                   status='S',
                                   public=True,
                                   submitter=user1)
        self.create_review_request(summary='Test 4',
                                   status='S',
                                   public=True,
                                   submitter=user2)
        self.create_review_request(summary='Test 5',
                                   status='D',
                                   public=True,
                                   submitter=user1)
        self.create_review_request(summary='Test 6',
                                   status='D',
                                   submitter=user2)

        self.assertValidSummaries(
            ReviewRequest.objects.public(user=user1),
            [
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.public(status=None),
            [
                'Test 5',
                'Test 4',
                'Test 3',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.public(user=user2, status=None),
            [
                'Test 6',
                'Test 5',
                'Test 4',
                'Test 3',
                'Test 2',
                'Test 1'
            ])

    @add_fixtures(['test_scmtools'])
    def test_public_without_private_repo_access(self):
        """Testing ReviewRequest.objects.public without access to private
        repositories
        """
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertFalse(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 0)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_access(self):
        """Testing ReviewRequest.objects.public with access to private
        repositories
        """
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)
        repository.users.add(user)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_access_through_group(self):
        """Testing ReviewRequest.objects.public with access to private
        repositories
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        repository = self.create_repository(public=False)
        repository.review_groups.add(group)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 1)

    def test_public_without_private_group_access(self):
        """Testing ReviewRequest.objects.public without access to private
        group
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)
        self.assertFalse(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 0)

    def test_public_with_private_group_access(self):
        """Testing ReviewRequest.objects.public with access to private
        group
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_and_public_group(self):
        """Testing ReviewRequest.objects.public without access to private
        repositories and with access to private group
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group()

        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        review_request.target_groups.add(group)
        self.assertFalse(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 0)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_group_and_public_repo(self):
        """Testing ReviewRequest.objects.public with access to private
        group and without access to private group
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)

        repository = self.create_repository(public=False)
        repository.users.add(user)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        review_request.target_groups.add(group)
        self.assertFalse(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 0)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_and_owner(self):
        """Testing ReviewRequest.objects.public without access to private
        repository and as the submitter
        """
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    submitter=user,
                                                    publish=True)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 1)

    def test_public_with_private_group_and_owner(self):
        """Testing ReviewRequest.objects.public without access to private
        group and as the submitter
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)

        review_request = self.create_review_request(submitter=user,
                                                    publish=True)
        review_request.target_groups.add(group)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_public_with_private_repo_and_target_people(self):
        """Testing ReviewRequest.objects.public without access to private
        repository and user in target_people
        """
        user = User.objects.get(username='grumpy')

        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        review_request.target_people.add(user)
        self.assertFalse(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 0)

    def test_public_with_private_group_and_target_people(self):
        """Testing ReviewRequest.objects.public without access to private
        group and user in target_people
        """
        user = User.objects.get(username='grumpy')
        group = self.create_review_group(invite_only=True)

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)
        review_request.target_people.add(user)
        self.assertTrue(review_request.is_accessible_by(user))

        review_requests = ReviewRequest.objects.public(user=user)
        self.assertEqual(review_requests.count(), 1)

    def test_to_group(self):
        """Testing ReviewRequest.objects.to_group"""
        user1 = User.objects.get(username='doc')

        group1 = self.create_review_group(name='privgroup')
        group1.users.add(user1)

        review_request = self.create_review_request(summary='Test 1',
                                                    public=True,
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 2',
                                                    public=False,
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 3',
                                                    public=True,
                                                    status='S',
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        self.assertValidSummaries(
            ReviewRequest.objects.to_group("privgroup", None),
            [
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_group("privgroup", None, status=None),
            [
                'Test 3',
                'Test 1',
            ])

    def test_to_user_group(self):
        """Testing ReviewRequest.objects.to_user_groups"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        group1 = self.create_review_group(name='group1')
        group1.users.add(user1)

        group2 = self.create_review_group(name='group2')
        group2.users.add(user2)

        review_request = self.create_review_request(summary='Test 1',
                                                    public=True,
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 2',
                                                    submitter=user2,
                                                    public=True,
                                                    status='S')
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 3',
                                                    public=True,
                                                    submitter=user2)
        review_request.target_groups.add(group1)
        review_request.target_groups.add(group2)

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_groups("doc", local_site=None),
            [
                'Test 3',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_groups(
                "doc", status=None, local_site=None),
            [
                'Test 3',
                'Test 2',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_groups(
                "grumpy", user=user2, local_site=None),
            [
                'Test 3',
            ])

    def test_to_user_directly(self):
        """Testing ReviewRequest.objects.to_user_directly"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        group1 = self.create_review_group(name='group1')
        group1.users.add(user1)

        group2 = self.create_review_group(name='group2')
        group2.users.add(user2)

        review_request = self.create_review_request(summary='Test 1',
                                                    public=True,
                                                    submitter=user1)
        review_request.target_groups.add(group1)
        review_request.target_people.add(user2)

        review_request = self.create_review_request(summary='Test 2',
                                                    submitter=user2,
                                                    status='S')
        review_request.target_groups.add(group1)
        review_request.target_people.add(user2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 3',
                                                    public=True,
                                                    submitter=user2)
        review_request.target_groups.add(group1)
        review_request.target_groups.add(group2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 4',
                                                    public=True,
                                                    status='S',
                                                    submitter=user2)
        review_request.target_people.add(user1)

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_directly("doc", local_site=None),
            [
                'Test 3',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_directly("doc", status=None),
            [
                'Test 4',
                'Test 3',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_directly(
                "doc", user2, status=None, local_site=None),
            [
                'Test 4',
                'Test 3',
                'Test 2',
            ])

    def test_from_user(self):
        """Testing ReviewRequest.objects.from_user"""
        user1 = User.objects.get(username='doc')

        self.create_review_request(summary='Test 1',
                                   public=True,
                                   submitter=user1)

        self.create_review_request(summary='Test 2',
                                   public=False,
                                   submitter=user1)

        self.create_review_request(summary='Test 3',
                                   public=True,
                                   status='S',
                                   submitter=user1)

        self.assertValidSummaries(
            ReviewRequest.objects.from_user("doc", local_site=None),
            [
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.from_user("doc", status=None,
                                            local_site=None),
            [
                'Test 3',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.from_user(
                "doc", user=user1, status=None, local_site=None),
            [
                'Test 3',
                'Test 2',
                'Test 1',
            ])

    def to_user(self):
        """Testing ReviewRequest.objects.to_user"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        group1 = self.create_review_group(name='group1')
        group1.users.add(user1)

        group2 = self.create_review_group(name='group2')
        group2.users.add(user2)

        review_request = self.create_review_request(summary='Test 1',
                                                    publish=True,
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 2',
                                                    submitter=user2,
                                                    status='S')
        review_request.target_groups.add(group1)
        review_request.target_people.add(user2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 3',
                                                    publish=True,
                                                    submitter=user2)
        review_request.target_groups.add(group1)
        review_request.target_groups.add(group2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 4',
                                                    publish=True,
                                                    status='S',
                                                    submitter=user2)
        review_request.target_groups.add(group1)
        review_request.target_groups.add(group2)
        review_request.target_people.add(user1)

        self.assertValidSummaries(
            ReviewRequest.objects.to_user("doc", local_site=None),
            [
                'Test 3',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user("doc", status=None, local_site=None),
            [
                'Test 4',
                'Test 3',
                'Test 1',
            ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user(
                "doc", user=user2, status=None, local_site=None),
            [
                'Test 4',
                'Test 3',
                'Test 2',
                'Test 1',
            ])

    def assertValidSummaries(self, review_requests, summaries):
        r_summaries = [r.summary for r in review_requests]

        for summary in r_summaries:
            self.assertTrue(summary in summaries,
                            'summary "%s" not found in summary list'
                            % summary)

        for summary in summaries:
            self.assertTrue(summary in r_summaries,
                            'summary "%s" not found in review request list'
                            % summary)


class ReviewRequestTests(TestCase):
    """Tests for ReviewRequest."""
    fixtures = ['test_users']

    def test_public_with_discard_reopen_submitted(self):
        """Testing ReviewRequest.public when discarded, reopened, submitted."""
        review_request = self.create_review_request(publish=True)
        self.assertTrue(review_request.public)

        review_request.close(ReviewRequest.DISCARDED)
        self.assertTrue(review_request.public)

        review_request.reopen()
        self.assertFalse(review_request.public)

        review_request.close(ReviewRequest.SUBMITTED)
        self.assertTrue(review_request.public)

    def test_unicode_summary_and_str(self):
        """Testing ReviewRequest.__str__ with unicode summaries."""
        review_request = self.create_review_request(
            summary='\u203e\u203e', publish=True)
        self.assertEqual(six.text_type(review_request), '\u203e\u203e')


class ViewTests(TestCase):
    """Tests for views in reviewboard.reviews.views"""
    fixtures = ['test_users', 'test_scmtools', 'test_site']

    def setUp(self):
        super(ViewTests, self).setUp()

        self.siteconfig = SiteConfiguration.objects.get_current()
        self.siteconfig.set("auth_require_sitewide_login", False)
        self.siteconfig.save()

    def getContextVar(self, response, varname):
        for context in response.context:
            if varname in context:
                return context[varname]

        return None

    def testReviewDetail0(self):
        """Testing review_detail redirect"""
        response = self.client.get('/r/1')
        self.assertEqual(response.status_code, 301)

    def testReviewDetail1(self):
        """Testing review_detail view (1)"""
        review_request = self.create_review_request(publish=True)

        response = self.client.get('/r/%d/' % review_request.id)
        self.assertEqual(response.status_code, 200)

        request = self.getContextVar(response, 'review_request')
        self.assertEqual(request.pk, review_request.pk)

    def testReviewDetail2(self):
        """Testing review_detail view (3)"""
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

        request = self.getContextVar(response, 'review_request')
        self.assertEqual(request.submitter.username, username)
        self.assertEqual(request.summary, summary)
        self.assertEqual(request.description, description)
        self.assertEqual(request.testing_done, testing_done)
        self.assertEqual(request.pk, review_request.pk)

    def test_review_detail_diff_comment_ordering(self):
        """Testing order of diff comments on a review."""
        comment_text_1 = "Comment text 1"
        comment_text_2 = "Comment text 2"
        comment_text_3 = "Comment text 3"

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
        """Testing visibility of file attachments on review requests."""
        caption_1 = 'File Attachment 1'
        caption_2 = 'File Attachment 2'
        caption_3 = 'File Attachment 3'
        comment_text_1 = "Comment text 1"
        comment_text_2 = "Comment text 2"

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
        """Testing visibility of screenshots on review requests."""
        caption_1 = 'Screenshot 1'
        caption_2 = 'Screenshot 2'
        caption_3 = 'Screenshot 3'
        comment_text_1 = "Comment text 1"
        comment_text_2 = "Comment text 2"

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

    def testReviewDetailSitewideLogin(self):
        """Testing review_detail view with site-wide login enabled"""
        self.siteconfig.set("auth_require_sitewide_login", True)
        self.siteconfig.save()

        self.create_review_request(publish=True)

        response = self.client.get('/r/1/')
        self.assertEqual(response.status_code, 302)

    def testNewReviewRequest0(self):
        """Testing new_review_request view (basic responses)"""
        response = self.client.get('/r/new')
        self.assertEqual(response.status_code, 301)

        response = self.client.get('/r/new/')
        self.assertEqual(response.status_code, 302)

        self.client.login(username='grumpy', password='grumpy')

        response = self.client.get('/r/new/')
        self.assertEqual(response.status_code, 200)

    # Bug 892
    def testInterdiff(self):
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
            print("Error: %s" % self.getContextVar(response, 'error'))
            print(self.getContextVar(response, 'trace'))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.getContextVar(response, 'diff_context')['num_diffs'],
            2)

        files = self.getContextVar(response, 'files')
        self.assertTrue(files)
        self.assertEqual(len(files), 2)

        self.assertEqual(files[0]['depot_filename'], '/newfile')
        self.assertTrue('interfilediff' in files[0])

        self.assertEqual(files[1]['depot_filename'], '/readme')
        self.assertTrue('interfilediff' in files[1])

    # Bug 847
    def testInterdiffNewFile(self):
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
            print("Error: %s" % self.getContextVar(response, 'error'))
            print(self.getContextVar(response, 'trace'))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.getContextVar(response, 'diff_context')['num_diffs'],
            2)

        files = self.getContextVar(response, 'files')
        self.assertTrue(files)
        self.assertEqual(len(files), 1)

        self.assertEqual(files[0]['depot_filename'], '/newfile')
        self.assertTrue('interfilediff' in files[0])

    def test_review_request_etag_with_issues(self):
        """Testing review request ETags with issue status toggling"""
        self.client.login(username='doc', password='doc')

        # Some objects we need.
        user = User.objects.get(username="doc")

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

        response = self.client.get('/r/%d/diff/raw/' % review_request.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'],
                         'attachment; filename=diffset')

class DraftTests(TestCase):
    fixtures = ['test_users', 'test_scmtools']

    def testDraftChanges(self):
        """Testing recording of draft changes."""
        draft = self.getDraft()
        review_request = draft.review_request

        old_summary = review_request.summary
        old_description = review_request.description
        old_testing_done = review_request.testing_done
        old_branch = review_request.branch
        old_bugs = review_request.get_bug_list()

        draft.summary = "New summary"
        draft.description = "New description"
        draft.testing_done = "New testing done"
        draft.branch = "New branch"
        draft.bugs_closed = "12, 34, 56"

        new_bugs = draft.get_bug_list()

        changes = draft.publish()
        fields = changes.fields_changed

        self.assertTrue("summary" in fields)
        self.assertTrue("description" in fields)
        self.assertTrue("testing_done" in fields)
        self.assertTrue("branch" in fields)
        self.assertTrue("bugs_closed" in fields)

        old_bugs_norm = set([(bug,) for bug in old_bugs])
        new_bugs_norm = set([(bug,) for bug in new_bugs])

        self.assertEqual(fields["summary"]["old"][0], old_summary)
        self.assertEqual(fields["summary"]["new"][0], draft.summary)
        self.assertEqual(fields["description"]["old"][0], old_description)
        self.assertEqual(fields["description"]["new"][0], draft.description)
        self.assertEqual(fields["testing_done"]["old"][0], old_testing_done)
        self.assertEqual(fields["testing_done"]["new"][0], draft.testing_done)
        self.assertEqual(fields["branch"]["old"][0], old_branch)
        self.assertEqual(fields["branch"]["new"][0], draft.branch)
        self.assertEqual(set(fields["bugs_closed"]["old"]), old_bugs_norm)
        self.assertEqual(set(fields["bugs_closed"]["new"]), new_bugs_norm)
        self.assertEqual(set(fields["bugs_closed"]["removed"]), old_bugs_norm)
        self.assertEqual(set(fields["bugs_closed"]["added"]), new_bugs_norm)

    def getDraft(self):
        """Convenience function for getting a new draft to work with."""
        review_request = self.create_review_request(publish=True)
        return ReviewRequestDraft.create(review_request)


class FieldTests(TestCase):
    # Bug #1352
    def test_long_bug_numbers(self):
        """Testing review requests with very long bug numbers"""
        review_request = ReviewRequest()
        review_request.bugs_closed = \
            '12006153200030304432010,4432009'
        self.assertEqual(review_request.get_bug_list(),
                         ['4432009', '12006153200030304432010'])

    # Our _("(no summary)") string was failing in the admin UI, as
    # django.template.defaultfilters.stringfilter would fail on a
    # ugettext_lazy proxy object. We can use any stringfilter for this.
    #
    # Bug #1346
    def test_no_summary(self):
        """Testing review requests with no summary"""
        from django.template.defaultfilters import lower
        review_request = ReviewRequest()
        lower(review_request)

    @add_fixtures(['test_users'])
    def test_commit_id(self):
        """Testing commit_id migration"""
        review_request = self.create_review_request()
        review_request.changenum = '123'

        self.assertEqual(review_request.commit_id, None)
        self.assertEqual(review_request.commit,
                         six.text_type(review_request.changenum))
        self.assertNotEqual(review_request.commit_id, None)


class PostCommitTests(SpyAgency, TestCase):
    fixtures = ['test_users', 'test_scmtools']

    def setUp(self):
        super(PostCommitTests, self).setUp()

        self.user = User.objects.create(username='testuser', password='')
        self.profile, is_new = Profile.objects.get_or_create(user=self.user)
        self.profile.save()

        self.testdata_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'scmtools', 'testdata')

        self.repository = self.create_repository(tool_name='Test')

    def test_update_from_committed_change(self):
        """Testing post-commit update"""
        commit_id = '4'

        def get_change(repository, commit_to_get):
            self.assertEqual(commit_id, commit_to_get)

            commit = Commit()
            commit.message = \
                'This is my commit message\n\nWith a summary line too.'
            diff_filename = os.path.join(self.testdata_dir, 'git_readme.diff')
            with open(diff_filename, 'r') as f:
                commit.diff = f.read()

            return commit

        def get_file_exists(repository, path, revision, base_commit_id=None,
                            request=None):
            return (path, revision) in [('/readme', 'd6613f5')]

        self.spy_on(self.repository.get_change, call_fake=get_change)
        self.spy_on(self.repository.get_file_exists, call_fake=get_file_exists)

        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.update_from_commit_id(commit_id)

        self.assertEqual(review_request.summary, 'This is my commit message')
        self.assertEqual(review_request.description,
                         'With a summary line too.')

        self.assertEqual(review_request.diffset_history.diffsets.count(), 1)

        diffset = review_request.diffset_history.diffsets.get()
        self.assertEqual(diffset.files.count(), 1)

        fileDiff = diffset.files.get()
        self.assertEqual(fileDiff.source_file, 'readme')
        self.assertEqual(fileDiff.source_revision, 'd6613f5')

    def test_update_from_committed_change_with_markdown_escaping(self):
        """Testing post-commit update with markdown escaping"""
        def get_change(repository, commit_to_get):
            commit = Commit()
            commit.message = '* No escaping\n\n* but this needs escaping'
            diff_filename = os.path.join(self.testdata_dir, 'git_readme.diff')
            with open(diff_filename, 'r') as f:
                commit.diff = f.read()

            return commit

        def get_file_exists(repository, path, revision, base_commit_id=None,
                            request=None):
            return (path, revision) in [('/readme', 'd6613f5')]

        self.spy_on(self.repository.get_change, call_fake=get_change)
        self.spy_on(self.repository.get_file_exists, call_fake=get_file_exists)

        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.rich_text = True
        review_request.update_from_commit_id('4')

        self.assertEqual(review_request.summary, '* No escaping')
        self.assertEqual(review_request.description,
                         '\\* but this needs escaping')

    def test_update_from_committed_change_without_repository_support(self):
        """Testing post-commit update failure conditions"""
        self.spy_on(self.repository.__class__.supports_post_commit.fget,
                    call_fake=lambda self: False)
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)

        self.assertRaises(NotImplementedError,
                          lambda: review_request.update_from_commit_id('4'))


class ConcurrencyTests(TestCase):
    fixtures = ['test_users', 'test_scmtools']

    def testDuplicateReviews(self):
        """Testing consolidation of duplicate reviews"""

        body_top = "This is the body_top."
        body_bottom = "This is the body_bottom."
        comment_text_1 = "Comment text 1"
        comment_text_2 = "Comment text 2"
        comment_text_3 = "Comment text 3"

        # Some objects we need.
        user = User.objects.get(username="doc")

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        # Create the first review.
        master_review = self.create_review(review_request, user=user,
                                           body_top=body_top,
                                           body_bottom='')
        self.create_diff_comment(master_review, filediff, text=comment_text_1,
                                 first_line=1, num_lines=1)

        # Create the second review.
        review = self.create_review(review_request, user=user,
                                    body_top='', body_bottom='')
        self.create_diff_comment(review, filediff, text=comment_text_2,
                                 first_line=1, num_lines=1)

        # Create the third review.
        review = self.create_review(review_request, user=user,
                                    body_top='',
                                    body_bottom=body_bottom)
        self.create_diff_comment(review, filediff, text=comment_text_3,
                                 first_line=1, num_lines=1)

        # Now that we've made a mess, see if we get a single review back.
        logging.disable(logging.WARNING)
        review = review_request.get_pending_review(user)
        self.assertTrue(review)
        self.assertEqual(review.id, master_review.id)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)

        comments = list(review.comments.all())
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_2)
        self.assertEqual(comments[2].text, comment_text_3)


class DefaultReviewerTests(TestCase):
    fixtures = ['test_scmtools']

    def test_for_repository(self):
        """Testing DefaultReviewer.objects.for_repository"""
        tool = Tool.objects.get(name='CVS')

        default_reviewer1 = DefaultReviewer(name="Test", file_regex=".*")
        default_reviewer1.save()

        default_reviewer2 = DefaultReviewer(name="Bar", file_regex=".*")
        default_reviewer2.save()

        repo1 = Repository(name='Test1', path='path1', tool=tool)
        repo1.save()
        default_reviewer1.repository.add(repo1)

        repo2 = Repository(name='Test2', path='path2', tool=tool)
        repo2.save()

        default_reviewers = DefaultReviewer.objects.for_repository(repo1, None)
        self.assertEqual(len(default_reviewers), 2)
        self.assertTrue(default_reviewer1 in default_reviewers)
        self.assertTrue(default_reviewer2 in default_reviewers)

        default_reviewers = DefaultReviewer.objects.for_repository(repo2, None)
        self.assertEqual(len(default_reviewers), 1)
        self.assertTrue(default_reviewer2 in default_reviewers)

    def test_for_repository_with_localsite(self):
        """Testing DefaultReviewer.objects.for_repository with a LocalSite."""
        test_site = LocalSite.objects.create(name='test')

        default_reviewer1 = DefaultReviewer(name='Test 1', file_regex='.*',
                                            local_site=test_site)
        default_reviewer1.save()

        default_reviewer2 = DefaultReviewer(name='Test 2', file_regex='.*')
        default_reviewer2.save()

        default_reviewers = DefaultReviewer.objects.for_repository(
            None, test_site)
        self.assertEqual(len(default_reviewers), 1)
        self.assertTrue(default_reviewer1 in default_reviewers)

        default_reviewers = DefaultReviewer.objects.for_repository(None, None)
        self.assertEqual(len(default_reviewers), 1)
        self.assertTrue(default_reviewer2 in default_reviewers)

    def test_form_with_localsite(self):
        """Testing DefaultReviewerForm with a LocalSite."""
        test_site = LocalSite.objects.create(name='test')

        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test', path='path', tool=tool,
                                         local_site=test_site)
        user = User.objects.create(username='testuser', password='')
        test_site.users.add(user)

        group = Group.objects.create(name='test', display_name='Test',
                                     local_site=test_site)

        form = DefaultReviewerForm({
            'name': 'Test',
            'file_regex': '.*',
            'local_site': test_site.pk,
            'repository': [repo.pk],
            'people': [user.pk],
            'groups': [group.pk],
        })
        self.assertTrue(form.is_valid())
        default_reviewer = form.save()

        self.assertEquals(default_reviewer.local_site, test_site)
        self.assertEquals(default_reviewer.repository.get(), repo)
        self.assertEquals(default_reviewer.people.get(), user)
        self.assertEquals(default_reviewer.groups.get(), group)

    def test_form_with_localsite_and_bad_user(self):
        """Testing DefaultReviewerForm with a User not on the same LocalSite.
        """
        test_site = LocalSite.objects.create(name='test')
        user = User.objects.create(username='testuser', password='')

        form = DefaultReviewerForm({
            'name': 'Test',
            'file_regex': '.*',
            'local_site': test_site.pk,
            'people': [user.pk],
        })
        self.assertFalse(form.is_valid())

    def test_form_with_localsite_and_bad_group(self):
        """Testing DefaultReviewerForm with a Group not on the same LocalSite.
        """
        test_site = LocalSite.objects.create(name='test')
        group = Group.objects.create(name='test', display_name='Test')

        form = DefaultReviewerForm({
            'name': 'Test',
            'file_regex': '.*',
            'local_site': test_site.pk,
            'groups': [group.pk],
        })
        self.assertFalse(form.is_valid())

        group.local_site = test_site
        group.save()

        form = DefaultReviewerForm({
            'name': 'Test',
            'file_regex': '.*',
            'groups': [group.pk],
        })
        self.assertFalse(form.is_valid())

    def test_form_with_localsite_and_bad_repository(self):
        """Testing DefaultReviewerForm with a Repository not on the same
        LocalSite.
        """
        test_site = LocalSite.objects.create(name='test')
        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test', path='path', tool=tool)

        form = DefaultReviewerForm({
            'name': 'Test',
            'file_regex': '.*',
            'local_site': test_site.pk,
            'repository': [repo.pk],
        })
        self.assertFalse(form.is_valid())

        repo.local_site = test_site
        repo.save()

        form = DefaultReviewerForm({
            'name': 'Test',
            'file_regex': '.*',
            'repository': [repo.pk],
        })
        self.assertFalse(form.is_valid())


class GroupTests(TestCase):
    def test_form_with_localsite(self):
        """Tests GroupForm with a LocalSite."""
        test_site = LocalSite.objects.create(name='test')

        user = User.objects.create(username='testuser', password='')
        test_site.users.add(user)

        form = GroupForm({
            'name': 'test',
            'display_name': 'Test',
            'local_site': test_site.pk,
            'users': [user.pk],
        })
        self.assertTrue(form.is_valid())
        group = form.save()

        self.assertEquals(group.local_site, test_site)
        self.assertEquals(group.users.get(), user)

    def test_form_with_localsite_and_bad_user(self):
        """Tests GroupForm with a User not on the same LocalSite."""
        test_site = LocalSite.objects.create(name='test')

        user = User.objects.create(username='testuser', password='')

        form = GroupForm({
            'name': 'test',
            'display_name': 'Test',
            'local_site': test_site.pk,
            'users': [user.pk],
        })
        self.assertFalse(form.is_valid())


class IfNeatNumberTagTests(TestCase):
    def testMilestones(self):
        """Testing the ifneatnumber tag with milestone numbers"""
        self.assertNeatNumberResult(100, "")
        self.assertNeatNumberResult(1000, "milestone")
        self.assertNeatNumberResult(10000, "milestone")
        self.assertNeatNumberResult(20000, "milestone")
        self.assertNeatNumberResult(20001, "")

    def testPalindrome(self):
        """Testing the ifneatnumber tag with palindrome numbers"""
        self.assertNeatNumberResult(101, "")
        self.assertNeatNumberResult(1001, "palindrome")
        self.assertNeatNumberResult(12321, "palindrome")
        self.assertNeatNumberResult(20902, "palindrome")
        self.assertNeatNumberResult(912219, "palindrome")
        self.assertNeatNumberResult(912218, "")

    def assertNeatNumberResult(self, rid, expected):
        t = Template(
            "{% load reviewtags %}"
            "{% ifneatnumber " + six.text_type(rid) + " %}"
            "{%  if milestone %}milestone{% else %}"
            "{%  if palindrome %}palindrome{% endif %}{% endif %}"
            "{% endifneatnumber %}")

        self.assertEqual(t.render(Context({})), expected)


class ReviewRequestCounterTests(TestCase):
    fixtures = ['test_scmtools']

    def setUp(self):
        super(ReviewRequestCounterTests, self).setUp()

        tool = Tool.objects.get(name='Subversion')
        repository = Repository.objects.create(name='Test1', path='path1',
                                               tool=tool)

        self.user = User.objects.create(username='testuser', password='')
        self.profile, is_new = Profile.objects.get_or_create(user=self.user)
        self.profile.save()

        self.test_site = LocalSite.objects.create(name='test')
        self.site_profile2 = \
            LocalSiteProfile.objects.create(user=self.user,
                                            profile=self.profile,
                                            local_site=self.test_site)

        self.review_request = ReviewRequest.objects.create(self.user,
                                                           repository)
        self.profile.star_review_request(self.review_request)

        self.site_profile = self.profile.site_profiles.get(local_site=None)
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)

        self.group = Group.objects.create(name='test-group')
        self.group.users.add(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

    def test_new_site_profile(self):
        """Testing counters on a new LocalSiteProfile"""
        self.site_profile.delete()
        self.site_profile = \
            LocalSiteProfile.objects.create(user=self.user,
                                            profile=self.profile)
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)

    def test_outgoing_requests(self):
        """Testing counters with creating outgoing review requests"""
        # The review request was already created
        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)

        ReviewRequestDraft.create(self.review_request)
        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)

    def test_closing_requests(self, close_type=ReviewRequest.DISCARDED):
        """Testing counters with closing outgoing review requests"""
        # The review request was already created
        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)
        draft.target_people.add(self.user)
        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

        self.assertTrue(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)
        self.review_request.close(close_type)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_closing_draft_requests(self, close_type=ReviewRequest.DISCARDED):
        """Testing counters with closing draft review requests"""
        # The review request was already created
        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

        self.assertFalse(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)
        self.review_request.close(close_type)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_closing_draft_requests_with_site(self):
        """Testing counters with closing draft review requests"""
        self.review_request.delete()
        self._reload_objects()
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

        tool = Tool.objects.get(name='Subversion')
        repository = Repository.objects.create(name='Test1', path='path1',
                                               tool=tool,
                                               local_site=self.test_site)
        self.review_request = ReviewRequest.objects.create(
            self.user,
            repository,
            local_site=self.test_site)

        self._reload_objects()
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

        self.assertFalse(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)
        self.review_request.close(ReviewRequest.DISCARDED)

        self._reload_objects()
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)

    def test_deleting_requests(self):
        """Testing counters with deleting outgoing review requests"""
        # The review request was already created
        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)
        draft.target_people.add(self.user)
        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

        self.review_request.delete()

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_deleting_draft_requests(self):
        """Testing counters with deleting draft review requests"""
        # The review request was already created
        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

        self.review_request.delete()

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_reopen_discarded_requests(self):
        """Testing counters with reopening discarded outgoing review requests
        """
        self.test_closing_requests(ReviewRequest.DISCARDED)

        self.review_request.reopen()
        self.assertFalse(self.review_request.public)
        self.assertTrue(self.review_request.status,
                        ReviewRequest.PENDING_REVIEW)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

    def test_reopen_submitted_requests(self):
        """Testing counters with reopening submitted outgoing review requests
        """
        self.test_closing_requests(ReviewRequest.SUBMITTED)

        self.review_request.reopen()
        self.assertTrue(self.review_request.public)
        self.assertTrue(self.review_request.status,
                        ReviewRequest.PENDING_REVIEW)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

    def test_reopen_discarded_draft_requests(self):
        """Testing counters with reopening discarded draft review requests"""
        self.assertFalse(self.review_request.public)

        self.test_closing_draft_requests(ReviewRequest.DISCARDED)

        self.review_request.reopen()
        self.assertFalse(self.review_request.public)
        self.assertTrue(self.review_request.status,
                        ReviewRequest.PENDING_REVIEW)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_reopen_submitted_draft_requests(self):
        """Testing counters with reopening submitted draft review requests"""
        self.test_closing_draft_requests(ReviewRequest.SUBMITTED)

        self.review_request.reopen()
        self.assertTrue(self.review_request.public)
        self.assertTrue(self.review_request.status,
                        ReviewRequest.PENDING_REVIEW)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_add_group(self):
        """Testing counters when adding a group reviewer"""
        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)

        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

    def test_remove_group(self):
        """Testing counters when removing a group reviewer"""
        self.test_add_group()

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.remove(self.group)

        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_add_person(self):
        """Testing counters when adding a person reviewer"""
        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_people.add(self.user)

        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)

    def test_remove_person(self):
        """Testing counters when removing a person reviewer"""
        self.test_add_person()

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_people.remove(self.user)

        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)

    def test_populate_counters(self):
        """Testing counters when populated from a fresh upgrade or clear"""
        # The review request was already created
        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)
        draft.target_people.add(self.user)
        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

        LocalSiteProfile.objects.update(
            direct_incoming_request_count=None,
            total_incoming_request_count=None,
            pending_outgoing_request_count=None,
            total_outgoing_request_count=None,
            starred_public_request_count=None)
        Group.objects.update(incoming_request_count=None)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

    def test_populate_counters_after_change(self):
        """Testing counter inc/dec on uninitialized counter fields"""
        # The review request was already created
        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)
        draft.target_people.add(self.user)

        LocalSiteProfile.objects.update(
            direct_incoming_request_count=None,
            total_incoming_request_count=None,
            pending_outgoing_request_count=None,
            total_outgoing_request_count=None,
            starred_public_request_count=None)
        Group.objects.update(incoming_request_count=None)

        profile_fields = [
            'direct_incoming_request_count',
            'total_incoming_request_count',
            'pending_outgoing_request_count',
            'total_outgoing_request_count',
            'starred_public_request_count',
        ]

        # Lock the fields so we don't re-initialize them on publish.
        locks = {
            self.site_profile: 1,
            self.site_profile2: 1,
        }

        for field in profile_fields:
            getattr(LocalSiteProfile, field)._locks = locks

        Group.incoming_request_count._locks = locks

        # Publish the review request. This will normally try to
        # increment/decrement the counts, which it should ignore now.
        self.review_request.publish(self.user)

        # Unlock the profiles so we can query/re-initialize them again.
        for field in profile_fields:
            getattr(LocalSiteProfile, field)._locks = {}

        Group.incoming_request_count._locks = {}

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

    def _reload_objects(self):
        self.test_site = LocalSite.objects.get(pk=self.test_site.pk)
        self.site_profile = \
            LocalSiteProfile.objects.get(pk=self.site_profile.pk)
        self.site_profile2 = \
            LocalSiteProfile.objects.get(pk=self.site_profile2.pk)
        self.group = Group.objects.get(pk=self.group.pk)


class IssueCounterTests(TestCase):
    fixtures = ['test_users']

    def setUp(self):
        super(IssueCounterTests, self).setUp()

        self.review_request = self.create_review_request(publish=True)
        self.assertEqual(self.review_request.issue_open_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

        self._reset_counts()

    @add_fixtures(['test_scmtools'])
    def test_init_with_diff_comments(self):
        """Testing ReviewRequest issue counter initialization
        from diff comments
        """
        self.review_request.repository = self.create_repository()

        diffset = self.create_diffset(self.review_request)
        filediff = self.create_filediff(diffset)

        self._test_issue_counts(
            lambda review, issue_opened: self.create_diff_comment(
                review, filediff, issue_opened=issue_opened))

    def test_init_with_file_attachment_comments(self):
        """Testing ReviewRequest issue counter initialization
        from file attachment comments
        """
        file_attachment = self.create_file_attachment(self.review_request)

        self._test_issue_counts(
            lambda review, issue_opened: self.create_file_attachment_comment(
                review, file_attachment, issue_opened=issue_opened))

    def test_init_with_screenshot_comments(self):
        """Testing ReviewRequest issue counter initialization
        from screenshot comments
        """
        screenshot = self.create_screenshot(self.review_request)

        self._test_issue_counts(
            lambda review, issue_opened: self.create_screenshot_comment(
                review, screenshot, issue_opened=issue_opened))

    @add_fixtures(['test_scmtools'])
    def test_init_with_mix(self):
        """Testing ReviewRequest issue counter initialization
        from multiple types of comments at once
        """
        # The initial implementation for issue status counting broke when
        # there were multiple types of comments on a review (such as diff
        # comments and file attachment comments). There would be an
        # artificially large number of issues reported.
        #
        # That's been fixed, and this test is ensuring that it doesn't
        # regress.
        self.review_request.repository = self.create_repository()
        diffset = self.create_diffset(self.review_request)
        filediff = self.create_filediff(diffset)
        file_attachment = self.create_file_attachment(self.review_request)
        screenshot = self.create_screenshot(self.review_request)

        review = self.create_review(self.review_request)

        # One open file attachment comment
        self.create_file_attachment_comment(review, file_attachment,
                                            issue_opened=True)

        # Two diff comments
        self.create_diff_comment(review, filediff, issue_opened=True)
        self.create_diff_comment(review, filediff, issue_opened=True)

        # Four screenshot comments
        self.create_screenshot_comment(review, screenshot, issue_opened=True)
        self.create_screenshot_comment(review, screenshot, issue_opened=True)
        self.create_screenshot_comment(review, screenshot, issue_opened=True)
        self.create_screenshot_comment(review, screenshot, issue_opened=True)

        # The issue counts should be end up being 0, since they'll initialize
        # during load.
        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

        # Now publish. We should have 7 open issues, by way of incrementing
        # during publish.
        review.publish()

        self._reload_object()
        self.assertEqual(self.review_request.issue_open_count, 7)
        self.assertEqual(self.review_request.issue_dropped_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)

        # Make sure we get the same number back when initializing counters.
        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 7)
        self.assertEqual(self.review_request.issue_dropped_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)

    def test_init_with_replies(self):
        """Testing ReviewRequest issue counter initialization and replies."""
        file_attachment = self.create_file_attachment(self.review_request)

        review = self.create_review(self.review_request)
        comment = self.create_file_attachment_comment(review, file_attachment,
                                                      issue_opened=True)
        review.publish()

        reply = self.create_reply(review)
        self.create_file_attachment_comment(reply, file_attachment,
                                            reply_to=comment,
                                            issue_opened=True)
        reply.publish()

        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 1)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

    def test_save_reply_comment(self):
        """Testing ReviewRequest issue counter and saving reply comments."""
        file_attachment = self.create_file_attachment(self.review_request)

        review = self.create_review(self.review_request)
        comment = self.create_file_attachment_comment(review, file_attachment,
                                                      issue_opened=True)
        review.publish()

        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 1)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

        reply = self.create_reply(review)
        reply_comment = self.create_file_attachment_comment(
            reply, file_attachment,
            reply_to=comment,
            issue_opened=True)
        reply.publish()

        self._reload_object()
        self.assertEqual(self.review_request.issue_open_count, 1)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

        reply_comment.save()
        self._reload_object()
        self.assertEqual(self.review_request.issue_open_count, 1)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

    def _test_issue_counts(self, create_comment_func):
        review = self.create_review(self.review_request)

        # One comment without an issue opened.
        create_comment_func(review, issue_opened=False)

        # Three comments with an issue opened.
        for i in range(3):
            create_comment_func(review, issue_opened=True)

        # Two comments that will have their issues dropped.
        dropped_comments = [
            create_comment_func(review, issue_opened=True)
            for i in range(2)
        ]

        # One comment that will have its issue resolved.
        resolved_comments = [
            create_comment_func(review, issue_opened=True)
        ]

        # The issue counts should be end up being 0, since they'll initialize
        # during load.
        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

        # Now publish. We should have 6 open issues, by way of incrementing
        # during publish.
        review.publish()

        self._reload_object()
        self.assertEqual(self.review_request.issue_open_count, 6)
        self.assertEqual(self.review_request.issue_dropped_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)

        # Make sure we get the same number back when initializing counters.
        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 6)
        self.assertEqual(self.review_request.issue_dropped_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)

        # Set the issue statuses.
        for comment in dropped_comments:
            comment.issue_status = Comment.DROPPED
            comment.save()

        for comment in resolved_comments:
            comment.issue_status = Comment.RESOLVED
            comment.save()

        self._reload_object()
        self.assertEqual(self.review_request.issue_open_count, 3)
        self.assertEqual(self.review_request.issue_dropped_count, 2)
        self.assertEqual(self.review_request.issue_resolved_count, 1)

        # Make sure we get the same number back when initializing counters.
        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 3)
        self.assertEqual(self.review_request.issue_dropped_count, 2)
        self.assertEqual(self.review_request.issue_resolved_count, 1)

    def _reload_object(self, clear_counters=False):
        if clear_counters:
            # 3 queries: One for the review request fetch, one for
            # the issue status load, and one for updating the issue counts.
            expected_query_count = 3
            self._reset_counts()
        else:
            # One query for the review request fetch.
            expected_query_count = 1

        with self.assertNumQueries(expected_query_count):
            self.review_request = \
                ReviewRequest.objects.get(pk=self.review_request.pk)

    def _reset_counts(self):
        self.review_request.issue_open_count = None
        self.review_request.issue_resolved_count = None
        self.review_request.issue_dropped_count = None
        self.review_request.save()


class PolicyTests(TestCase):
    fixtures = ['test_users']

    def setUp(self):
        super(PolicyTests, self).setUp()

        self.user = User.objects.create(username='testuser', password='')
        self.anonymous = AnonymousUser()

    def test_group_public(self):
        """Testing access to a public review group"""
        group = Group.objects.create(name='test-group')

        self.assertFalse(group.invite_only)
        self.assertTrue(group.is_accessible_by(self.user))
        self.assertTrue(group.is_accessible_by(self.anonymous))

        self.assertTrue(group in Group.objects.accessible(self.user))
        self.assertTrue(group in Group.objects.accessible(self.anonymous))

    def test_group_invite_only_access_denied(self):
        """Testing no access to unjoined invite-only group"""
        group = Group.objects.create(name='test-group', invite_only=True)

        self.assertTrue(group.invite_only)
        self.assertFalse(group.is_accessible_by(self.user))
        self.assertFalse(group.is_accessible_by(self.anonymous))

        self.assertFalse(group in Group.objects.accessible(self.user))
        self.assertFalse(group in Group.objects.accessible(self.anonymous))

    def test_group_invite_only_access_allowed(self):
        """Testing access to joined invite-only group"""
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        self.assertTrue(group.invite_only)
        self.assertTrue(group.is_accessible_by(self.user))
        self.assertFalse(group.is_accessible_by(self.anonymous))

        self.assertTrue(group in Group.objects.accessible(self.user))
        self.assertFalse(group in Group.objects.accessible(self.anonymous))

    def test_group_public_hidden(self):
        """Testing visibility of a hidden public group"""
        group = Group.objects.create(name='test-group', visible=False)

        self.assertFalse(group.visible)
        self.assertTrue(group.is_accessible_by(self.user))
        self.assertTrue(
            group in Group.objects.accessible(self.user, visible_only=False))
        self.assertFalse(
            group in Group.objects.accessible(self.user, visible_only=True))

    def test_group_invite_only_hidden_access_denied(self):
        """Testing visibility of a hidden unjoined invite-only group"""
        group = Group.objects.create(name='test-group', visible=False,
                                     invite_only=True)

        self.assertFalse(group.visible)
        self.assertTrue(group.invite_only)
        self.assertFalse(group.is_accessible_by(self.user))
        self.assertFalse(
            group in Group.objects.accessible(self.user, visible_only=False))
        self.assertFalse(
            group in Group.objects.accessible(self.user, visible_only=True))

    def test_group_invite_only_hidden_access_allowed(self):
        """Testing visibility of a hidden joined invite-only group"""
        group = Group.objects.create(name='test-group', visible=False,
                                     invite_only=True)
        group.users.add(self.user)

        self.assertFalse(group.visible)
        self.assertTrue(group.invite_only)
        self.assertTrue(group.is_accessible_by(self.user))
        self.assertTrue(
            group in Group.objects.accessible(self.user, visible_only=False))
        self.assertTrue(
            group in Group.objects.accessible(self.user, visible_only=True))

    def test_group_invite_only_review_request_ownership(self):
        """Testing visibility of review requests assigned to invite-only
        groups by a non-member
        """
        group = Group.objects.create(name='test-group', visible=False,
                                     invite_only=True)

        review_request = self.create_review_request(publish=True,
                                                    submitter=self.user)
        review_request.target_groups.add(group)

        self.assertTrue(review_request.is_accessible_by(self.user))

    @add_fixtures(['test_scmtools'])
    def test_repository_public(self):
        """Testing access to a public repository"""
        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test1', path='path1', tool=tool)

        self.assertTrue(repo.public)
        self.assertTrue(repo.is_accessible_by(self.user))
        self.assertTrue(repo.is_accessible_by(self.anonymous))

    @add_fixtures(['test_scmtools'])
    def test_repository_private_access_denied(self):
        """Testing no access to a private repository"""
        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test1', path='path1', tool=tool,
                                         public=False)

        self.assertFalse(repo.public)
        self.assertFalse(repo.is_accessible_by(self.user))
        self.assertFalse(repo.is_accessible_by(self.anonymous))

    @add_fixtures(['test_scmtools'])
    def test_repository_private_access_allowed_by_user(self):
        """Testing access to a private repository with user added"""
        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test1', path='path1', tool=tool,
                                         public=False)
        repo.users.add(self.user)

        self.assertFalse(repo.public)
        self.assertTrue(repo.is_accessible_by(self.user))
        self.assertFalse(repo.is_accessible_by(self.anonymous))

    @add_fixtures(['test_scmtools'])
    def test_repository_private_access_allowed_by_review_group(self):
        """Testing access to a private repository with joined review group
        added
        """
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test1', path='path1', tool=tool,
                                         public=False)
        repo.review_groups.add(group)

        self.assertFalse(repo.public)
        self.assertTrue(repo.is_accessible_by(self.user))
        self.assertFalse(repo.is_accessible_by(self.anonymous))

    def test_review_request_public(self):
        """Testing access to a public review request"""
        review_request = self.create_review_request(publish=True)

        self.assertTrue(review_request.is_accessible_by(self.user))
        self.assertTrue(review_request.is_accessible_by(self.anonymous))

    def test_review_request_with_invite_only_group(self):
        """Testing no access to a review request with only an unjoined
        invite-only group
        """
        group = Group(name='test-group', invite_only=True)
        group.save()

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        self.assertFalse(review_request.is_accessible_by(self.user))
        self.assertFalse(review_request.is_accessible_by(self.anonymous))

    def test_review_request_with_invite_only_group_and_target_user(self):
        """Testing access to a review request with specific target user and
        invite-only group
        """
        group = Group(name='test-group', invite_only=True)
        group.save()

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)
        review_request.target_people.add(self.user)

        self.assertTrue(review_request.is_accessible_by(self.user))
        self.assertFalse(review_request.is_accessible_by(self.anonymous))

    @add_fixtures(['test_scmtools'])
    def test_review_request_with_private_repository(self):
        """Testing no access to a review request with a private repository"""
        Group.objects.create(name='test-group', invite_only=True)

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review_request.repository.public = False
        review_request.repository.save()

        self.assertFalse(review_request.is_accessible_by(self.user))
        self.assertFalse(review_request.is_accessible_by(self.anonymous))

    @add_fixtures(['test_scmtools'])
    def test_review_request_with_private_repository_allowed_by_user(self):
        """Testing access to a review request with a private repository with
        user added
        """
        Group.objects.create(name='test-group', invite_only=True)

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review_request.repository.public = False
        review_request.repository.users.add(self.user)
        review_request.repository.save()

        self.assertTrue(review_request.is_accessible_by(self.user))
        self.assertFalse(review_request.is_accessible_by(self.anonymous))

    @add_fixtures(['test_scmtools'])
    def test_review_request_with_private_repository_allowed_by_review_group(self):
        """Testing access to a review request with a private repository with
        review group added
        """
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review_request.repository.public = False
        review_request.repository.review_groups.add(group)
        review_request.repository.save()

        self.assertTrue(review_request.is_accessible_by(self.user))
        self.assertFalse(review_request.is_accessible_by(self.anonymous))


class UserInfoboxTests(TestCase):
    def testUnicode(self):
        """Testing user_infobox with a user with non-ascii characters"""
        user = User.objects.create_user('test', 'test@example.com')
        user.first_name = 'Test\u21b9'
        user.last_name = 'User\u2729'
        user.save()

        self.client.get(local_site_reverse('user-infobox', args=['test']))


class MarkdownUtilsTests(TestCase):
    UNESCAPED_TEXT = r'\`*_{}[]()>#+-.!'
    ESCAPED_TEXT = r'\\\`\*\_\{\}\[\]\(\)\>#+-.\!'

    def test_markdown_escape(self):
        """Testing markdown_escape"""
        self.assertEqual(markdown_escape(self.UNESCAPED_TEXT),
                         self.ESCAPED_TEXT)

    def test_markdown_escape_periods(self):
        """Testing markdown_escape with '.' placement"""
        self.assertEqual(
            markdown_escape('Line. 1.\n'
                            '1. Line. 2.\n'
                            '1.2. Line. 3.\n'
                            '  1. Line. 4.'),
            ('Line. 1.\n'
             '1\\. Line. 2.\n'
             '1\\.2\\. Line. 3.\n'
             '  1\\. Line. 4.'))

    def test_markdown_escape_atx_headers(self):
        """Testing markdown_escape with '#' placement"""
        self.assertEqual(
            markdown_escape('### Header\n'
                            '  ## Header ##\n'
                            'Not # a header'),
            ('\\#\\#\\# Header\n'
             '  \\#\\# Header ##\n'
             'Not # a header'))

    def test_markdown_escape_hyphens(self):
        """Testing markdown_escape with '-' placement"""
        self.assertEqual(
            markdown_escape('Header\n'
                            '------\n'
                            '\n'
                            '- List item\n'
                            '  - List item\n'
                            'Just hyp-henated'),
            ('Header\n'
             '\\-\\-\\-\\-\\-\\-\n'
             '\n'
             '\\- List item\n'
             '  \\- List item\n'
             'Just hyp-henated'))

    def test_markdown_escape_plusses(self):
        """Testing markdown_escape with '+' placement"""
        self.assertEqual(
            markdown_escape('+ List item\n'
                            'a + b'),
            ('\\+ List item\n'
             'a + b'))

    def test_markdown_escape_underscores(self):
        """Testing markdown_escape with '_' placement"""
        self.assertEqual(markdown_escape('_foo_'), r'\_foo\_')
        self.assertEqual(markdown_escape('__foo__'), r'\_\_foo\_\_')
        self.assertEqual(markdown_escape(' _foo_ '), r' \_foo\_ ')
        self.assertEqual(markdown_escape('f_o_o'), r'f\_o\_o')
        self.assertEqual(markdown_escape('f_o_o_'), r'f\_o\_o\_')
        self.assertEqual(markdown_escape('foo_ _bar'), r'foo\_ \_bar')
        self.assertEqual(markdown_escape('foo__bar'), r'foo\_\_bar')
        self.assertEqual(markdown_escape('foo\n_bar'), 'foo\n\\_bar')
        self.assertEqual(markdown_escape('(_foo_)'), r'(\_foo\_)')

    def test_markdown_escape_asterisks(self):
        """Testing markdown_escape with '*' placement"""
        self.assertEqual(markdown_escape('*foo*'), r'\*foo\*')
        self.assertEqual(markdown_escape('**foo**'), r'\*\*foo\*\*')
        self.assertEqual(markdown_escape(' *foo* '), r' \*foo\* ')
        self.assertEqual(markdown_escape('f*o*o'), r'f*o*o')
        self.assertEqual(markdown_escape('f*o*o*'), r'f*o*o\*')
        self.assertEqual(markdown_escape('foo* *bar'), r'foo\* \*bar')
        self.assertEqual(markdown_escape('foo**bar'), r'foo**bar')
        self.assertEqual(markdown_escape('foo\n*bar'), 'foo\n\\*bar')

    def test_markdown_escape_parens(self):
        """Testing markdown_escape with '(' and ')' placement"""
        self.assertEqual(markdown_escape('[name](link)'), r'\[name\]\(link\)')
        self.assertEqual(markdown_escape('(link)'), r'(link)')
        self.assertEqual(markdown_escape('](link)'), r'\](link)')
        self.assertEqual(markdown_escape('[foo] ](link)'),
                         r'\[foo\] \](link)')

    def test_markdown_unescape(self):
        """Testing markdown_unescape"""
        self.assertEqual(markdown_unescape(self.ESCAPED_TEXT),
                         self.UNESCAPED_TEXT)
