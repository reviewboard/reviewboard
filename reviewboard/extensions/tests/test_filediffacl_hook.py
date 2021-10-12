"""Unit tests for reviewboard.extensions.hooks.FileDiffACLHook."""

import kgb
from djblets.features.testing import override_feature_check

from reviewboard.extensions.hooks import FileDiffACLHook
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase
from reviewboard.reviews.features import DiffACLsFeature


class FileDiffACLHookTests(kgb.SpyAgency, BaseExtensionHookTestCase):
    """Tests for the FileDiffACLHook."""

    fixtures = ['test_scmtools', 'test_users']

    def setUp(self):
        super(FileDiffACLHookTests, self).setUp()

        self.user = self.create_user()
        self.review_request = self.create_review_request(
            create_repository=True)
        self.review_request.target_people.add(self.review_request.submitter)
        self.create_diffset(review_request=self.review_request, draft=True)
        self.review_request.publish(user=self.review_request.submitter)

    def test_single_aclhook_true(self):
        """Testing FileDiffACLHook basic approval with True result"""
        self._test_hook_approval_sequence([True], True)

    def test_single_aclhook_none(self):
        """Testing FileDiffACLHook basic approval with None result"""
        self._test_hook_approval_sequence([None], True)

    def test_single_aclhook_false(self):
        """Testing FileDiffACLHook basic approval with False result"""
        self._test_hook_approval_sequence([False], False)

    def test_multiple_aclhooks_1(self):
        """Testing FileDiffACLHook multiple with True and False"""
        self._test_hook_approval_sequence([True, False], False)

    def test_multiple_aclhooks_2(self):
        """Testing FileDiffACLHook multiple with True and None"""
        self._test_hook_approval_sequence([True, None], True)

    def test_multiple_aclhooks_3(self):
        """Testing FileDiffACLHook multiple with False and None"""
        self._test_hook_approval_sequence([False, None], False)

    def _test_hook_approval_sequence(self, accessible_values, result):
        """Test a sequence of FileDiffACLHook approval results.

        Args:
            accessible_values (list of bool):
                A list of the values to return from FileDiffACLHook
                implementations.

            result (bool):
                A resulting approval value to check.
        """
        with override_feature_check(DiffACLsFeature.feature_id,
                                    enabled=True):
            for value in accessible_values:
                hook = FileDiffACLHook(extension=self.extension)
                self.spy_on(hook.is_accessible, op=kgb.SpyOpReturn(value))

            self.assertEqual(self.review_request.is_accessible_by(self.user),
                             result)
