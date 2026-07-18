"""Tests for reviewboard.reviews.builtin_fields.TrackedBugsField.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import kgb
from django.contrib.auth.models import User
from django.test.client import RequestFactory
from django.utils import timezone

from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.reviews import builtin_fields
from reviewboard.reviews.builtin_fields import (
    BugsField,
    InformationFieldSet,
    MainFieldSet,
    TestingDoneField,
    TrackedBugsField,
    TrackedBugsTableField,
)
from reviewboard.reviews.models import Bug, ReviewRequest
from reviewboard.reviews.models.bug import BUGS_MIGRATED_KEY
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

        tracker = self.create_bug_tracker(name='My Tracker',
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

        tracker = self.create_bug_tracker(name='Default Tracker',
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

        self.create_bug_tracker(
            name='Limited Tracker',
            service_name='splat',
            limit_to_groups=[group])

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

        tracker = self.create_bug_tracker(name='Old Tracker',
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

        tracker = self.create_bug_tracker(name='Tracker',
                                          service_name='splat')
        other_tracker = self.create_bug_tracker(
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

        tracker = self.create_bug_tracker(name='Tracker',
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

        tracker = self.create_bug_tracker(name='Tracker')

        field = TrackedBugsField(review_request, tracker=tracker, usable=True)

        # Bugs link through the local tracker-qualified redirect, which also
        # powers the hover infobox.
        expected_url = (f'/r/{review_request.display_id}/'
                        f'bug-trackers/{tracker.pk}/bugs/123/')
        self.assertEqual(
            field.render_item('123'),
            f'<a class="bug" href="{expected_url}">123</a>')

    def test_render_item_with_unusable_tracker(self) -> None:
        """Testing TrackedBugsField.render_item renders plain IDs for
        unusable trackers
        """
        review_request = self.create_review_request()

        tracker = self.create_bug_tracker(name='Tracker')

        field = TrackedBugsField(review_request, tracker=tracker, usable=False)

        self.assertEqual(field.render_item('123'), '123')


class TrackedBugsTableFieldTests(kgb.SpyAgency, TestCase):
    """Unit tests for TrackedBugsTableField.

    Version Added:
        9.0
    """

    fixtures = ['test_users', 'test_scmtools']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.user = User.objects.create_user(username='table-test-user')
        self.request = RequestFactory().get('/')
        self.request.user = self.user

        self.tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat',
            settings={
                'display_mode': ConfiguredBugTracker.DISPLAY_MODE_DETAILED,
                'splat_org_name': 'my-org',
            })

    def test_build_fields_moves_field_to_main_fieldset(self) -> None:
        """Testing build_fields places detailed trackers in the main fieldset
        """
        review_request = self.create_review_request()

        info_fields = InformationFieldSet(
            review_request_details=review_request,
            request=self.request).build_fields()
        main_fields = MainFieldSet(
            review_request_details=review_request,
            request=self.request).build_fields()

        self.assertEqual(
            [
                field
                for field in info_fields
                if isinstance(field, TrackedBugsField)
            ],
            [])

        tracked_fields = [
            field
            for field in main_fields
            if isinstance(field, TrackedBugsTableField)
        ]

        self.assertEqual(len(tracked_fields), 1)
        self.assertEqual(tracked_fields[0].field_id,
                         f'bugs:{self.tracker.pk}')

        # The detailed table renders after the main fields.
        self.assertIs(main_fields[-1], tracked_fields[0])
        self.assertIsInstance(main_fields[-2], TestingDoneField)

    def test_build_fields_shares_trackers_across_fieldsets(self) -> None:
        """Testing build_fields looks up bug trackers once per request across
        fieldsets
        """
        review_request = self.create_review_request()

        self.spy_on(builtin_fields._build_tracked_bugs_fields)

        # The review request box builds the main fieldset twice, along
        # with the information fieldset.
        for fieldset_cls in (MainFieldSet, MainFieldSet, InformationFieldSet):
            fieldset_cls(
                review_request_details=review_request,
                request=self.request,
            ).build_fields()

        self.assertSpyCallCount(builtin_fields._build_tracked_bugs_fields, 1)

    def test_build_fields_caches_draft_separately(self) -> None:
        """Testing build_fields looks up bug trackers separately for a review
        request and its draft
        """
        review_request = self.create_review_request()
        draft = self.create_review_request_draft(review_request)

        self.spy_on(builtin_fields._build_tracked_bugs_fields)

        for review_request_details in (review_request, draft):
            MainFieldSet(
                review_request_details=review_request_details,
                request=self.request,
            ).build_fields()

        self.assertSpyCallCount(builtin_fields._build_tracked_bugs_fields, 2)

    def test_build_fields_with_compact_tracker(self) -> None:
        """Testing build_fields keeps compact trackers out of the main fieldset
        """
        review_request = self.create_review_request()

        self.tracker.settings['display_mode'] = \
            ConfiguredBugTracker.DISPLAY_MODE_COMPACT
        self.tracker.save(update_fields=('settings',))

        main_fields = MainFieldSet(
            review_request_details=review_request,
            request=self.request).build_fields()

        self.assertEqual(
            [
                field
                for field in main_fields
                if isinstance(field, TrackedBugsField)
            ],
            [])

    def test_render_value(self) -> None:
        """Testing TrackedBugsTableField.render_value with cached metadata"""
        review_request = self.create_review_request()

        bug = Bug.objects.create(bug_tracker=self.tracker,
                                 bug_id='123',
                                 summary='A crash',
                                 status='open',
                                 metadata_timestamp=timezone.now())
        review_request.bugs.add(bug)
        review_request.bugs.add(Bug.objects.create(bug_tracker=self.tracker,
                                                   bug_id='456'))

        field = TrackedBugsTableField(review_request,
                                      request=self.request,
                                      tracker=self.tracker,
                                      usable=True)
        html = field.render_value(field.value)

        self.assertIn('<th class="rb-c-bug-list__column-summary">', html)
        self.assertIn('<td class="rb-c-bug-list__summary">A crash</td>', html)
        self.assertIn('<td class="rb-c-bug-list__status">open</td>', html)
        self.assertIn(
            f'<a class="bug" href="/r/{review_request.display_id}/'
            f'bug-trackers/{self.tracker.pk}/bugs/123/">123</a>',
            html)

        # Bugs without cached metadata still get a row.
        self.assertIn('data-bug-id="456"', html)

    def test_render_value_without_usable_tracker(self) -> None:
        """Testing TrackedBugsTableField.render_value renders IDs alone for
        unusable trackers
        """
        review_request = self.create_review_request()

        bug = Bug.objects.create(bug_tracker=self.tracker,
                                 bug_id='123',
                                 summary='A crash',
                                 status='open',
                                 metadata_timestamp=timezone.now())
        review_request.bugs.add(bug)

        field = TrackedBugsTableField(review_request,
                                      request=self.request,
                                      tracker=self.tracker,
                                      usable=False)
        html = field.render_value(field.value)

        self.assertIn('data-bug-id="123"', html)
        self.assertNotIn('rb-c-bug-list__column-summary', html)
        self.assertNotIn('A crash', html)
        self.assertNotIn('<a class="bug"', html)

    def test_render_value_without_bugs(self) -> None:
        """Testing TrackedBugsTableField.render_value without any bugs"""
        review_request = self.create_review_request()

        field = TrackedBugsTableField(review_request,
                                      request=self.request,
                                      tracker=self.tracker,
                                      usable=True)
        html = field.render_value(field.value)

        self.assertIn('rb-c-bug-list__empty', html)
        self.assertIn('No bugs have been added.', html)

    def test_get_data_attributes(self) -> None:
        """Testing TrackedBugsTableField.get_data_attributes"""
        review_request = self.create_review_request()
        review_request.bugs.add(Bug.objects.create(bug_tracker=self.tracker,
                                                   bug_id='123'))

        field = TrackedBugsTableField(review_request,
                                      request=self.request,
                                      tracker=self.tracker,
                                      usable=True)
        attrs = field.get_data_attributes()

        self.assertEqual(
            attrs['bug-info-url'],
            f'/r/{review_request.display_id}/'
            f'bug-trackers/{self.tracker.pk}/bug-info/')

        # The bug has no cached metadata, so a refresh is needed.
        self.assertEqual(attrs['bug-info-stale'], '1')

    def test_get_data_attributes_with_fresh_metadata(self) -> None:
        """Testing TrackedBugsTableField.get_data_attributes with fresh
        metadata
        """
        review_request = self.create_review_request()
        review_request.bugs.add(Bug.objects.create(
            bug_tracker=self.tracker,
            bug_id='123',
            summary='A crash',
            status='open',
            metadata_timestamp=timezone.now()))

        field = TrackedBugsTableField(review_request,
                                      request=self.request,
                                      tracker=self.tracker,
                                      usable=True)
        attrs = field.get_data_attributes()

        self.assertIn('bug-info-url', attrs)
        self.assertNotIn('bug-info-stale', attrs)

    def test_get_data_attributes_with_unattributed_bugs(self) -> None:
        """Testing TrackedBugsTableField.get_data_attributes on the default
        tracker ignores unattributed bugs when checking for stale metadata
        """
        repository = self.create_repository()
        repository.default_bug_tracker = self.tracker
        repository.save(update_fields=('default_bug_tracker',))

        review_request = self.create_review_request(repository=repository)
        review_request.extra_data[BUGS_MIGRATED_KEY] = True
        review_request.save(update_fields=('extra_data',))

        review_request.bugs.add(
            Bug.objects.create(bug_tracker=self.tracker,
                               bug_id='10',
                               summary='A crash',
                               status='open',
                               metadata_timestamp=timezone.now()),
            Bug.objects.get_or_create_bug(
                bug_tracker=ConfiguredBugTracker.objects.get_sentinel(),
                bug_id='2'))

        field = TrackedBugsTableField(review_request,
                                      request=self.request,
                                      tracker=self.tracker,
                                      is_default=True,
                                      usable=True)

        self.assertEqual(field.value, ['2', '10'])

        # The unattributed bug can never have cached metadata, so it
        # must not trigger a refresh on every page load.
        attrs = field.get_data_attributes()
        self.assertIn('bug-info-url', attrs)
        self.assertNotIn('bug-info-stale', attrs)

        # It's still shown, by ID alone.
        html = field.render_value(field.value)
        self.assertIn('data-bug-id="2"', html)
        self.assertIn('<td class="rb-c-bug-list__summary">A crash</td>', html)

    def test_get_data_attributes_with_legacy_bugs(self) -> None:
        """Testing TrackedBugsTableField.get_data_attributes on the default
        tracker ignores legacy bugs when checking for stale metadata
        """
        repository = self.create_repository()
        repository.default_bug_tracker = self.tracker
        repository.save(update_fields=('default_bug_tracker',))

        review_request = self.create_review_request(repository=repository)
        review_request.bugs_closed = '5'
        review_request.save(update_fields=('bugs_closed',))

        field = TrackedBugsTableField(review_request,
                                      request=self.request,
                                      tracker=self.tracker,
                                      is_default=True,
                                      usable=True)

        self.assertEqual(field.value, ['5'])
        self.assertNotIn('bug-info-stale', field.get_data_attributes())
        self.assertIn('data-bug-id="5"', field.render_value(field.value))

    def test_get_data_attributes_without_metadata_support(self) -> None:
        """Testing TrackedBugsTableField.get_data_attributes with a tracker
        that cannot provide metadata
        """
        review_request = self.create_review_request()

        tracker = ConfiguredBugTracker.objects.create(
            name='Custom Tracker',
            service_name='custom-bug-tracker',
            settings={
                'display_mode': ConfiguredBugTracker.DISPLAY_MODE_DETAILED,
                'url_template': 'https://bugs.example.com/%s',
            })
        review_request.bugs.add(Bug.objects.create(bug_tracker=tracker,
                                                   bug_id='123'))

        field = TrackedBugsTableField(review_request,
                                      request=self.request,
                                      tracker=tracker,
                                      usable=True)

        self.assertNotIn('bug-info-url', field.get_data_attributes())
        self.assertNotIn('rb-c-bug-list__column-summary',
                         field.render_value(field.value))
