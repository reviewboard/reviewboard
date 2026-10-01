"""Unit tests for reviewboard.reviews.approval.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import kgb

from reviewboard.extensions.hooks import ReviewRequestApprovalHook
from reviewboard.extensions.tests.testcases import ExtensionHookTestCaseMixin
from reviewboard.reviews.approval import (
    get_default_review_request_approval,
    run_approval_hooks,
)
from reviewboard.reviews.models import Comment
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from reviewboard.reviews.approval import ReviewRequestApproval
    from reviewboard.reviews.models import ReviewRequest


class BaseApprovalTests(ExtensionHookTestCaseMixin,
                        kgb.SpyAgency,
                        TestCase):
    """Base class for approval-related unit tests.

    Version Added:
        9.0
    """

    fixtures = ['test_users']

    ######################
    # Instance variables #
    ######################

    #: The review request used for the test.
    review_request: ReviewRequest

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.review_request = self.create_review_request(publish=True)

    def _setup_hook(
        self,
        hook_cls: type[ReviewRequestApprovalHook],
    ) -> None:
        """Set up an approval hook for testing.

        Args:
            hook_cls (type):
                The hook to set up.
        """
        extension = self.extension
        assert extension is not None

        hook_cls(extension=extension)


class GetDefaultReviewRequestApprovalTests(BaseApprovalTests):
    """Unit tests for get_default_review_request_approval.

    Version Added:
        9.0
    """

    def test_get_approval_with_ship_it(self) -> None:
        """Testing get_default_review_request_approval with default approval
        logic with Ship It
        """
        review_request = self.review_request

        self.create_review(
            review_request,
            ship_it=True,
            publish=True,
        )

        self.assertEqual(
            get_default_review_request_approval(review_request),
            {
                'approved': True,
                'reason': None,
            })

    def test_get_approval_without_ship_it(self) -> None:
        """Testing get_default_review_request_approval with default approval
        logic with no Ship-Its
        """
        review_request = self.review_request

        self.create_review(
            review_request,
            ship_it=False,
            publish=True,
        )

        self.assertEqual(
            get_default_review_request_approval(review_request),
            {
                'approved': False,
                'reason': 'The review request has not been marked "Ship It!"',
            })

    def test_get_approval_with_open_issues(self) -> None:
        """Testing get_default_review_request_approval with default approval
        logic with open issues
        """
        review_request = self.review_request

        review = self.create_review(review_request, ship_it=True)
        self.create_general_comment(review, issue_opened=True)
        review.publish()

        review_request.reload_issue_open_count()

        self.assertEqual(
            get_default_review_request_approval(review_request),
            {
                'approved': False,
                'reason': 'The review request has open issues.',
            })

    def test_get_approval_with_unverified_issues(self) -> None:
        """Testing get_default_review_request_approval with default approval
        logic with unverified issues
        """
        review_request = self.review_request

        review = self.create_review(review_request, ship_it=True)
        comment = self.create_general_comment(review, issue_opened=True)
        review.publish()

        comment.issue_status = Comment.VERIFYING_RESOLVED
        comment.save()

        review_request.reload_issue_open_count()
        review_request.reload_issue_verifying_count()

        self.assertEqual(
            get_default_review_request_approval(review_request),
            {
                'approved': False,
                'reason': 'The review request has unverified issues.',
            })

    def test_get_approval_with_hooks(self) -> None:
        """Testing get_default_review_request_approval with a modern hook"""
        class MyApprovalHook(ReviewRequestApprovalHook):
            def get_approval(
                _self,
                *,
                review_request: ReviewRequest,
                prev_approval: ReviewRequestApproval,
            ) -> ReviewRequestApproval:
                self.assertEqual(prev_approval, {
                    'approved': False,
                    'reason': (
                        'The review request has not been marked "Ship It!"'
                    ),
                })

                return {
                    'approved': True,
                    'reason': 'Approved!',
                }

        review_request = self.review_request
        self._setup_hook(MyApprovalHook)

        with self.assertNoLogs():
            self.assertEqual(
                get_default_review_request_approval(review_request),
                {
                    'approved': True,
                    'reason': 'Approved!',
                })

    def test_get_approval_with_hooks_and_run_hooks_false(self) -> None:
        """Testing get_default_review_request_approval with a hook and
        run_hooks=False
        """
        class MyApprovalHook(ReviewRequestApprovalHook):
            def get_approval(
                _self,
                *,
                review_request: ReviewRequest,
                prev_approval: ReviewRequestApproval,
            ) -> ReviewRequestApproval:
                return {
                    'approved': True,
                    'reason': 'Approved!',
                }

        self.spy_on(MyApprovalHook.get_approval,
                    owner=MyApprovalHook)

        review_request = self.review_request
        self._setup_hook(MyApprovalHook)

        with self.assertNoLogs():
            self.assertEqual(
                get_default_review_request_approval(
                    review_request,
                    run_hooks=False,
                ),
                {
                    'approved': False,
                    'reason': (
                        'The review request has not been marked "Ship It!"'
                    ),
                })

        self.assertSpyNotCalled(MyApprovalHook.get_approval)


class RunApprovalHooksTests(BaseApprovalTests):
    """Unit tests for run_approval_hooks.

    Version Added:
        9.0
    """

    def test_get_approval_with_modern_hook(self) -> None:
        """Testing run_approval_hooks with a modern hook"""
        class MyApprovalHook(ReviewRequestApprovalHook):
            def get_approval(
                _self,
                *,
                review_request: ReviewRequest,
                prev_approval: ReviewRequestApproval,
            ) -> ReviewRequestApproval:
                self.assertEqual(
                    prev_approval,
                    {
                        'approved': False,
                        'reason': 'Not allowed! Nope!',
                    },
                )

                return {
                    'approved': True,
                    'reason': 'Approved!',
                }

        review_request = self.review_request
        self._setup_hook(MyApprovalHook)

        approval: ReviewRequestApproval = {
            'approved': False,
            'reason': 'Not allowed! Nope!',
        }

        with self.assertNoLogs():
            self.assertEqual(
                run_approval_hooks(
                    default_approval=approval,
                    review_request=review_request,
                ),
                {
                    'approved': True,
                    'reason': 'Approved!',
                },
            )

    def test_get_approval_with_modern_hook_without_reason_approved_unchanged(
        self,
    ) -> None:
        """Testing run_approval_hooks with a hook not overriding a
        reason and approved unchanged
        """
        class MyApprovalHook(ReviewRequestApprovalHook):
            def get_approval(
                _self,
                *,
                review_request: ReviewRequest,
                prev_approval: ReviewRequestApproval,
            ) -> ReviewRequestApproval:
                self.assertEqual(
                    prev_approval,
                    {
                        'approved': False,
                        'reason': 'Not allowed! Nope!',
                    },
                )

                return {
                    'approved': False,
                }

        self._setup_hook(MyApprovalHook)

        approval: ReviewRequestApproval = {
            'approved': False,
            'reason': 'Not allowed! Nope!',
        }

        with self.assertNoLogs():
            self.assertEqual(
                run_approval_hooks(
                    default_approval=approval,
                    review_request=self.review_request,
                ),
                {
                    'approved': False,
                    'reason': 'Not allowed! Nope!',
                })

    def test_get_approval_with_hook_exception(self) -> None:
        """Testing run_approval_hooks with a hook exception"""
        class MyApprovalHook(ReviewRequestApprovalHook):
            def get_approval(
                _self,
                *,
                review_request: ReviewRequest,
                prev_approval: ReviewRequestApproval,
            ) -> ReviewRequestApproval:
                raise Exception('oh no')

        self._setup_hook(MyApprovalHook)

        approval: ReviewRequestApproval = {
            'approved': False,
            'reason': 'Not allowed! Nope!',
        }

        with self.assertLogs() as logs:
            self.assertEqual(
                run_approval_hooks(
                    default_approval=approval,
                    review_request=self.review_request,
                ),
                {
                    'approved': False,
                    'reason': 'Not allowed! Nope!',
                },
            )

        self.assertEqual(len(logs.output), 1)
        self.assertTrue(logs.output[0].startswith(
            'ERROR:reviewboard.reviews.approval:Error when running '
            'ReviewRequestApprovalHook.get_approval function in extension '
            '"reviewboard.extensions.tests.testcases.DummyExtension": oh no'
            '\n'
            'Traceback'
        ))

    def test_get_approval_with_modern_hook_without_reason_approved_changed(
        self,
    ) -> None:
        """Testing run_approval_hooks with a hook not overriding a
        reason and approved changed
        """
        class MyApprovalHook(ReviewRequestApprovalHook):
            def get_approval(
                _self,
                *,
                review_request: ReviewRequest,
                prev_approval: ReviewRequestApproval,
            ) -> ReviewRequestApproval:
                self.assertEqual(
                    prev_approval,
                    {
                        'approved': False,
                        'reason': 'Not allowed! Nope!',
                    },
                )

                return {
                    'approved': True,
                }

        self._setup_hook(MyApprovalHook)

        approval: ReviewRequestApproval = {
            'approved': False,
            'reason': 'Not allowed! Nope!',
        }

        with self.assertNoLogs():
            self.assertEqual(
                run_approval_hooks(
                    default_approval=approval,
                    review_request=self.review_request,
                ),
                {
                    'approved': True,
                },
            )

    def test_get_approval_with_unimplemented_hook(self) -> None:
        """Testing run_approval_hooks with unimplemented hook"""
        class MyApprovalHook(ReviewRequestApprovalHook):
            pass

        self._setup_hook(MyApprovalHook)

        approval: ReviewRequestApproval = {
            'approved': False,
            'reason': 'Not allowed! Nope!',
        }

        with self.assertNoLogs():
            self.assertEqual(
                run_approval_hooks(
                    default_approval=approval,
                    review_request=self.review_request,
                ),
                {
                    'approved': False,
                    'reason': 'Not allowed! Nope!',
                },
            )

    def test_get_approval_with_legacy_hook_tuple(self) -> None:
        """Testing run_approval_hooks with legacy hook tuple result"""
        class MyApprovalHook(ReviewRequestApprovalHook):
            def is_approved(
                _self,
                review_request: ReviewRequest,
                prev_approved: bool,
                prev_failure: str | None,
            ) -> tuple[bool, str]:
                self.assertFalse(prev_approved)
                self.assertEqual(prev_failure, 'Not allowed! Nope!')

                return False, 'Nope.'

        self._setup_hook(MyApprovalHook)

        approval: ReviewRequestApproval = {
            'approved': False,
            'reason': 'Not allowed! Nope!',
        }

        with self.assertNoLogs():
            self.assertEqual(
                run_approval_hooks(
                    default_approval=approval,
                    review_request=self.review_request,
                ),
                {
                    'approved': False,
                    'reason': 'Nope.',
                },
            )

    def test_get_approval_with_legacy_hook_bool_true(self) -> None:
        """Testing run_approval_hooks with legacy hook True result"""
        class MyApprovalHook(ReviewRequestApprovalHook):
            def is_approved(
                _self,
                review_request: ReviewRequest,
                prev_approved: bool,
                prev_failure: str | None,
            ) -> bool:
                self.assertFalse(prev_approved)
                self.assertEqual(prev_failure, 'Not allowed! Nope!')

                return True

        self._setup_hook(MyApprovalHook)

        approval: ReviewRequestApproval = {
            'approved': False,
            'reason': 'Not allowed! Nope!',
        }

        with self.assertNoLogs():
            self.assertEqual(
                run_approval_hooks(
                    default_approval=approval,
                    review_request=self.review_request,
                ),
                {
                    'approved': True,
                    'reason': None,
                },
            )

    def test_get_approval_with_legacy_hook_bool_false(self) -> None:
        """Testing run_approval_hooks with legacy hook False result"""
        class MyApprovalHook(ReviewRequestApprovalHook):
            def is_approved(
                _self,
                review_request: ReviewRequest,
                prev_approved: bool,
                prev_failure: str | None,
            ) -> bool:
                self.assertFalse(prev_approved)
                self.assertEqual(prev_failure, 'Not allowed! Nope!')

                return False

        self._setup_hook(MyApprovalHook)

        approval: ReviewRequestApproval = {
            'approved': False,
            'reason': 'Not allowed! Nope!',
        }

        with self.assertNoLogs():
            self.assertEqual(
                run_approval_hooks(
                    default_approval=approval,
                    review_request=self.review_request,
                ),
                {
                    'approved': False,
                    'reason': 'Not allowed! Nope!',
                },
            )

    def test_get_approval_with_legacy_hook_invalid_result(self) -> None:
        """Testing run_approval_hooks with legacy hook and invalid result"""
        class MyApprovalHook(ReviewRequestApprovalHook):
            def is_approved(
                _self,
                review_request: ReviewRequest,
                prev_approved: bool,
                prev_failure: str | None,
            ) -> bool:
                self.assertFalse(prev_approved)
                self.assertEqual(prev_failure, 'Not allowed! Nope!')

                return 'xxx'  # type: ignore

            def __repr__(self) -> str:
                return '<MyApprovalHook>'

        self._setup_hook(MyApprovalHook)

        approval: ReviewRequestApproval = {
            'approved': False,
            'reason': 'Not allowed! Nope!',
        }

        with self.assertLogs() as logs:
            self.assertEqual(
                run_approval_hooks(
                    default_approval=approval,
                    review_request=self.review_request,
                ),
                {
                    'approved': False,
                    'reason': 'Not allowed! Nope!',
                },
            )

        self.assertEqual(len(logs.output), 1)
        self.assertTrue(logs.output[0].startswith(
            'ERROR:reviewboard.extensions.hooks.review_request_approval:'
            'Error when running ReviewRequestApprovalHook.is_approved '
            'function in extension '
            '"reviewboard.extensions.tests.testcases.DummyExtension": '
            '<MyApprovalHook> returned an invalid value \'xxx\' from '
            'is_approved\n'
            'Traceback'
        ))
