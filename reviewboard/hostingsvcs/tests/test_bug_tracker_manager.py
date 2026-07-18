"""Tests for reviewboard.hostingsvcs.managers.ConfiguredBugTrackerManager.

Version Added:
    9.0
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.test.client import RequestFactory
from djblets.conditions import Condition, ConditionSet

from reviewboard.accounts.conditions import UserInGroupChoice
from reviewboard.hostingsvcs.models import (
    ConfiguredBugTracker,
    SENTINEL_BUG_TRACKER_SERVICE_NAME,
)
from reviewboard.reviews.models import Bug, ReviewRequestDraft
from reviewboard.testing import TestCase


class ConfiguredBugTrackerManagerForReviewRequestTests(TestCase):
    """Unit tests for ConfiguredBugTrackerManager.for_review_request.

    Version Added:
        9.0
    """

    fixtures = ['test_users', 'test_scmtools']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.user = User.objects.create_user(username='test-user')

    def test_with_apply_to_all(self) -> None:
        """Testing for_review_request with apply_to=ALL"""
        repository = self.create_repository()
        review_request = self.create_review_request(repository=repository)

        tracker = ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='splat')

        self.assertEqual(
            ConfiguredBugTracker.objects.for_review_request(review_request,
                                                            user=self.user),
            [tracker])

    def test_with_selected_repositories(self) -> None:
        """Testing for_review_request with apply_to=SELECTED_REPOS"""
        repository1 = self.create_repository(name='repo1')
        repository2 = self.create_repository(name='repo2')
        review_request1 = self.create_review_request(repository=repository1)
        review_request2 = self.create_review_request(repository=repository2)

        tracker = ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='splat',
            apply_to=ConfiguredBugTracker.APPLY_TO_SELECTED_REPOS)
        tracker.repositories.add(repository1)

        self.assertEqual(
            ConfiguredBugTracker.objects.for_review_request(review_request1,
                                                            user=self.user),
            [tracker])
        self.assertEqual(
            ConfiguredBugTracker.objects.for_review_request(review_request2,
                                                            user=self.user),
            [])

    def test_with_no_repository(self) -> None:
        """Testing for_review_request with a repository-less review
        request
        """
        review_request = self.create_review_request()

        tracker_all = ConfiguredBugTracker.objects.create(
            name='Tracker All',
            service_name='splat')
        tracker_no_repos = ConfiguredBugTracker.objects.create(
            name='Tracker No Repos',
            service_name='splat',
            apply_to=ConfiguredBugTracker.APPLY_TO_NO_REPOS)
        selected_tracker = ConfiguredBugTracker.objects.create(
            name='Tracker Selected',
            service_name='splat',
            apply_to=ConfiguredBugTracker.APPLY_TO_SELECTED_REPOS)

        self.assertEqual(
            ConfiguredBugTracker.objects.for_review_request(review_request,
                                                            user=self.user),
            [tracker_all, tracker_no_repos])
        self.assertNotIn(
            selected_tracker,
            ConfiguredBugTracker.objects.for_review_request(review_request,
                                                            user=self.user))

    def test_with_no_repos_tracker_and_repository(self) -> None:
        """Testing for_review_request excludes apply_to=NO_REPOS trackers
        for review requests with a repository
        """
        repository = self.create_repository()
        review_request = self.create_review_request(repository=repository)

        ConfiguredBugTracker.objects.create(
            name='Tracker No Repos',
            service_name='splat',
            apply_to=ConfiguredBugTracker.APPLY_TO_NO_REPOS)

        self.assertEqual(
            ConfiguredBugTracker.objects.for_review_request(review_request,
                                                            user=self.user),
            [])

    def test_includes_default_bug_tracker(self) -> None:
        """Testing for_review_request includes the repository's default
        bug tracker
        """
        repository = self.create_repository()
        review_request = self.create_review_request(repository=repository)

        # This tracker's scoping does not match the repository, but it
        # is the repository's default.
        tracker = ConfiguredBugTracker.objects.create(
            name='Default Tracker',
            service_name='splat',
            apply_to=ConfiguredBugTracker.APPLY_TO_SELECTED_REPOS)

        repository.default_bug_tracker = tracker
        repository.save(update_fields=('default_bug_tracker',))

        self.assertEqual(
            ConfiguredBugTracker.objects.for_review_request(review_request,
                                                            user=self.user),
            [tracker])

    def test_excludes_disabled(self) -> None:
        """Testing for_review_request excludes disabled trackers"""
        repository = self.create_repository()
        review_request = self.create_review_request(repository=repository)

        ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='splat',
            enabled=False)

        self.assertEqual(
            ConfiguredBugTracker.objects.for_review_request(review_request,
                                                            user=self.user),
            [])

    def test_with_local_site(self) -> None:
        """Testing for_review_request filters by LocalSite"""
        local_site = self.create_local_site()
        local_site.users.add(self.user)

        repository = self.create_repository(local_site=local_site)
        review_request = self.create_review_request(
            repository=repository,
            local_site=local_site,
            local_id=1)

        global_tracker = ConfiguredBugTracker.objects.create(
            name='Global Tracker',
            service_name='splat')
        site_tracker = ConfiguredBugTracker.objects.create(
            name='Site Tracker',
            service_name='splat',
            local_site=local_site)

        trackers = ConfiguredBugTracker.objects.for_review_request(
            review_request,
            user=self.user)
        self.assertEqual(trackers, [site_tracker])
        self.assertNotIn(global_tracker, trackers)

    def test_filters_by_user_conditions(self) -> None:
        """Testing for_review_request filters by user conditions"""
        repository = self.create_repository()
        review_request = self.create_review_request(repository=repository)

        group = self.create_review_group(name='group1')
        other_user = User.objects.create_user(username='other-user')
        group.users.add(other_user)

        choice = UserInGroupChoice()
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(choice,
                      choice.get_operator('contains-any'),
                      [group]),
        ])

        open_tracker = ConfiguredBugTracker.objects.create(
            name='Open Tracker',
            service_name='splat')
        limited_tracker = ConfiguredBugTracker.objects.create(
            name='Limited Tracker',
            service_name='splat',
            user_conditions=condition_set.serialize())

        self.assertEqual(
            ConfiguredBugTracker.objects.for_review_request(review_request,
                                                            user=self.user),
            [open_tracker])
        self.assertEqual(
            ConfiguredBugTracker.objects.for_review_request(review_request,
                                                            user=other_user),
            [open_tracker, limited_tracker])

    def test_caches_on_request(self) -> None:
        """Testing for_review_request caches results on the request"""
        repository = self.create_repository()
        review_request = self.create_review_request(repository=repository)

        ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='splat')

        request = RequestFactory().get('/')

        trackers = ConfiguredBugTracker.objects.for_review_request(
            review_request,
            user=self.user,
            request=request)

        with self.assertNumQueries(0):
            self.assertIs(
                ConfiguredBugTracker.objects.for_review_request(
                    review_request,
                    user=self.user,
                    request=request),
                trackers)


class ConfiguredBugTrackerManagerWithLinkedBugsTests(TestCase):
    """Unit tests for ConfiguredBugTrackerManager.with_linked_bugs.

    Version Added:
        9.0
    """

    fixtures = ['test_users', 'test_scmtools']

    def test_with_linked_bugs(self) -> None:
        """Testing with_linked_bugs"""
        review_request = self.create_review_request()

        tracker = ConfiguredBugTracker.objects.create(name='Tracker',
                                                      service_name='splat')
        ConfiguredBugTracker.objects.create(name='Unlinked',
                                            service_name='splat')

        review_request.bugs.add(Bug.objects.get_or_create_bug(
            bug_tracker=tracker,
            bug_id='10'))

        self.assertEqual(
            ConfiguredBugTracker.objects.with_linked_bugs(review_request),
            [tracker])

    def test_excludes_sentinel(self) -> None:
        """Testing with_linked_bugs excludes the sentinel tracker"""
        review_request = self.create_review_request()

        review_request.bugs.add(Bug.objects.get_or_create_bug(
            bug_tracker=ConfiguredBugTracker.objects.get_sentinel(),
            bug_id='10'))

        self.assertEqual(
            ConfiguredBugTracker.objects.with_linked_bugs(review_request),
            [])

    def test_with_draft(self) -> None:
        """Testing with_linked_bugs with a draft"""
        review_request = self.create_review_request(publish=True)
        draft = ReviewRequestDraft.create(review_request)

        tracker = ConfiguredBugTracker.objects.create(name='Tracker',
                                                      service_name='splat')
        draft.bugs.add(Bug.objects.get_or_create_bug(bug_tracker=tracker,
                                                     bug_id='10'))

        self.assertEqual(ConfiguredBugTracker.objects.with_linked_bugs(draft),
                         [tracker])

    def test_caches_on_request(self) -> None:
        """Testing with_linked_bugs caches results on the request"""
        review_request = self.create_review_request()

        tracker = ConfiguredBugTracker.objects.create(name='Tracker',
                                                      service_name='splat')
        review_request.bugs.add(Bug.objects.get_or_create_bug(
            bug_tracker=tracker,
            bug_id='10'))

        request = RequestFactory().get('/')

        trackers = ConfiguredBugTracker.objects.with_linked_bugs(
            review_request,
            request=request)

        with self.assertNumQueries(0):
            self.assertIs(
                ConfiguredBugTracker.objects.with_linked_bugs(review_request,
                                                              request=request),
                trackers)

    def test_caches_per_details(self) -> None:
        """Testing with_linked_bugs caches separately per review request
        and draft
        """
        review_request = self.create_review_request(publish=True)
        draft = ReviewRequestDraft.create(review_request)

        tracker = ConfiguredBugTracker.objects.create(name='Tracker',
                                                      service_name='splat')
        draft.bugs.add(Bug.objects.get_or_create_bug(bug_tracker=tracker,
                                                     bug_id='10'))

        request = RequestFactory().get('/')

        # The review request and its draft share a primary key, so the
        # cache must key on the model as well.
        self.assertEqual(
            ConfiguredBugTracker.objects.with_linked_bugs(review_request,
                                                          request=request),
            [])
        self.assertEqual(
            ConfiguredBugTracker.objects.with_linked_bugs(draft,
                                                          request=request),
            [tracker])

    def test_with_multiple_linked_bugs(self) -> None:
        """Testing with_linked_bugs does not return duplicate trackers with
        multiple linked bugs
        """
        review_request = self.create_review_request()

        tracker = ConfiguredBugTracker.objects.create(name='Tracker',
                                                      service_name='splat')
        ConfiguredBugTracker.objects.create(name='Unlinked',
                                            service_name='splat')

        review_request.bugs.add(Bug.objects.get_or_create_bug(
            bug_tracker=tracker,
            bug_id='10'))
        review_request.bugs.add(Bug.objects.get_or_create_bug(
            bug_tracker=tracker,
            bug_id='12'))
        review_request.bugs.add(Bug.objects.get_or_create_bug(
            bug_tracker=tracker,
            bug_id='13'))

        self.assertEqual(
            ConfiguredBugTracker.objects.with_linked_bugs(review_request),
            [tracker])


class ConfiguredBugTrackerManagerAccessibleTests(TestCase):
    """Unit tests for ConfiguredBugTrackerManager.accessible.

    Version Added:
        9.0
    """

    def test_accessible(self) -> None:
        """Testing accessible includes disabled trackers and excludes the
        sentinel
        """
        tracker = ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='splat')
        disabled_tracker = ConfiguredBugTracker.objects.create(
            name='Disabled Tracker',
            service_name='splat',
            enabled=False)

        # Ensure that we've created the sentinel tracker.
        ConfiguredBugTracker.objects.get_sentinel()

        # This should not include the sentinel tracker row.
        self.assertQuerySetEqual(
            ConfiguredBugTracker.objects.accessible(),
            [disabled_tracker, tracker])

    def test_accessible_with_local_site(self) -> None:
        """Testing accessible with a LocalSite"""
        local_site = self.create_local_site()

        ConfiguredBugTracker.objects.create(
            name='Global Tracker',
            service_name='splat')
        site_tracker = ConfiguredBugTracker.objects.create(
            name='Site Tracker',
            service_name='splat',
            local_site=local_site)

        # This should not include the global tracker.
        self.assertQuerySetEqual(
            ConfiguredBugTracker.objects.accessible(local_site=local_site),
            [site_tracker])


class ConfiguredBugTrackerManagerGetSentinelTests(TestCase):
    """Unit tests for ConfiguredBugTrackerManager.get_sentinel.

    Version Added:
        9.0
    """

    fixtures = ['test_users']

    def test_creates_sentinel(self) -> None:
        """Testing get_sentinel creates the sentinel row"""
        sentinel = ConfiguredBugTracker.objects.get_sentinel()

        self.assertEqual(sentinel.service_name,
                         SENTINEL_BUG_TRACKER_SERVICE_NAME)
        self.assertFalse(sentinel.enabled)
        self.assertIsNone(sentinel.local_site)
        self.assertEqual(sentinel.apply_to,
                         ConfiguredBugTracker.APPLY_TO_NO_REPOS)

    def test_is_idempotent(self) -> None:
        """Testing get_sentinel returns the same row on repeat calls"""
        sentinel1 = ConfiguredBugTracker.objects.get_sentinel()
        sentinel2 = ConfiguredBugTracker.objects.get_sentinel()

        self.assertEqual(sentinel1.pk, sentinel2.pk)
        self.assertEqual(
            ConfiguredBugTracker.objects.filter(
                service_name=SENTINEL_BUG_TRACKER_SERVICE_NAME).count(),
            1)

    def test_returns_lowest_pk(self) -> None:
        """Testing get_sentinel returns the lowest-ID row if duplicates
        exist
        """
        sentinel1 = ConfiguredBugTracker.objects.get_sentinel()

        # Simulate a lost creation race.
        ConfiguredBugTracker.objects.create(
            name='Unattributed Bugs',
            service_name=SENTINEL_BUG_TRACKER_SERVICE_NAME,
            enabled=False,
            apply_to=ConfiguredBugTracker.APPLY_TO_NO_REPOS)

        self.assertEqual(ConfiguredBugTracker.objects.get_sentinel().pk,
                         sentinel1.pk)

    def test_excluded_from_for_review_request(self) -> None:
        """Testing the sentinel is excluded from for_review_request"""
        user = User.objects.create_user(username='test-user')
        review_request = self.create_review_request()

        ConfiguredBugTracker.objects.get_sentinel()

        self.assertEqual(
            ConfiguredBugTracker.objects.for_review_request(review_request,
                                                            user=user),
            [])
