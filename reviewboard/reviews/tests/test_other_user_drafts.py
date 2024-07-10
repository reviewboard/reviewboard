"""Unit tests for viewing drafts as other users.

Version Added:
    7.0.2
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Union, cast

from django.contrib.auth.models import Permission, User

from reviewboard.reviews.context import ReviewRequestContext
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft


class OtherUserDraftTests(TestCase):
    """Unit tests for viewing drafts as other users.

    Admins or users with the reviews.can_edit_reviewrequest permission are
    allowed to see and manipulate drafts on review requests owned by other
    people. These tests cover the various reviewable pages and check that we're
    adding the right things to the page data.

    Version Added:
        7.0.2
    """

    fixtures = ['test_scmtools', 'test_users']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        users = User.objects.in_bulk(
            ['doc', 'grumpy', 'admin', 'dopey'],
            field_name='username')
        self.user_owner = users['doc']
        self.user_regular = users['grumpy']
        self.user_admin = users['admin']
        self.user_privileged = users['dopey']
        self.user_privileged.user_permissions.add(
            Permission.objects.get(codename='can_edit_reviewrequest'))

    def test_unpublished_review_request_as_owner(self) -> None:
        """Testing ReviewRequestDetailView with an unpublished review request
        as the owner
        """
        review_request = self.create_review_request()
        draft = self.create_review_request_draft(review_request)

        self.client.force_login(self.user_owner)
        rsp = self.client.get(review_request.get_absolute_url())

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_unpublished_review_request_as_regular_user(self) -> None:
        """Testing ReviewRequestDetailView with an unpublished review request
        as a regular user
        """
        review_request = self.create_review_request()
        self.create_review_request_draft(review_request)

        self.client.force_login(self.user_regular)
        rsp = self.client.get(review_request.get_absolute_url())

        self.assertEqual(rsp.status_code, 403)

    def test_unpublished_review_request_as_admin(self) -> None:
        """Testing ReviewRequestDetailView with an unpublished review request
        as an admin
        """
        review_request = self.create_review_request()
        draft = self.create_review_request_draft(review_request)

        self.client.force_login(self.user_admin)
        rsp = self.client.get(review_request.get_absolute_url())

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=True,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_unpublished_review_request_as_privileged(self) -> None:
        """Testing ReviewRequestDetailView with an unpublished review request
        as a privileged user
        """
        review_request = self.create_review_request()
        draft = self.create_review_request_draft(review_request)

        self.client.force_login(self.user_privileged)
        rsp = self.client.get(review_request.get_absolute_url())

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=True,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_review_request_draft_as_owner(self) -> None:
        """Testing ReviewRequestDetailView with a draft on a published review
        request as the owner
        """
        review_request = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(review_request)

        self.client.force_login(self.user_owner)
        rsp = self.client.get(review_request.get_absolute_url())

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_review_request_draft_as_regular_user(self) -> None:
        """Testing ReviewRequestDetailView with a draft on a published review
        request as a regular user
        """
        review_request = self.create_review_request(publish=True)
        self.create_review_request_draft(review_request)

        self.client.force_login(self.user_regular)
        rsp = self.client.get(review_request.get_absolute_url())

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=None,
            review_request_details=review_request,
            mutable_by_user=False,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_review_request_draft_as_admin(self) -> None:
        """Testing ReviewRequestDetailView with a draft on a published review
        request as an admin
        """
        review_request = self.create_review_request(publish=True)
        self.create_review_request_draft(review_request)

        self.client.force_login(self.user_admin)
        rsp = self.client.get(review_request.get_absolute_url())

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=None,
            review_request_details=review_request,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=True,
            viewing_user_draft=False)

    def test_review_request_draft_as_privileged(self) -> None:
        """Testing ReviewRequestDetailView with a draft on a published review
        request as a privileged user
        """
        review_request = self.create_review_request(publish=True)
        self.create_review_request_draft(review_request)

        self.client.force_login(self.user_privileged)
        rsp = self.client.get(review_request.get_absolute_url())

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=None,
            review_request_details=review_request,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=True,
            viewing_user_draft=False)

    def test_review_request_draft_as_owner_with_view_draft(self) -> None:
        """Testing ReviewRequestDetailView with a draft on a published review
        request as the owner with ?view-draft=1
        """
        review_request = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(review_request)

        self.client.force_login(self.user_owner)
        rsp = self.client.get(review_request.get_absolute_url() +
                              '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_review_request_draft_as_regular_user_with_view_draft(
        self,
    ) -> None:
        """Testing ReviewRequestDetailView with a draft on a published review
        request as a regular user with ?view-draft=1
        """
        review_request = self.create_review_request(publish=True)
        self.create_review_request_draft(review_request)

        self.client.force_login(self.user_regular)
        rsp = self.client.get(review_request.get_absolute_url() +
                              '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=None,
            review_request_details=review_request,
            mutable_by_user=False,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_review_request_draft_as_admin_with_view_draft(self) -> None:
        """Testing ReviewRequestDetailView with a draft on a published review
        request as an admin with ?view-draft=1
        """
        review_request = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(review_request)

        self.client.force_login(self.user_admin)
        rsp = self.client.get(review_request.get_absolute_url() +
                              '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_review_request_draft_as_privileged_user_with_view_draft(
        self,
    ) -> None:
        """Testing ReviewRequestDetailView with a draft on a published review
        request as a privileged_user with ?view-draft=1
        """
        review_request = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(review_request)

        self.client.force_login(self.user_privileged)
        rsp = self.client.get(review_request.get_absolute_url() +
                              '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_unpublished_diff_as_owner(self) -> None:
        """Testing ReviewsDiffViewerView with an unpublished review request as
        the owner
        """
        review_request = self.create_review_request(create_repository=True)
        diffset = self.create_diffset(review_request, draft=True)
        draft = review_request.draft.get()

        self.client.force_login(self.user_owner)
        rsp = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_unpublished_diff_as_regular_user(self) -> None:
        """Testing ReviewsDiffViewerView with an unpublished review request as
        a regular user
        """
        review_request = self.create_review_request(create_repository=True)
        diffset = self.create_diffset(review_request, draft=True)

        self.client.force_login(self.user_regular)
        rsp = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }))

        self.assertEqual(rsp.status_code, 403)

    def test_unpublished_diff_as_admin(self) -> None:
        """Testing ReviewsDiffViewerView with an unpublished review request as
        an admin
        """
        review_request = self.create_review_request(create_repository=True)
        diffset = self.create_diffset(review_request, draft=True)
        draft = review_request.draft.get()

        self.client.force_login(self.user_admin)
        rsp = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=True,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_unpublished_diff_as_privileged(self) -> None:
        """Testing ReviewsDiffViewerView with an unpublished review request as
        a privileged user
        """
        review_request = self.create_review_request(create_repository=True)
        diffset = self.create_diffset(review_request, draft=True)
        draft = review_request.draft.get()

        self.client.force_login(self.user_privileged)
        rsp = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=True,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_draft_diff_as_owner(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as the owner"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        self.create_diffset(review_request)
        diffset = self.create_diffset(review_request, revision=2, draft=True)
        draft = review_request.draft.get()

        self.client.force_login(self.user_owner)
        rsp = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_draft_diff_as_regular_user(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as a regular
        user
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        self.create_diffset(review_request)
        diffset = self.create_diffset(review_request, revision=2, draft=True)

        self.client.force_login(self.user_regular)
        rsp = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }))

        self.assertEqual(rsp.status_code, 404)

    def test_draft_diff_as_admin(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as an admin"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        self.create_diffset(review_request)
        diffset = self.create_diffset(review_request, revision=2, draft=True)

        self.client.force_login(self.user_admin)
        rsp = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=None,
            review_request_details=review_request,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=True,
            viewing_user_draft=False)

    def test_draft_diff_as_privileged(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as a privileged
        user
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        self.create_diffset(review_request)
        diffset = self.create_diffset(review_request, revision=2, draft=True)

        self.client.force_login(self.user_privileged)
        rsp = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=None,
            review_request_details=review_request,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=True,
            viewing_user_draft=False)

    def test_draft_diff_as_owner_with_view_draft(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as the owner
        with ?view-draft=1
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        self.create_diffset(review_request)
        diffset = self.create_diffset(review_request, revision=2, draft=True)
        draft = review_request.draft.get()

        self.client.force_login(self.user_owner)
        rsp = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_draft_diff_as_regular_user_with_view_draft(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as a regular
        user with ?view-draft=1
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        self.create_diffset(review_request)
        diffset = self.create_diffset(review_request, revision=2, draft=True)

        self.client.force_login(self.user_regular)
        rsp = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 404)

    def test_draft_diff_as_admin_with_view_draft(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as an admin with
        ?view-draft=1
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        self.create_diffset(review_request)
        diffset = self.create_diffset(review_request, revision=2, draft=True)
        draft = review_request.draft.get()

        self.client.force_login(self.user_admin)
        rsp = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_draft_diff_as_privileged_with_view_draft(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as a privileged
        user with ?view-draft=1
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        self.create_diffset(review_request)
        diffset = self.create_diffset(review_request, revision=2, draft=True)
        draft = review_request.draft.get()

        self.client.force_login(self.user_privileged)
        rsp = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_draft_interdiff_as_owner(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as the owner"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset1 = self.create_diffset(review_request)
        diffset2 = self.create_diffset(review_request, revision=2, draft=True)
        draft = review_request.draft.get()

        self.client.force_login(self.user_owner)
        rsp = self.client.get(
            local_site_reverse(
                'view-interdiff',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset1.revision,
                    'interdiff_revision': diffset2.revision,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_draft_interdiff_as_regular_user(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as a regular
        user
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset1 = self.create_diffset(review_request)
        diffset2 = self.create_diffset(review_request, revision=2, draft=True)

        self.client.force_login(self.user_regular)
        rsp = self.client.get(
            local_site_reverse(
                'view-interdiff',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset1.revision,
                    'interdiff_revision': diffset2.revision,
                }))

        self.assertEqual(rsp.status_code, 404)

    def test_draft_interdiff_as_admin(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as an admin"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset1 = self.create_diffset(review_request)
        diffset2 = self.create_diffset(review_request, revision=2, draft=True)

        self.client.force_login(self.user_admin)
        rsp = self.client.get(
            local_site_reverse(
                'view-interdiff',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset1.revision,
                    'interdiff_revision': diffset2.revision,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=None,
            review_request_details=review_request,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=True,
            viewing_user_draft=False)

    def test_draft_interdiff_as_privileged(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as a privileged
        user
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset1 = self.create_diffset(review_request)
        diffset2 = self.create_diffset(review_request, revision=2, draft=True)

        self.client.force_login(self.user_privileged)
        rsp = self.client.get(
            local_site_reverse(
                'view-interdiff',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset1.revision,
                    'interdiff_revision': diffset2.revision,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=None,
            review_request_details=review_request,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=True,
            viewing_user_draft=False)

    def test_draft_interdiff_as_owner_with_view_draft(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as the owner
        with ?view-draft=1
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset1 = self.create_diffset(review_request)
        diffset2 = self.create_diffset(review_request, revision=2, draft=True)
        draft = review_request.draft.get()

        self.client.force_login(self.user_owner)
        rsp = self.client.get(
            local_site_reverse(
                'view-interdiff',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset1.revision,
                    'interdiff_revision': diffset2.revision,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_draft_interdiff_as_regular_user_with_view_draft(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as a regular
        user with ?view-draft=1
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset1 = self.create_diffset(review_request)
        diffset2 = self.create_diffset(review_request, revision=2, draft=True)

        self.client.force_login(self.user_regular)
        rsp = self.client.get(
            local_site_reverse(
                'view-interdiff',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset1.revision,
                    'interdiff_revision': diffset2.revision,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 404)

    def test_draft_interdiff_as_admin_with_view_draft(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as an admin with
        ?view-draft=1
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset1 = self.create_diffset(review_request)
        diffset2 = self.create_diffset(review_request, revision=2, draft=True)
        draft = review_request.draft.get()

        self.client.force_login(self.user_admin)
        rsp = self.client.get(
            local_site_reverse(
                'view-interdiff',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset1.revision,
                    'interdiff_revision': diffset2.revision,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_draft_interdiff_as_privileged_with_view_draft(self) -> None:
        """Testing ReviewsDiffViewerView with a new draft diff as a privileged
        user with ?view-draft=1
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset1 = self.create_diffset(review_request)
        diffset2 = self.create_diffset(review_request, revision=2, draft=True)
        draft = review_request.draft.get()

        self.client.force_login(self.user_privileged)
        rsp = self.client.get(
            local_site_reverse(
                'view-interdiff',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset1.revision,
                    'interdiff_revision': diffset2.revision,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_unpublished_file_attachment_as_owner(self) -> None:
        """Testing ReviewFileAttachmentView with an unpublished review request
        as the owner
        """
        review_request = self.create_review_request()
        draft = self.create_review_request_draft(review_request)
        attachment = self.create_file_attachment(review_request, draft=draft)

        self.client.force_login(self.user_owner)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': attachment.pk,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_unpublished_file_attachment_as_regular_user(self) -> None:
        """Testing ReviewFileAttachmentView with an unpublished review request
        as a regular user
        """
        review_request = self.create_review_request()
        draft = self.create_review_request_draft(review_request)
        attachment = self.create_file_attachment(review_request, draft=draft)

        self.client.force_login(self.user_regular)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': attachment.pk,
                }))

        self.assertEqual(rsp.status_code, 403)

    def test_unpublished_file_attachment_as_admin(self) -> None:
        """Testing ReviewFileAttachmentView with an unpublished review request
        as an admin
        """
        review_request = self.create_review_request()
        draft = self.create_review_request_draft(review_request)
        attachment = self.create_file_attachment(review_request, draft=draft)

        self.client.force_login(self.user_admin)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': attachment.pk,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=True,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_unpublished_file_attachment_as_privileged(self) -> None:
        """Testing ReviewFileAttachmentView with an unpublished review request
        as a privileged user
        """
        review_request = self.create_review_request()
        draft = self.create_review_request_draft(review_request)
        attachment = self.create_file_attachment(review_request, draft=draft)

        self.client.force_login(self.user_privileged)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': attachment.pk,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=True,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_draft_file_attachment_as_owner(self) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as the
        owner
        """
        review_request = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(review_request)
        attachment = self.create_file_attachment(review_request, draft=draft)

        self.client.force_login(self.user_owner)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': attachment.pk,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_draft_file_attachment_as_regular_user(self) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as a
        regular user
        """
        review_request = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(review_request)
        attachment = self.create_file_attachment(review_request, draft=draft)

        self.client.force_login(self.user_regular)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': attachment.pk,
                }))

        self.assertEqual(rsp.status_code, 404)

    def test_draft_file_attachment_as_admin(self) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as an
        admin
        """
        review_request = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(review_request)
        attachment = self.create_file_attachment(review_request, draft=draft)

        self.client.force_login(self.user_admin)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': attachment.pk,
                }))

        self.assertEqual(rsp.status_code, 404)

    def test_draft_file_attachment_as_privileged(self) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as a
        privileged user
        """
        review_request = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(review_request)
        attachment = self.create_file_attachment(review_request, draft=draft)

        self.client.force_login(self.user_privileged)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': attachment.pk,
                }))

        self.assertEqual(rsp.status_code, 404)

    def test_draft_file_attachment_diff_as_owner(self) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as the
        owner
        """
        review_request = self.create_review_request(publish=True)
        attachment1 = self.create_file_attachment(review_request)
        draft = self.create_review_request_draft(review_request)
        attachment2 = self.create_file_attachment(
            review_request, draft=draft,
            attachment_history=attachment1.attachment_history)

        self.client.force_login(self.user_owner)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_diff_id': attachment1.pk,
                    'file_attachment_id': attachment2.pk,
                }))

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_draft_file_attachment_diff_as_regular_user(self) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as a
        regular user
        """
        review_request = self.create_review_request(publish=True)
        attachment1 = self.create_file_attachment(review_request)
        draft = self.create_review_request_draft(review_request)
        attachment2 = self.create_file_attachment(
            review_request, draft=draft,
            attachment_history=attachment1.attachment_history)

        self.client.force_login(self.user_regular)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_diff_id': attachment1.pk,
                    'file_attachment_id': attachment2.pk,
                }))

        self.assertEqual(rsp.status_code, 404)

    def test_draft_file_attachment_diff_as_admin(self) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as an
        admin
        """
        review_request = self.create_review_request(publish=True)
        attachment1 = self.create_file_attachment(review_request)
        draft = self.create_review_request_draft(review_request)
        attachment2 = self.create_file_attachment(
            review_request, draft=draft,
            attachment_history=attachment1.attachment_history)

        self.client.force_login(self.user_admin)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_diff_id': attachment1.pk,
                    'file_attachment_id': attachment2.pk,
                }))

        self.assertEqual(rsp.status_code, 404)

    def test_draft_file_attachment_diff_as_privileged(self) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as a
        privileged user
        """
        review_request = self.create_review_request(publish=True)
        attachment1 = self.create_file_attachment(review_request)
        draft = self.create_review_request_draft(review_request)
        attachment2 = self.create_file_attachment(
            review_request, draft=draft,
            attachment_history=attachment1.attachment_history)

        self.client.force_login(self.user_privileged)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_diff_id': attachment1.pk,
                    'file_attachment_id': attachment2.pk,
                }))

        self.assertEqual(rsp.status_code, 404)

    def test_draft_file_attachment_as_owner_with_view_draft(self) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as the
        owner
        """
        review_request = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(review_request)
        attachment = self.create_file_attachment(review_request, draft=draft)

        self.client.force_login(self.user_owner)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': attachment.pk,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_draft_file_attachment_as_regular_user_with_view_draft(
        self,
    ) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as a
        regular user
        """
        review_request = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(review_request)
        attachment = self.create_file_attachment(review_request, draft=draft)

        self.client.force_login(self.user_regular)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': attachment.pk,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 404)

    def test_draft_file_attachment_as_admin_with_view_draft(self) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as an
        admin
        """
        review_request = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(review_request)
        attachment = self.create_file_attachment(review_request, draft=draft)

        self.client.force_login(self.user_admin)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': attachment.pk,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=True,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_draft_file_attachment_as_privileged_with_view_draft(self) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as a
        privileged user
        """
        review_request = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(review_request)
        attachment = self.create_file_attachment(review_request, draft=draft)

        self.client.force_login(self.user_privileged)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': attachment.pk,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=True,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_draft_file_attachment_diff_as_owner_with_view_draft(self) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as the
        owner
        """
        review_request = self.create_review_request(publish=True)
        attachment1 = self.create_file_attachment(review_request)
        draft = self.create_review_request_draft(review_request)
        attachment2 = self.create_file_attachment(
            review_request, draft=draft,
            attachment_history=attachment1.attachment_history)

        self.client.force_login(self.user_owner)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_diff_id': attachment1.pk,
                    'file_attachment_id': attachment2.pk,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=False,
            user_draft_exists=False,
            viewing_user_draft=False)

    def test_draft_file_attachment_diff_as_regular_user_with_view_draft(
        self,
    ) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as a
        regular user
        """
        review_request = self.create_review_request(publish=True)
        attachment1 = self.create_file_attachment(review_request)
        draft = self.create_review_request_draft(review_request)
        attachment2 = self.create_file_attachment(
            review_request, draft=draft,
            attachment_history=attachment1.attachment_history)

        self.client.force_login(self.user_regular)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_diff_id': attachment1.pk,
                    'file_attachment_id': attachment2.pk,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 404)

    def test_draft_file_attachment_diff_as_admin_with_view_draft(self) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as an
        admin
        """
        review_request = self.create_review_request(publish=True)
        attachment1 = self.create_file_attachment(review_request)
        draft = self.create_review_request_draft(review_request)
        attachment2 = self.create_file_attachment(
            review_request, draft=draft,
            attachment_history=attachment1.attachment_history)

        self.client.force_login(self.user_admin)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_diff_id': attachment1.pk,
                    'file_attachment_id': attachment2.pk,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=True,
            user_draft_exists=True,
            viewing_user_draft=True)

    def test_draft_file_attachment_diff_as_privileged_with_view_draft(
        self,
    ) -> None:
        """Testing ReviewFileAttachmentView with a draft attachment as a
        privileged user
        """
        review_request = self.create_review_request(publish=True)
        attachment1 = self.create_file_attachment(review_request)
        draft = self.create_review_request_draft(review_request)
        attachment2 = self.create_file_attachment(
            review_request, draft=draft,
            attachment_history=attachment1.attachment_history)

        self.client.force_login(self.user_privileged)
        rsp = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_diff_id': attachment1.pk,
                    'file_attachment_id': attachment2.pk,
                }) + '?view-draft=1')

        self.assertEqual(rsp.status_code, 200)
        self._test_result_context(
            context=cast(ReviewRequestContext, rsp.context),
            draft=draft,
            review_request_details=draft,
            mutable_by_user=True,
            force_view_user_draft=True,
            user_draft_exists=True,
            viewing_user_draft=True)

    def _test_result_context(
        self,
        *,
        context: ReviewRequestContext,
        draft: Optional[ReviewRequestDraft],
        review_request_details: Union[ReviewRequest, ReviewRequestDraft],
        mutable_by_user: bool,
        force_view_user_draft: bool,
        user_draft_exists: bool,
        viewing_user_draft: bool,
    ) -> None:
        """Do assertions for the result context.

        Args:
            context (reviewboard.reviews.context.ReviewRequestContext):
                The rendering context for the review request page.

            draft (reviewboard.reviews.models.ReviewRequestDraft):
                The draft that should be set in the context. This may be None.

            review_request_details (reviewboard.reviews.models.ReviewRequest or
                                    reviewboard.reviews.models.
                                    ReviewRequestDraft):
                The object that should be used for showing the review request
                data.

            mutable_by_user (bool):
                Whether the review request should be mutable by the current
                user.

            force_view_user_draft (bool):
                Whether the user is forced to view a draft that is owned by
                another user (such as an admin viewing an unpublished review
                request).

            user_draft_exists (bool):
                Whether a draft exists that is owned by another user.

            viewing_user_draft (bool):
                Whether the user is viewing a draft that is owned by another
                user.
        """
        self.assertEqual(context['draft'], draft)
        self.assertEqual(context['review_request_details'],
                         review_request_details)
        self.assertEqual(context['mutable_by_user'],
                         mutable_by_user)
        self.assertEqual(context['force_view_user_draft'],
                         force_view_user_draft)
        self.assertEqual(context['user_draft_exists'],
                         user_draft_exists)
        self.assertEqual(context['viewing_user_draft'],
                         viewing_user_draft)
