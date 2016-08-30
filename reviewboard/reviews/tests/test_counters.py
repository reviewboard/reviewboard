from __future__ import unicode_literals

from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.accounts.models import Profile, LocalSiteProfile
from reviewboard.reviews.errors import NotModifiedError
from reviewboard.reviews.models import (Comment, Group, ReviewRequest,
                                        ReviewRequestDraft)
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class ReviewRequestCounterTests(SpyAgency, TestCase):
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
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1)

        ReviewRequestDraft.create(self.review_request)
        self.review_request.publish(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             starred_public=1)

    def test_closing_requests(self, close_type=ReviewRequest.DISCARDED):
        """Testing counters with closing outgoing review requests"""
        # The review request was already created
        self._check_counters(total_outgoing=1, pending_outgoing=1)

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)
        draft.target_people.add(self.user)
        self.review_request.publish(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             direct_incoming=1,
                             total_incoming=1,
                             starred_public=1,
                             group_incoming=1)

        self.assertTrue(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)

        self.review_request.close(close_type)
        self._check_counters(total_outgoing=1)

    def test_closing_draft_requests(self, close_type=ReviewRequest.DISCARDED):
        """Testing counters with closing draft review requests"""
        # The review request was already created
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1)

        self.assertFalse(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)

        self.review_request.close(close_type)
        self._check_counters(total_outgoing=1)

    def test_closing_closed_requests(self):
        """Testing counters with closing closed review requests"""
        # The review request was already created
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1)

        self.review_request.publish(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             starred_public=1)

        self.assertTrue(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)

        self.review_request.close(ReviewRequest.DISCARDED)
        self._check_counters(total_outgoing=1)

        self.review_request.close(ReviewRequest.SUBMITTED)
        self._check_counters(total_outgoing=1)

    def test_closing_draft_requests_with_site(self):
        """Testing counters with closing draft review requests on LocalSite"""
        self.review_request.delete()

        self._check_counters(with_local_site=True)

        tool = Tool.objects.get(name='Subversion')
        repository = Repository.objects.create(name='Test1', path='path1',
                                               tool=tool,
                                               local_site=self.test_site)
        self.review_request = ReviewRequest.objects.create(
            self.user,
            repository,
            local_site=self.test_site)

        self._check_counters(with_local_site=True,
                             total_outgoing=1,
                             pending_outgoing=1)

        self.assertFalse(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)

        self.review_request.close(ReviewRequest.DISCARDED)
        self._check_counters(with_local_site=True,
                             total_outgoing=1)

    def test_deleting_requests(self):
        """Testing counters with deleting outgoing review requests"""
        # The review request was already created
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1)

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)
        draft.target_people.add(self.user)

        self.review_request.publish(self.user)
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             direct_incoming=1,
                             total_incoming=1,
                             starred_public=1,
                             group_incoming=1)

        self.review_request.delete()
        self._check_counters()

    def test_deleting_draft_requests(self):
        """Testing counters with deleting draft review requests"""
        # We're simulating what a DefaultReviewer would do by populating
        # the ReviewRequest's target users and groups while not public and
        # without a draft.
        self.review_request.target_people.add(self.user)
        self.review_request.target_groups.add(self.group)

        # The review request was already created
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1)

        self.review_request.delete()
        self._check_counters()

    def test_deleting_closed_requests(self):
        """Testing counters with deleting closed review requests"""
        # We're simulating what a DefaultReviewer would do by populating
        # the ReviewRequest's target users and groups while not public and
        # without a draft.
        self.review_request.target_people.add(self.user)
        self.review_request.target_groups.add(self.group)

        # The review request was already created
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1)

        self.review_request.close(ReviewRequest.DISCARDED)
        self._check_counters(total_outgoing=1)

        self.review_request.delete()
        self._check_counters()

    def test_reopen_discarded_requests(self):
        """Testing counters with reopening discarded outgoing review requests
        """
        self.test_closing_requests(ReviewRequest.DISCARDED)

        self.review_request.reopen()
        self.assertFalse(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1)

        self.review_request.publish(self.user)
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             direct_incoming=1,
                             total_incoming=1,
                             starred_public=1,
                             group_incoming=1)

    def test_reopen_submitted_requests(self):
        """Testing counters with reopening submitted outgoing review requests
        """
        self.test_closing_requests(ReviewRequest.SUBMITTED)

        self.review_request.reopen()
        self.assertTrue(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             direct_incoming=1,
                             total_incoming=1,
                             starred_public=1,
                             group_incoming=1)

        self.review_request.publish(self.user)
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             direct_incoming=1,
                             total_incoming=1,
                             starred_public=1,
                             group_incoming=1)

    def test_reopen_discarded_draft_requests(self):
        """Testing counters with reopening discarded draft review requests"""
        self.assertFalse(self.review_request.public)

        self.test_closing_draft_requests(ReviewRequest.DISCARDED)

        self.review_request.reopen()
        self.assertFalse(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1)

    def test_reopen_submitted_draft_requests(self):
        """Testing counters with reopening submitted draft review requests"""
        self.test_closing_requests(ReviewRequest.SUBMITTED)

        # We're simulating what a DefaultReviewer would do by populating
        # the ReviewRequest's target users and groups while not public and
        # without a draft.
        self.review_request.target_people.add(self.user)
        self.review_request.target_groups.add(self.group)

        self._check_counters(total_outgoing=1)

        self.review_request.reopen()
        self.assertTrue(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             direct_incoming=1,
                             total_incoming=1,
                             starred_public=1,
                             group_incoming=1)

    def test_double_publish(self):
        """Testing counters with publishing a review request twice"""
        self.assertFalse(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)

        # Publish the first time.
        self.review_request.publish(self.user)
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             starred_public=1)

        # Publish the second time.
        self.review_request.publish(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             starred_public=1)

    def test_add_group(self):
        """Testing counters when adding a group reviewer"""
        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1)

        self.review_request.publish(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             total_incoming=1,
                             group_incoming=1,
                             starred_public=1)

    def test_remove_group(self):
        """Testing counters when removing a group reviewer"""
        self.test_add_group()

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.remove(self.group)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             total_incoming=1,
                             group_incoming=1,
                             starred_public=1)

        self.review_request.publish(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             starred_public=1)

    def test_remove_group_and_fail_publish(self):
        """Testing counters when removing a group reviewer and then
        failing to publish the draft
        """
        self.test_add_group()

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.remove(self.group)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             total_incoming=1,
                             group_incoming=1,
                             starred_public=1)

        self.spy_on(ReviewRequestDraft.publish,
                    call_fake=self._raise_publish_error)

        with self.assertRaises(NotModifiedError):
            self.review_request.publish(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             total_incoming=1,
                             group_incoming=1,
                             starred_public=1)

    def test_add_person(self):
        """Testing counters when adding a person reviewer"""
        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_people.add(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1)

        self.review_request.publish(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             direct_incoming=1,
                             total_incoming=1,
                             starred_public=1)

    def test_remove_person(self):
        """Testing counters when removing a person reviewer"""
        self.test_add_person()

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_people.remove(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             direct_incoming=1,
                             total_incoming=1,
                             starred_public=1)

        self.review_request.publish(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             starred_public=1)

    def test_remove_person_and_fail_publish(self):
        """Testing counters when removing a person reviewer and then
        failing to publish the draft
        """
        self.test_add_person()

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_people.remove(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             direct_incoming=1,
                             total_incoming=1,
                             starred_public=1)

        self.spy_on(ReviewRequestDraft.publish,
                    call_fake=self._raise_publish_error)

        with self.assertRaises(NotModifiedError):
            self.review_request.publish(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             direct_incoming=1,
                             total_incoming=1,
                             starred_public=1)

    def test_populate_counters(self):
        """Testing counters when populated from a fresh upgrade or clear"""
        # The review request was already created
        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)
        draft.target_people.add(self.user)
        self.review_request.publish(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             total_incoming=1,
                             direct_incoming=1,
                             starred_public=1,
                             group_incoming=1)

        LocalSiteProfile.objects.update(
            direct_incoming_request_count=None,
            total_incoming_request_count=None,
            pending_outgoing_request_count=None,
            total_outgoing_request_count=None,
            starred_public_request_count=None)
        Group.objects.update(incoming_request_count=None)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             total_incoming=1,
                             direct_incoming=1,
                             starred_public=1,
                             group_incoming=1)

    def test_populate_counters_after_change(self):
        """Testing counter inc/dec on uninitialized counter fields"""
        # The review request was already created
        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)
        draft.target_people.add(self.user)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1)

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

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             direct_incoming=1,
                             total_incoming=1,
                             starred_public=1,
                             group_incoming=1)

    def _check_counters(self, total_outgoing=0, pending_outgoing=0,
                        direct_incoming=0, total_incoming=0,
                        starred_public=0, group_incoming=0,
                        with_local_site=False):
        self._reload_objects()

        if with_local_site:
            main_site_profile = self.site_profile2
            unused_site_profile = self.site_profile
        else:
            main_site_profile = self.site_profile
            unused_site_profile = self.site_profile2

        self.assertEqual(main_site_profile.total_outgoing_request_count,
                         total_outgoing)
        self.assertEqual(main_site_profile.pending_outgoing_request_count,
                         pending_outgoing)
        self.assertEqual(main_site_profile.direct_incoming_request_count,
                         direct_incoming)
        self.assertEqual(main_site_profile.total_incoming_request_count,
                         total_incoming)
        self.assertEqual(main_site_profile.starred_public_request_count,
                         starred_public)
        self.assertEqual(self.group.incoming_request_count, group_incoming)

        # These should never be affected by the updates on the main
        # LocalSite we're working with, so they should always be 0.
        self.assertEqual(unused_site_profile.total_outgoing_request_count, 0)
        self.assertEqual(unused_site_profile.pending_outgoing_request_count, 0)
        self.assertEqual(unused_site_profile.direct_incoming_request_count, 0)
        self.assertEqual(unused_site_profile.total_incoming_request_count, 0)
        self.assertEqual(unused_site_profile.starred_public_request_count, 0)

    def _reload_objects(self):
        self.test_site = LocalSite.objects.get(pk=self.test_site.pk)
        self.site_profile = \
            LocalSiteProfile.objects.get(pk=self.site_profile.pk)
        self.site_profile2 = \
            LocalSiteProfile.objects.get(pk=self.site_profile2.pk)
        self.group = Group.objects.get(pk=self.group.pk)

    def _raise_publish_error(self, *args, **kwargs):
        raise NotModifiedError()


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

        # One comment without an issue opened, which will have its
        # status set to a valid status, while closed.
        closed_with_status_comment = \
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

        closed_with_status_comment.issue_status = Comment.OPEN
        closed_with_status_comment.save()

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
