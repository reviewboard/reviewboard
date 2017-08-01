"""Unit tests for ReviewRequestPageEntryRegistry."""

from __future__ import unicode_literals

from djblets.registries.errors import AlreadyRegisteredError

from reviewboard.reviews.detail import (BaseReviewRequestPageEntry,
                                        ReviewRequestPageEntryRegistry)
from reviewboard.testing import TestCase


class DummyEntry(BaseReviewRequestPageEntry):
    entry_type_id = 'dummy'


class ReviewRequestPageEntryRegistryTests(TestCase):
    """Unit tests for ReviewRequestPageEntryRegistry."""

    def setUp(self):
        super(ReviewRequestPageEntryRegistryTests, self).setUp()

        self.registry = ReviewRequestPageEntryRegistry()

    def test_register(self):
        """Testing ReviewRequestPageEntryRegistry.register"""
        self.registry.register(DummyEntry)
        self.assertIn(DummyEntry, self.registry)

    def test_register_with_entry_already_registered(self):
        """Testing ReviewRequestPageEntryRegistry.register with already
        registered entry
        """
        self.registry.register(DummyEntry)

        message = 'This review request page entry is already registered.'

        with self.assertRaisesMessage(AlreadyRegisteredError, message):
            self.registry.register(DummyEntry)

    def test_register_with_id_already_registered(self):
        """Testing ReviewRequestPageEntryRegistry.register with already
        registered entry_type_id
        """
        class DummyEntry2(DummyEntry):
            pass

        self.registry.register(DummyEntry)

        message = (
            'A review request page entry with the entry_type_id "dummy" is '
            'already registered by another entry (<class \'reviewboard.'
            'reviews.tests.test_review_request_page_entry_registry.'
            'DummyEntry\'>).'
        )

        with self.assertRaisesMessage(AlreadyRegisteredError, message):
            self.registry.register(DummyEntry2)

    def test_unregister(self):
        """Testing ReviewRequestPageEntryRegistry.unregister"""
        self.registry.register(DummyEntry)
        self.registry.unregister(DummyEntry)

        self.assertNotIn(DummyEntry, self.registry)

    def test_get_entry(self):
        """Testing ReviewRequestPageEntryRegistry.get_entry"""
        self.registry.register(DummyEntry)
        self.assertEqual(self.registry.get_entry('dummy'), DummyEntry)

    def test_get_entry_with_invalid_id(self):
        """Testing ReviewRequestPageEntryRegistry.get_entry with invalid entry
        ID
        """
        self.assertIsNone(self.registry.get_entry('dummy'))
