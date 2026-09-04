"""Tests for reviewboard.reviews.builtin_fields.TrackedBugsField.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.test.client import RequestFactory
from djblets.conditions import Condition, ConditionSet

from reviewboard.accounts.conditions import UserInGroupChoice
from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.reviews.builtin_fields import (BugsField,
                                                InformationFieldSet,
                                                TrackedBugsField)
from reviewboard.reviews.models import Bug, ReviewRequest
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from reviewboard.reviews.fields import BaseReviewRequestField


class InformationFieldSetBuildFieldsTests(TestCase):
    """Unit tests for InformationFieldSet.build_fields.

    Version Added:
        9.0
    """

    fixtures = ['test_users', 'test_scmtools']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.user = User.objects.create_user(username='field-test-user')
        self.request = RequestFactory().get('/')
        self.request.user = self.user

    def _build_fields(
        self,
        review_request: ReviewRequest,
    ) -> Sequence[BaseReviewRequestField[Any]]:
        """Return the built fields for a review request.

        Args:
            review_request (ReviewRequest):
                The review request to build fields for.

        Returns:
            list of reviewboard.reviews.fields.BaseReviewRequestField:
            The built fields.
        """
        fieldset = InformationFieldSet(
            review_request_details=review_request,
            request=self.request)

        return fieldset.build_fields()

    def test_with_no_trackers(self) -> None:
        """Testing build_fields with no trackers"""
        review_request = self.create_review_request()

        fields = self._build_fields(review_request)

        bug_fields = [
            field
            for field in fields
            if isinstance(field, (BugsField, TrackedBugsField))
        ]

        self.assertEqual(len(bug_fields), 1)
        self.assertIsInstance(bug_fields[0], BugsField)

    def test_with_available_tracker(self) -> None:
        """Testing build_fields with an available tracker"""
        review_request = self.create_review_request()

        tracker = ConfiguredBugTracker.objects.create(name='My Tracker',
                                                      service_name='splat')

        fields = self._build_fields(review_request)

        tracked_fields = [
            field
            for field in fields
            if isinstance(field, TrackedBugsField)
        ]

        self.assertEqual(len(tracked_fields), 1)
        field = tracked_fields[0]
        self.assertEqual(field.field_id, f'bugs:{tracker.pk}')
        self.assertEqual(field.label, 'My Tracker')
        self.assertTrue(field.is_editable)

        # Without a default tracker, the legacy field remains for
        # unattributed bugs.
        self.assertEqual(
            len([
                field
                for field in fields
                if isinstance(field, BugsField)
            ]),
            1)

    def test_with_default_tracker(self) -> None:
        """Testing build_fields replaces the legacy field with the default
        tracker's field
        """
        repository = self.create_repository()
        review_request = self.create_review_request(repository=repository)

        tracker = ConfiguredBugTracker.objects.create(name='Default Tracker',
                                                      service_name='splat')
        repository.default_bug_tracker = tracker
        repository.save(update_fields=('default_bug_tracker',))

        fields = self._build_fields(review_request)

        self.assertEqual(
            [
                field
                for field in fields
                if isinstance(field, BugsField)
            ],
            [])

        tracked_fields = [
            field
            for field in fields
            if isinstance(field, TrackedBugsField)
        ]

        self.assertEqual(len(tracked_fields), 1)
        self.assertTrue(tracked_fields[0].is_default)

    def test_with_acl_failing_tracker(self) -> None:
        """Testing build_fields with a tracker the user cannot use"""
        review_request = self.create_review_request()

        group = self.create_review_group(name='limited-group')

        choice = UserInGroupChoice()
        condition_set = ConditionSet(ConditionSet.MODE_ALL, [
            Condition(choice,
                      choice.get_operator('contains-any'),
                      [group]),
        ])

        ConfiguredBugTracker.objects.create(
            name='Limited Tracker',
            service_name='splat',
            user_conditions=condition_set.serialize())

        fields = self._build_fields(review_request)

        # The tracker is not available to the user and has no linked
        # bugs, so no field is built for it.
        self.assertEqual(
            [
                field
                for field in fields
                if isinstance(field, TrackedBugsField)
            ],
            [])

    def test_with_linked_unavailable_tracker(self) -> None:
        """Testing build_fields renders linked bugs on unavailable
        trackers read-only
        """
        review_request = self.create_review_request()

        tracker = ConfiguredBugTracker.objects.create(name='Old Tracker',
                                                      service_name='splat',
                                                      enabled=False)
        bug = Bug.objects.create(bug_tracker=tracker, bug_id='123')
        review_request.bugs.add(bug)

        fields = self._build_fields(review_request)

        tracked_fields = [
            field
            for field in fields
            if isinstance(field, TrackedBugsField)
        ]

        self.assertEqual(len(tracked_fields), 1)
        field = tracked_fields[0]
        self.assertEqual(field.field_id, f'bugs:{tracker.pk}')
        self.assertFalse(field.is_editable)
        self.assertEqual(field.value, ['123'])


class TrackedBugsFieldTests(TestCase):
    """Unit tests for TrackedBugsField.

    Version Added:
        9.0
    """

    fixtures = ['test_users', 'test_scmtools']

    def test_load_value(self) -> None:
        """Testing TrackedBugsField.load_value from linked bugs"""
        review_request = self.create_review_request()

        tracker = ConfiguredBugTracker.objects.create(name='Tracker',
                                                      service_name='splat')
        other_tracker = ConfiguredBugTracker.objects.create(
            name='Other Tracker',
            service_name='splat')

        for bug_tracker, bug_id in ((tracker, '10'),
                                    (tracker, '2'),
                                    (other_tracker, '99')):
            review_request.bugs.add(Bug.objects.get_or_create_bug(
                bug_tracker=bug_tracker,
                bug_id=bug_id))

        field = TrackedBugsField(review_request, tracker=tracker)

        self.assertEqual(field.load_value(review_request), ['2', '10'])

    def test_load_value_for_default_tracker(self) -> None:
        """Testing TrackedBugsField.load_value for the default tracker
        reads the legacy view
        """
        repository = self.create_repository()
        review_request = self.create_review_request(repository=repository)
        review_request.bugs_closed = '5,3'
        review_request.save(update_fields=('bugs_closed',))

        tracker = ConfiguredBugTracker.objects.create(name='Tracker',
                                                      service_name='splat')
        repository.default_bug_tracker = tracker
        repository.save(update_fields=('default_bug_tracker',))

        field = TrackedBugsField(review_request, tracker=tracker,
                                 is_default=True)

        # The review request is unmigrated, so the legacy string is read.
        self.assertEqual(field.load_value(review_request), ['3', '5'])

    def test_render_item_with_usable_tracker(self) -> None:
        """Testing TrackedBugsField.render_item links bugs for usable
        trackers
        """
        review_request = self.create_review_request()

        tracker = ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='custom-bug-tracker',
            settings={
                'url_template': 'https://bugs.example.com/%s',
            })

        field = TrackedBugsField(review_request, tracker=tracker,
                                 usable=True)

        self.assertEqual(
            field.render_item('123'),
            '<a class="bug" href="https://bugs.example.com/123">123</a>')

    def test_render_item_with_unusable_tracker(self) -> None:
        """Testing TrackedBugsField.render_item renders plain IDs for
        unusable trackers
        """
        review_request = self.create_review_request()

        tracker = ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='custom-bug-tracker',
            settings={
                'url_template': 'https://bugs.example.com/%s',
            })

        field = TrackedBugsField(review_request, tracker=tracker,
                                 usable=False)

        self.assertEqual(field.render_item('123'), '123')
