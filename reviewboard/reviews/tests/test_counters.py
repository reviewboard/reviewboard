from __future__ import unicode_literals

from django.contrib.auth.models import User
from kgb import SpyAgency

from reviewboard.accounts.models import Profile, LocalSiteProfile
from reviewboard.reviews.errors import NotModifiedError
from reviewboard.reviews.models import (Group, ReviewRequest,
                                        ReviewRequestDraft)
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class ReviewRequestCounterTests(SpyAgency, TestCase):
    """Unit tests for review request counters."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(ReviewRequestCounterTests, self).setUp()

        tool = Tool.objects.get(name='Subversion')
        repository = Repository.objects.create(name='Test1', path='path1',
                                               tool=tool)

        self.user = User.objects.create_user(username='testuser', password='',
                                             email='user@example.com')
        self.profile = self.user.get_profile()

        self.test_site = LocalSite.objects.create(name='test')
        self.site_profile2 = \
            LocalSiteProfile.objects.create(user=self.user,
                                            profile=self.profile,
                                            local_site=self.test_site)

        self.review_request = self.create_review_request(submitter=self.user,
                                                         repository=repository)

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

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_people = [self.user]
        draft.save()
        self.review_request.publish(self.user)

        self._check_counters(direct_incoming=1,
                             total_incoming=1,
                             total_outgoing=1,
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
        draft.summary = 'Test Summary'
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

        # There must be at least one target_group or target_people
        draft.target_people = [self.user]

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             total_incoming=1,
                             direct_incoming=0,
                             group_incoming=1,
                             starred_public=1)

        self.review_request.publish(self.user)
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             direct_incoming=1,
                             total_incoming=1,
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
                    owner=ReviewRequestDraft,
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
        draft.summary = 'Test Summary'
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

        # There must be at least one target_group or target_people
        draft.target_groups = [self.group]

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             direct_incoming=1,
                             total_incoming=1,
                             starred_public=1)

        self.review_request.publish(self.user)
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             group_incoming=1,
                             total_incoming=1,
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
                    owner=ReviewRequestDraft,
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

    def test_counts_with_reassignment_in_initial_draft(self):
        """Testing counters when changing review request ownership in initial
        draft
        """
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1)

        new_user = User.objects.create_user(username='test2',
                                            password='',
                                            email='user@example.com')
        site_profile = \
            new_user.get_site_profile(self.review_request.local_site)

        draft = ReviewRequestDraft.create(self.review_request)
        draft.owner = new_user
        draft.target_people = [draft.owner]
        draft.save()
        self.review_request.publish(self.user)

        self._check_counters(total_outgoing=0,
                             pending_outgoing=0,
                             starred_public=1)

        site_profile = LocalSiteProfile.objects.get(pk=site_profile.pk)
        self._check_counters_on_profile(site_profile,
                                        total_outgoing=1,
                                        pending_outgoing=1,
                                        direct_incoming=1,
                                        total_incoming=1)

    def test_counts_with_reassignment_in_initial_draft_new_profile(self):
        """Testing counters when changing review request ownership in initial
        draft and new owner without initial site profile
        """
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1)

        new_user = User.objects.create_user(username='test2',
                                            password='',
                                            email='user@example.com')

        draft = ReviewRequestDraft.create(self.review_request)
        draft.owner = new_user
        draft.target_people = [draft.owner]
        draft.save()
        self.review_request.publish(self.user)

        self._check_counters(total_outgoing=0,
                             pending_outgoing=0,
                             starred_public=1)

        site_profile = \
            new_user.get_site_profile(self.review_request.local_site)
        self._check_counters_on_profile(site_profile,
                                        total_outgoing=1,
                                        pending_outgoing=1,
                                        direct_incoming=1,
                                        total_incoming=1)

    def test_counts_with_reassignment_after_publish(self):
        """Testing counters when changing review request ownership after
        publish
        """
        self.review_request.publish(self.user)
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             starred_public=1)

        new_user = User.objects.create_user(username='test2',
                                            password='',
                                            email='user@example.com')
        site_profile = \
            new_user.get_site_profile(self.review_request.local_site)

        draft = ReviewRequestDraft.create(self.review_request)
        draft.owner = new_user
        draft.target_people = [draft.owner]
        draft.save()
        self.review_request.publish(self.user)

        self._check_counters(total_outgoing=0,
                             pending_outgoing=0,
                             starred_public=1)

        site_profile = LocalSiteProfile.objects.get(pk=site_profile.pk)
        self._check_counters_on_profile(site_profile,
                                        total_outgoing=1,
                                        pending_outgoing=1,
                                        direct_incoming=1,
                                        total_incoming=1)

    def test_counts_with_reassignment_after_publish_new_profile(self):
        """Testing counters when changing review request ownership after
        publish and new owner without initial site profile
        """
        self.review_request.publish(self.user)
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             starred_public=1)

        new_user = User.objects.create_user(username='test2',
                                            password='',
                                            email='user@example.com')

        draft = ReviewRequestDraft.create(self.review_request)
        draft.owner = new_user
        draft.target_people = [draft.owner]
        draft.save()
        self.review_request.publish(self.user)

        self._check_counters(total_outgoing=0,
                             pending_outgoing=0,
                             starred_public=1)

        site_profile = \
            new_user.get_site_profile(self.review_request.local_site)
        self._check_counters_on_profile(site_profile,
                                        total_outgoing=1,
                                        pending_outgoing=1,
                                        direct_incoming=1,
                                        total_incoming=1)

    def test_counts_with_reassignment_and_close(self):
        """Testing counters when changing review request ownership and closing
        in same operation
        """
        self.review_request.publish(self.user)
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             starred_public=1)

        new_user = User.objects.create_user(username='test2',
                                            password='',
                                            email='user@example.com')
        site_profile = \
            new_user.get_site_profile(self.review_request.local_site)

        # Note that it's not normally possible to update something like an
        # owner while also closing in the same operation. Drafts don't allow
        # it. However, we have logic that considers these combinations of
        # operations, and it's technically possible to do, so we're testing
        # it here by updating the review request manually.
        self.review_request.owner = new_user
        self.review_request.status = ReviewRequest.SUBMITTED
        self.review_request.save(update_counts=True,
                                 old_submitter=self.user)

        self._check_counters(total_outgoing=0,
                             pending_outgoing=0,
                             starred_public=0)

        site_profile = LocalSiteProfile.objects.get(pk=site_profile.pk)
        self._check_counters_on_profile(site_profile,
                                        total_outgoing=1,
                                        pending_outgoing=0)

    def test_counts_with_reassignment_and_reopen(self):
        """Testing counters when changing review request ownership and
        reopening in same operation
        """
        self.review_request.close(ReviewRequest.DISCARDED)
        self.assertFalse(self.review_request.public)
        self.assertEqual(self.review_request.status, ReviewRequest.DISCARDED)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=0,
                             starred_public=0)

        new_user = User.objects.create_user(username='test2',
                                            password='',
                                            email='user@example.com')
        site_profile = \
            new_user.get_site_profile(self.review_request.local_site)

        # Note that it's not normally possible to update something like an
        # owner while also reopening in the same operation. Drafts don't allow
        # it. However, we have logic that considers these combinations of
        # operations, and it's technically possible to do, so we're testing
        # it here by updating the review request manually.
        self.review_request.owner = new_user
        self.review_request.status = ReviewRequest.PENDING_REVIEW
        self.review_request.save(update_counts=True,
                                 old_submitter=self.user)

        self._check_counters(total_outgoing=0,
                             pending_outgoing=0,
                             starred_public=0)

        site_profile = LocalSiteProfile.objects.get(pk=site_profile.pk)
        self._check_counters_on_profile(site_profile,
                                        total_outgoing=1,
                                        pending_outgoing=1)

    def test_counts_with_join_group(self):
        """Testing counters when joining a review group"""
        user2 = self.create_user()
        group2 = self.create_review_group(name='group2')

        self.create_review_request(submitter=user2,
                                   target_groups=[group2],
                                   publish=True)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             total_incoming=0)

        group2.users.add(self.user)
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             total_incoming=1)

    def test_counts_with_leave_group(self):
        """Testing counters when leaving a review group"""
        user2 = self.create_user()

        group2 = self.create_review_group(name='group2')
        group2.users.add(self.user)

        self.create_review_request(submitter=user2,
                                   target_groups=[group2],
                                   publish=True)

        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             total_incoming=1)

        group2.users.remove(self.user)
        self._check_counters(total_outgoing=1,
                             pending_outgoing=1,
                             total_incoming=0)

    def _check_counters(self, total_outgoing=0, pending_outgoing=0,
                        direct_incoming=0, total_incoming=0,
                        starred_public=0, group_incoming=0,
                        with_local_site=False):
        """Check that the counters match the expected values.

        Args:
            total_outgoing (int):
                The expected number of total outgoing review requests.

            pending_outgoing (int):
                The expected number of pending outgoing review requests.

            direct_incoming (int):
                The expected number of review requests assigned directly to the
                user.

            total_incoming (int):
                The expected number of review requests assigned either directly
                or indirectly to the user.

            starred_public (int):
                The expected number of public review requests starred by the
                user.

            group_incoming (int):
                The expected number of review requests assigned to the test
                group.

            with_local_site (bool):
                Whether to run the test for a local site.
        """
        self._reload_objects()

        if with_local_site:
            main_site_profile = self.site_profile2
            unused_site_profile = self.site_profile
        else:
            main_site_profile = self.site_profile
            unused_site_profile = self.site_profile2

        self._check_counters_on_profile(main_site_profile, total_outgoing,
                                        pending_outgoing, direct_incoming,
                                        total_incoming, starred_public)
        self.assertEqual(
            self.group.incoming_request_count,
            group_incoming,
            'Expected Group.incoming_request_count to be %s. Got %s instead.'
            % (group_incoming, self.group.incoming_request_count))

        # These should never be affected by updates on the main LocalSite we're
        # working with, so they should always be 0.
        self._check_counters_on_profile(unused_site_profile)

    def _check_counters_on_profile(self, profile, total_outgoing=0,
                                   pending_outgoing=0, direct_incoming=0,
                                   total_incoming=0, starred_public=0):
        """Check that the counters match the expected values.

        Args:
            profile (reviewboard.accounts.models.LocalSiteProfile):
                The profile object to test counts on.

            total_outgoing (int):
                The expected number of total outgoing review requests.

            pending_outgoing (int):
                The expected number of pending outgoing review requests.

            direct_incoming (int):
                The expected number of review requests assigned directly to the
                user.

            total_incoming (int):
                The expected number of review requests assigned either directly
                or indirectly to the user.

            starred_public (int):
                The expected number of public review requests starred by the
                user.
        """
        msg = 'Expected %s to be %s. Got %s instead.'

        self.assertEqual(
            profile.total_outgoing_request_count,
            total_outgoing,
            msg % ('total_outgoing_request_count', total_outgoing,
                   profile.total_outgoing_request_count))
        self.assertEqual(
            profile.pending_outgoing_request_count,
            pending_outgoing,
            msg % ('pending_outgoing_request_count', pending_outgoing,
                   profile.pending_outgoing_request_count))
        self.assertEqual(
            profile.direct_incoming_request_count,
            direct_incoming,
            msg % ('direct_incoming_request_count', direct_incoming,
                   profile.direct_incoming_request_count))
        self.assertEqual(
            profile.total_incoming_request_count,
            total_incoming,
            msg % ('total_incoming_request_count', total_incoming,
                   profile.total_incoming_request_count))
        self.assertEqual(
            profile.starred_public_request_count,
            starred_public,
            msg % ('starred_public_request_count', starred_public,
                   profile.starred_public_request_count))

    def _reload_objects(self):
        self.test_site = LocalSite.objects.get(pk=self.test_site.pk)
        self.site_profile = \
            LocalSiteProfile.objects.get(pk=self.site_profile.pk)
        self.site_profile2 = \
            LocalSiteProfile.objects.get(pk=self.site_profile2.pk)
        self.group = Group.objects.get(pk=self.group.pk)

    def _raise_publish_error(self, *args, **kwargs):
        raise NotModifiedError()
