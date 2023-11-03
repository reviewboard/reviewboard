"""Unit tests for reviewboard.reviews.views.BatchOperationView."""

import json
from typing import List

import kgb
from django.contrib.auth.models import Permission, User
from django.core import mail
from django.db.models import Q
from django.http.response import HttpResponse
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import (LocalSiteProfile,
                                         Profile,
                                         ReviewRequestVisit)
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.notifications.models import WebHookTarget
from reviewboard.notifications.tests.mixins import EmailTestHelper
from reviewboard.reviews.models import (Group,
                                        Review,
                                        ReviewRequest,
                                        ReviewRequestDraft)
from reviewboard.scmtools.models import Repository
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class BatchOperationViewTests(kgb.SpyAgency, EmailTestHelper, TestCase):
    """Unit tests for reviewboard.reviews.views.BatchOperationView."""

    fixtures = ['test_users']
    email_siteconfig_settings = {
        'mail_send_review_mail': True,
        'mail_default_from': 'noreply@example.com',
    }

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()
        self.url = local_site_reverse('batch-operation')
        self.local_site_url = local_site_reverse(
            'batch-operation', local_site_name=self.local_site_name)

    def test_invalid(self) -> None:
        """Testing BatchOperationView with invalid data"""
        self.client.login(username='doc', password='doc')

        response = self.client.post(self.url, data={})
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'Batch data was not found.',
        })

        response = self.client.post(self.url, data={
            'batch': 'aoeu',
        })
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'Could not parse batch data: Expecting value: line '
                     '1 column 1 (char 0).',
        })

        response = self.client.post(self.url, data={
            'batch': json.dumps({}),
        })
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'Unknown batch operation "None".',
        })

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'unknown',
            }),
        })
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'Unknown batch operation "unknown".',
        })

    def test_archive(self) -> None:
        """Testing BatchOperationView archive op"""
        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(3, public=True)

        # 11 queries:
        #
        # 1-7. Review request list queries
        #   8. Try to fetch first review request visit
        #   9. Create first review request visit
        #  10. Try to fetch second review request visit
        #  11. Create second review request visit
        queries = self._get_review_request_list_queries(user, [rr1, rr2]) + [
            {
                'model': ReviewRequestVisit,
                'select_for_update': True,
                'where': Q(user=user, review_request=rr1),
            },
            {
                'model': ReviewRequestVisit,
                'type': 'INSERT',
            },
            {
                'model': ReviewRequestVisit,
                'select_for_update': True,
                'where': Q(user=user, review_request=rr2),
            },
            {
                'model': ReviewRequestVisit,
                'type': 'INSERT',
            },
        ]

        with self.assertQueries(queries, num_statements=19):
            response = self.client.post(self.url, data={
                'batch': json.dumps({
                    'op': 'archive',
                    'review_requests': [rr1.pk, rr2.pk],
                }),
            })
        self.assertEqual(response.status_code, 200)

        self.assertVisibility(rr1, 'doc', ReviewRequestVisit.ARCHIVED)
        self.assertVisibility(rr2, 'doc', ReviewRequestVisit.ARCHIVED)
        self.assertFalse(
            ReviewRequestVisit.objects.filter(
                review_request=rr3, user__username='doc')
            .exists())

    def test_archive_invalid(self) -> None:
        """Testing BatchOperationView archive op with invalid review
        requests
        """
        self.client.login(username='doc', password='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(3, public=True)

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'archive',
                'review_requests': [rr1.pk, rr2.pk, 45],
            }),
        })
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'The following review requests are not valid: [45].',
        })

    @add_fixtures(['test_site'])
    def test_archive_local_site(self) -> None:
        """Testing BatchOperationView archive op in a local site"""
        self.client.login(username='doc', password='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(
            3, public=True, with_local_site=True)

        response = self.client.post(self.local_site_url, data={
            'batch': json.dumps({
                'op': 'archive',
                'review_requests': [rr1.display_id, rr2.display_id],
            }),
        })
        self.assertEqual(response.status_code, 200)

        self.assertVisibility(rr1, 'doc', ReviewRequestVisit.ARCHIVED)
        self.assertVisibility(rr2, 'doc', ReviewRequestVisit.ARCHIVED)
        self.assertFalse(
            ReviewRequestVisit.objects.filter(
                review_request=rr3, user__username='doc')
            .exists())

    @add_fixtures(['test_site'])
    def test_archive_local_site_invalid_ID(self) -> None:
        """Testing BatchOperationView archive op in a local site with
        invalid local_ids
        """
        self.client.login(username='doc', password='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(
            3, public=True, with_local_site=True)

        response = self.client.post(self.local_site_url, data={
            'batch': json.dumps({
                'op': 'archive',
                'review_requests': [rr1.display_id,
                                    rr2.display_id,
                                    rr3.pk],
            }),
        })
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'The following review requests are not valid for the '
                     'local site: [3].',
        })

    @add_fixtures(['test_site'])
    def test_archive_local_site_no_access(self) -> None:
        """Testing BatchOperationView archive op in a local site with
        no access
        """
        self.client.login(username='grumpy', password='grumpy')

        rr1, rr2, rr3 = self.create_many_review_requests(
            3, public=True, with_local_site=True)

        response = self.client.post(self.local_site_url, data={
            'batch': json.dumps({
                'op': 'archive',
                'review_requests': [rr1.display_id,
                                    rr2.display_id],
            }),
        })
        self.assertEqual(response.status_code, 403)

    def test_mute(self) -> None:
        """Testing BatchOperationView mute op"""
        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(3, public=True)

        # 11 queries:
        #
        #  1-7. Review request list queries
        #    8. Try to fetch first review request visit
        #    9. Create first review request visit
        #   10. Try to fetch second review request visit
        #   11. Create second review request visit
        queries = self._get_review_request_list_queries(user, [rr1, rr2]) + [
            {
                'model': ReviewRequestVisit,
                'select_for_update': True,
                'where': Q(user=user, review_request=rr1),
            },
            {
                'model': ReviewRequestVisit,
                'type': 'INSERT',
            },
            {
                'model': ReviewRequestVisit,
                'select_for_update': True,
                'where': Q(user=user, review_request=rr2),
            },
            {
                'model': ReviewRequestVisit,
                'type': 'INSERT',
            },
        ]

        with self.assertQueries(queries, num_statements=19):
            response = self.client.post(self.url, data={
                'batch': json.dumps({
                    'op': 'mute',
                    'review_requests': [rr1.pk, rr2.pk],
                }),
            })

        self.assertEqual(response.status_code, 200)

        self.assertVisibility(rr1, 'doc', ReviewRequestVisit.MUTED)
        self.assertVisibility(rr2, 'doc', ReviewRequestVisit.MUTED)
        self.assertFalse(
            ReviewRequestVisit.objects.filter(
                review_request=rr3, user__username='doc')
            .exists())

    def test_mute_invalid(self) -> None:
        """Testing BatchOperationView mute op with invalid review requests"""
        self.client.login(username='doc', password='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(3, public=True)

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'mute',
                'review_requests': [rr1.pk, rr2.pk, 45],
            }),
        })
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'The following review requests are not valid: [45].',
        })

    @add_fixtures(['test_site'])
    def test_mute_local_site(self) -> None:
        """Testing BatchOperationView mute op in a local site"""
        self.client.login(username='doc', password='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(
            3, public=True, with_local_site=True)

        response = self.client.post(self.local_site_url, data={
            'batch': json.dumps({
                'op': 'mute',
                'review_requests': [rr1.display_id, rr2.display_id],
            }),
        })
        self.assertEqual(response.status_code, 200)

        self.assertVisibility(rr1, 'doc', ReviewRequestVisit.MUTED)
        self.assertVisibility(rr2, 'doc', ReviewRequestVisit.MUTED)
        self.assertFalse(
            ReviewRequestVisit.objects.filter(
                review_request=rr3, user__username='doc')
            .exists())

    @add_fixtures(['test_site'])
    def test_mute_local_site_invalid_ID(self) -> None:
        """Testing BatchOperationView mute op in a local site with invalid
        local_ids
        """
        self.client.login(username='doc', password='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(
            3, public=True, with_local_site=True)

        response = self.client.post(self.local_site_url, data={
            'batch': json.dumps({
                'op': 'mute',
                'review_requests': [rr1.display_id, rr2.display_id, rr3.pk],
            }),
        })
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'The following review requests are not valid for the '
                     'local site: [3].',
        })

    @add_fixtures(['test_site'])
    def test_mute_local_site_no_access(self) -> None:
        """Testing BatchOperationView mute op in a local site with no access"""
        self.client.login(username='grumpy', password='grumpy')

        rr1, rr2, rr3 = self.create_many_review_requests(
            3, public=True, with_local_site=True)

        response = self.client.post(self.local_site_url, data={
            'batch': json.dumps({
                'op': 'mute',
                'review_requests': [rr1.display_id, rr2.display_id],
            }),
        })
        self.assertEqual(response.status_code, 403)

    def test_unarchive(self) -> None:
        """Testing BatchOperationView unarchive op"""
        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(3, public=True)
        ReviewRequestVisit.objects.update_visibility(
            rr1, user, ReviewRequestVisit.ARCHIVED)
        ReviewRequestVisit.objects.update_visibility(
            rr2, user, ReviewRequestVisit.MUTED)
        ReviewRequestVisit.objects.update_visibility(
            rr3, user, ReviewRequestVisit.ARCHIVED)

        # 11 queries:
        #
        # 1-7. Review request list queries
        #   8. Try to fetch first review request visit
        #   9. Create first review request visit
        #  10. Try to fetch second review request visit
        #  11. Create second review request visit
        queries = self._get_review_request_list_queries(user, [rr1, rr2]) + [
            {
                'model': ReviewRequestVisit,
                'select_for_update': True,
                'where': Q(user=user, review_request=rr1),
            },
            {
                'model': ReviewRequestVisit,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
            {
                'model': ReviewRequestVisit,
                'select_for_update': True,
                'where': Q(user=user, review_request=rr2),
            },
            {
                'model': ReviewRequestVisit,
                'type': 'UPDATE',
                'where': Q(pk=2),
            },
        ]

        with self.assertQueries(queries, num_statements=15):
            response = self.client.post(self.url, data={
                'batch': json.dumps({
                    'op': 'unarchive',
                    'review_requests': [rr1.pk, rr2.pk],
                }),
            })
        self.assertEqual(response.status_code, 200)

        self.assertVisibility(rr1, 'doc', ReviewRequestVisit.VISIBLE)
        self.assertVisibility(rr2, 'doc', ReviewRequestVisit.VISIBLE)
        self.assertVisibility(rr3, 'doc', ReviewRequestVisit.ARCHIVED)

    def test_close(self) -> None:
        """Testing BatchOperationView close op"""
        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        site_profile = user.get_site_profile(None)

        rr1, rr2, rr3 = self.create_many_review_requests(3, public=True)

        # 39 queries:
        #
        #   1-7. Review request list queries
        #     8. Fetch user
        #     9. Fetch user
        # 10-25. Close first review request
        # 26-39. Close second review request
        queries = (  # noqa
            self._get_review_request_list_queries(user, [rr1, rr2]) +
            [
                {
                    'model': User,
                    'where': Q(id=user.pk),
                },
                {
                    'model': User,
                    'where': Q(id=user.pk),
                },
            ] +
            self._get_review_request_close_queries(
                user, profile, site_profile, rr1) +
            self._get_review_request_close_queries(
                user, profile, site_profile, rr2)
        )

        # We can't currently use this because QuerySet.update() is adding a
        # subquery that we can't test against.
        # with self.assertQueries(queries, num_statements=39):
        with self.assertNumQueries(39):
            response = self.client.post(self.url, data={
                'batch': json.dumps({
                    'op': 'close',
                    'review_requests': [rr1.pk, rr2.pk],
                }),
            })

        self.assertEqual(response.status_code, 200)

        rr1.refresh_from_db()
        rr2.refresh_from_db()
        rr3.refresh_from_db()

        self.assertEqual(rr1.status, ReviewRequest.SUBMITTED)
        self.assertEqual(rr2.status, ReviewRequest.SUBMITTED)
        self.assertEqual(rr3.status, ReviewRequest.PENDING_REVIEW)

    def test_close_invalid(self) -> None:
        """Testing BatchOperationView close op with invalid review requests"""
        self.client.login(username='doc', password='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(3, public=True)

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'close',
                'review_requests': [rr1.pk, rr2.pk, 45],
            }),
        })
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'The following review requests are not valid: [45].',
        })

    def test_close_permissions(self) -> None:
        """Testing BatchOperationView close op with non-owner user"""
        self.client.login(username='grumpy', password='grumpy')

        rr1, rr2, rr3 = self.create_many_review_requests(3, public=True)

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'close',
                'review_requests': [rr1.pk, rr2.pk],
            }),
        })
        self.assertResponse(response, 403, {
            'stat': 'fail',
            'error': 'User does not have permission to close review '
                     'request 1.',
        })

    @add_fixtures(['test_site'])
    def test_close_local_site(self) -> None:
        """Testing BatchOperationView close op in a local site"""
        self.client.login(username='doc', password='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(
            3, public=True, with_local_site=True)

        response = self.client.post(self.local_site_url, data={
            'batch': json.dumps({
                'op': 'close',
                'review_requests': [rr1.display_id, rr2.display_id],
            }),
        })
        self.assertEqual(response.status_code, 200)

        rr1.refresh_from_db()
        rr2.refresh_from_db()
        rr3.refresh_from_db()

        self.assertEqual(rr1.status, ReviewRequest.SUBMITTED)
        self.assertEqual(rr2.status, ReviewRequest.SUBMITTED)
        self.assertEqual(rr3.status, ReviewRequest.PENDING_REVIEW)

    @add_fixtures(['test_site'])
    def test_close_local_site_invalid_ID(self) -> None:
        """Testing BatchOperationView close op in a local site with
        invalid local_ids
        """
        self.client.login(username='doc', password='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(
            3, public=True, with_local_site=True)

        response = self.client.post(self.local_site_url, data={
            'batch': json.dumps({
                'op': 'close',
                'review_requests': [rr1.display_id,
                                    rr2.display_id,
                                    rr3.pk],
            }),
        })
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'The following review requests are not valid for the '
                     'local site: [3].'
        })

        rr1.refresh_from_db()
        rr2.refresh_from_db()
        rr3.refresh_from_db()

        self.assertEqual(rr1.status, ReviewRequest.PENDING_REVIEW)
        self.assertEqual(rr2.status, ReviewRequest.PENDING_REVIEW)
        self.assertEqual(rr3.status, ReviewRequest.PENDING_REVIEW)

    def test_discard(self) -> None:
        """Testing BatchOperationView discard op"""
        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        site_profile = user.get_site_profile(None)

        rr1, rr2, rr3 = self.create_many_review_requests(3, public=True)

        # 39 queries:
        #
        #   1-7. Review request list queries
        #     8. Fetch user
        #     9. Fetch user
        # 10-25. Close first review request
        # 26-39. Close second review request
        queries = (  # noqa
            self._get_review_request_list_queries(user, [rr1, rr2]) +
            [
                {
                    'model': User,
                    'where': Q(id=user.pk),
                },
                {
                    'model': User,
                    'where': Q(id=user.pk),
                },
            ] +
            self._get_review_request_close_queries(
                user, profile, site_profile, rr1) +
            self._get_review_request_close_queries(
                user, profile, site_profile, rr2)
        )

        # We can't currently use this because QuerySet.update() is adding a
        # subquery that we can't test against.
        # with self.assertQueries(queries, num_statements=39):
        with self.assertNumQueries(39):
            response = self.client.post(self.url, data={
                'batch': json.dumps({
                    'op': 'discard',
                    'review_requests': [rr1.pk, rr2.pk],
                }),
            })

        self.assertEqual(response.status_code, 200)

        rr1.refresh_from_db()
        rr2.refresh_from_db()
        rr3.refresh_from_db()

        self.assertEqual(rr1.status, ReviewRequest.DISCARDED)
        self.assertEqual(rr2.status, ReviewRequest.DISCARDED)
        self.assertEqual(rr3.status, ReviewRequest.PENDING_REVIEW)

    def test_discard_invalid(self) -> None:
        """Testing BatchOperationView discard op with invalid review
        requests
        """
        self.client.login(username='doc', password='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(3, public=True)

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'discard',
                'review_requests': [rr1.pk, rr2.pk, 45],
            }),
        })
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'The following review requests are not valid: [45].',
        })

    def test_discard_permissions(self) -> None:
        """Testing BatchOperationView discard op with non-owner user"""
        self.client.login(username='grumpy', password='grumpy')

        rr1, rr2, rr3 = self.create_many_review_requests(3, public=True)

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'discard',
                'review_requests': [rr1.pk, rr2.pk],
            }),
        })
        self.assertResponse(response, 403, {
            'stat': 'fail',
            'error': 'User does not have permission to close review '
                     'request 1.',
        })

    @add_fixtures(['test_site'])
    def test_discard_local_site(self) -> None:
        """Testing BatchOperationView discard op in a local site"""
        self.client.login(username='doc', password='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(
            3, public=True, with_local_site=True)

        response = self.client.post(self.local_site_url, data={
            'batch': json.dumps({
                'op': 'discard',
                'review_requests': [rr1.display_id,
                                    rr2.display_id],
            }),
        })
        self.assertEqual(response.status_code, 200)

        rr1.refresh_from_db()
        rr2.refresh_from_db()
        rr3.refresh_from_db()

        self.assertEqual(rr1.status, ReviewRequest.DISCARDED)
        self.assertEqual(rr2.status, ReviewRequest.DISCARDED)
        self.assertEqual(rr3.status, ReviewRequest.PENDING_REVIEW)

    @add_fixtures(['test_site'])
    def test_discard_local_site_invalid_ID(self) -> None:
        """Testing BatchOperationView discard op in a local site with
        invalid local_ids
        """
        self.client.login(username='doc', password='doc')

        rr1, rr2, rr3 = self.create_many_review_requests(
            3, public=True, with_local_site=True)

        response = self.client.post(self.local_site_url, data={
            'batch': json.dumps({
                'op': 'discard',
                'review_requests': [rr1.display_id,
                                    rr2.display_id,
                                    rr3.pk],
            }),
        })
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'The following review requests are not valid for the '
                     'local site: [3].',
        })

        rr1.refresh_from_db()
        rr2.refresh_from_db()
        rr3.refresh_from_db()

        self.assertEqual(rr1.status, ReviewRequest.PENDING_REVIEW)
        self.assertEqual(rr2.status, ReviewRequest.PENDING_REVIEW)
        self.assertEqual(rr3.status, ReviewRequest.PENDING_REVIEW)

    def test_publish(self) -> None:
        """Testing BatchOperationView publish op with multiple objects"""
        self.client.login(username='doc', password='doc')
        grumpy = User.objects.get(username='grumpy')

        rr1 = self.create_review_request(publish=True, target_people=[grumpy])
        rr2 = self.create_review_request(target_people=[grumpy])
        self.create_review_request_draft(rr2)
        r1 = self.create_review(rr1, user='doc')
        r2 = self.create_review(rr1, user='doc')

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [rr2.pk],
                'reviews': [r1.pk, r2.pk],
            }),
        })
        self.assertEqual(response.status_code, 200)

        rr2.refresh_from_db()
        r1.refresh_from_db()
        r2.refresh_from_db()

        self.assertTrue(rr2.public)
        self.assertTrue(r1.public)
        self.assertTrue(r2.public)

    def test_publish_with_draft(self) -> None:
        """Testing BatchOperationView publish op with review request draft
        update
        """
        self.client.login(username='doc', password='doc')
        grumpy = User.objects.get(username='grumpy')

        rr = self.create_review_request(publish=True, target_people=[grumpy])
        draft = self.create_review_request_draft(rr)
        draft.summary = 'Updated Summary'
        draft.save(update_fields=('summary',))

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [rr.pk],
            }),
        })
        self.assertEqual(response.status_code, 200)

        rr.refresh_from_db()

        self.assertTrue(rr.public)
        self.assertEqual(rr.summary, 'Updated Summary')

    def test_publish_other_draft_as_admin(self) -> None:
        """Testing BatchOperationView publish op with an admin publishing
        a draft on another user's review request
        """
        self.client.login(username='admin', password='admin')
        grumpy = User.objects.get(username='grumpy')

        rr = self.create_review_request(publish=True,
                                        target_people=[grumpy])
        draft = self.create_review_request_draft(rr)
        draft.summary = 'Updated Summary'
        draft.save(update_fields=('summary',))

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [rr.pk],
            }),
        })
        self.assertEqual(response.status_code, 200)

        rr.refresh_from_db()

        self.assertTrue(rr.public)
        self.assertEqual(rr.summary, 'Updated Summary')

    def test_publish_permissions(self) -> None:
        """Testing BatchOperationView publish op with non-owner user"""
        self.client.login(username='grumpy', password='grumpy')
        grumpy = User.objects.get(username='grumpy')

        rr = self.create_review_request(publish=True, target_people=[grumpy])
        draft = self.create_review_request_draft(rr)
        draft.summary = 'Updated Summary'
        draft.save(update_fields=('summary',))

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [rr.pk],
            }),
        })
        self.assertResponse(response, 403, {
            'stat': 'fail',
            'error': 'User does not have permission to publish review '
                     'request 1.',
        })

    def test_publish_with_invalid_review_requests(self) -> None:
        """Testing BatchOperationView publish op with invalid review requests
        """
        self.client.login(username='doc', password='doc')
        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [45],
            })
        })
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'The following review requests are not valid: [45].',
        })

    def test_publish_with_invalid_reviews(self) -> None:
        """Testing BatchOperationView publish op with invalid reviews"""
        self.client.login(username='doc', password='doc')

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [],
                'reviews': [23],
            })
        })
        self.assertResponse(response, 400, {
            'stat': 'fail',
            'error': 'The following reviews are not valid: [23].',
        })

    def test_publish_with_publish_error(self) -> None:
        """Testing BatchOperationView publish op with publish error"""
        self.client.login(username='doc', password='doc')

        rr = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(rr)
        draft.summary = 'Updated Summary'
        draft.save(update_fields=('summary',))

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [rr.pk],
            }),
        })
        self.assertResponse(response, 500, {
            'stat': 'fail',
            'error': 'Failed to publish review request 1: '
                     'Error publishing: There must be at least one '
                     'reviewer before this review request can be '
                     'published.',
            'review_requests_published': 0,
            'review_requests_not_published': 1,
            'reviews_published': 0,
            'reviews_not_published': 0,
        })

        rr.refresh_from_db()
        self.assertEqual(rr.summary, 'Test Summary')

        draft = rr.get_draft()
        self.assertIsNotNone(draft)
        self.assertEqual(draft.summary, 'Updated Summary')

    def test_publish_review_requests_mixed_result(self) -> None:
        """Testing BatchOperationView publish op with review requests and mixed
        result
        """
        self.client.login(username='doc', password='doc')
        grumpy = User.objects.get(username='grumpy')

        rr1 = self.create_review_request(publish=True, target_people=[grumpy])
        draft = self.create_review_request_draft(rr1)
        draft.summary = 'Updated Summary'
        draft.save(update_fields=('summary',))

        rr2 = self.create_review_request(publish=True)
        draft = self.create_review_request_draft(rr2)
        draft.summary = 'Updated Summary'
        draft.save(update_fields=('summary',))

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [rr1.pk, rr2.pk],
            }),
        })
        self.assertResponse(response, 500, {
            'stat': 'mixed',
            'error': 'Failed to publish review request 2: Error publishing: '
                     'There must be at least one reviewer before this review '
                     'request can be published.',
            'review_requests_not_published': 1,
            'review_requests_published': 1,
            'reviews_not_published': 0,
            'reviews_published': 0,
        })

    def test_publish_multiple_mixed_result(self) -> None:
        """Testing BatchOperationView publish op with multiple items and mixed
        result
        """
        self.client.login(username='doc', password='doc')
        grumpy = User.objects.get(username='grumpy')

        rr1 = self.create_review_request(publish=True, target_people=[grumpy])
        draft = self.create_review_request_draft(rr1)
        draft.summary = 'Updated Summary'
        draft.save(update_fields=('summary',))

        rr2 = self.create_review_request(publish=True, target_people=[grumpy])
        draft = self.create_review_request_draft(rr2)
        draft.summary = 'Updated Summary'
        draft.save(update_fields=('summary',))

        review1 = self.create_review(rr1, user='doc')
        review2 = self.create_review(rr2, user='doc')

        self.spy_on(
            Review.publish,
            owner=Review,
            op=kgb.SpyOpMatchInOrder([
                {
                },
                {
                    'op': kgb.SpyOpRaise(Exception('Cannot publish')),
                },
            ]))

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [rr1.pk, rr2.pk],
                'reviews': [review1.pk, review2.pk],
            }),
        })
        self.assertResponse(response, 500, {
            'stat': 'mixed',
            'error': 'Failed to publish review 2: Cannot publish',
            'review_requests_not_published': 0,
            'review_requests_published': 2,
            'reviews_not_published': 1,
            'reviews_published': 1,
        })

    def test_publish_trivial(self) -> None:
        """Testing BatchOperationView publish op with trivial flag"""
        self.client.login(username='doc', password='doc')
        grumpy = User.objects.get(username='grumpy')

        rr1 = self.create_review_request(publish=True, target_people=[grumpy])
        rr2 = self.create_review_request(target_people=[grumpy])
        self.create_review_request_draft(rr2)
        r1 = self.create_review(rr1, user='doc')
        r2 = self.create_review(rr1, user='doc')

        mail.outbox = []

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [rr2.pk],
                'reviews': [r1.pk, r2.pk],
                'trivial': True,
            }),
        })
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 0)

    def test_publish_notification_with_single_review_request(self) -> None:
        """Testing BatchOperationView publish op notification with a single
        review request
        """
        self.client.login(username='doc', password='doc')
        grumpy = User.objects.get(username='grumpy')

        rr1 = self.create_review_request(target_people=[grumpy])
        self.create_review_request_draft(rr1)

        mail.outbox = []

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [rr1.pk],
            }),
        })
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         'Review Request 1: Test Summary')

    def test_publish_review_request_and_review(self) -> None:
        """Testing BatchOperationView publish op with a new review request and
        review
        """
        self.client.login(username='doc', password='doc')
        grumpy = User.objects.get(username='grumpy')

        rr1 = self.create_review_request(target_people=[grumpy])
        self.create_review_request_draft(rr1)
        r1 = self.create_review(rr1, user='doc')

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [rr1.pk],
                'reviews': [r1.pk],
            }),
        })
        self.assertEqual(response.status_code, 200)

        rr1.refresh_from_db()
        r1.refresh_from_db()

        self.assertTrue(rr1.public)
        self.assertTrue(r1.public)

    def test_publish_review_on_unpublished_review_request(self) -> None:
        """Testing BatchOperationView publish op with a review on an
        unpublished review request
        """
        self.client.login(username='doc', password='doc')
        grumpy = User.objects.get(username='grumpy')

        rr1 = self.create_review_request(target_people=[grumpy])
        self.create_review_request_draft(rr1)
        r1 = self.create_review(rr1, user='doc')

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [],
                'reviews': [r1.pk],
            }),
        })
        self.assertResponse(response, 403, {
            'stat': 'fail',
            'error': 'This review cannot be published until the review '
                     'request is published.',
        })

        rr1.refresh_from_db()
        r1.refresh_from_db()

        self.assertFalse(rr1.public)
        self.assertFalse(r1.public)

    def test_publish_notifications(self) -> None:
        """Testing BatchOperationView publish op with multiple published items
        """
        self.client.login(username='doc', password='doc')
        grumpy = User.objects.get(username='grumpy')

        rr1, rr2, rr3 = self.create_many_review_requests(
            3, public=True, target_people=[grumpy])
        rr1.email_message_id = 'fake message id'
        rr1.save(update_fields=('email_message_id',))
        draft1 = self.create_review_request_draft(rr1)
        draft1.summary = 'Updated Summary'
        draft1.save(update_fields=('summary',))
        draft2 = self.create_review_request_draft(rr2)
        draft2.summary = 'Updated Summary 2'
        draft2.save(update_fields=('summary',))

        r1 = self.create_review(rr1, user='doc')
        r2 = self.create_review(rr2, user='doc')
        r3 = self.create_review(rr3, user='doc')

        mail.outbox = []

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [rr1.pk, rr2.pk],
                'reviews': [r1.pk, r2.pk, r3.pk],
            }),
        })
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(mail.outbox[0].subject,
                         'Re: Review Request 1: Updated Summary')
        self.assertEqual(mail.outbox[1].subject,
                         'Review Request 2: Updated Summary 2')
        self.assertEqual(mail.outbox[2].subject,
                         'Review Request 3: Test Summary 3')

    def test_publish_archive(self) -> None:
        """Testing BatchOperationView publish op with archive after publish"""
        self.client.login(username='doc', password='doc')
        grumpy = User.objects.get(username='grumpy')

        rr1 = self.create_review_request(publish=True, target_people=[grumpy])
        rr2 = self.create_review_request(target_people=[grumpy])
        self.create_review_request_draft(rr2)
        r1 = self.create_review(rr1, user='doc')
        r2 = self.create_review(rr1, user='doc')

        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [rr2.pk],
                'reviews': [r1.pk, r2.pk],
                'archive': True,
            }),
        })
        self.assertEqual(response.status_code, 200)

        self.assertVisibility(rr1, 'doc', ReviewRequestVisit.ARCHIVED)
        self.assertVisibility(rr2, 'doc', ReviewRequestVisit.ARCHIVED)

    @add_fixtures(['test_scmtools'])
    def test_publish_with_acls(self) -> None:
        """Testing BatchOperationView when publishing a review on a review
        request that has multiple groups with ACLs
        """
        # Review Board 6.0 had a bug where the way the batch endpoint was
        # fetching reviews could return duplicates, which would then fail
        # length comparisons. This test case is an example of something that
        # triggered that bug before it was fixed.
        doc = User.objects.get(username='doc')
        grumpy = User.objects.get(username='grumpy')

        group1 = self.create_review_group(invite_only=True)
        group1.users.add(doc, grumpy)

        group2 = self.create_review_group(invite_only=True)
        group2.users.add(doc, grumpy)

        repository = self.create_repository(public=False)
        repository.review_groups.set([group1])

        review_request = self.create_review_request(
            publish=True,
            repository=repository,
            target_groups=[group1, group2])
        review = self.create_review(review_request, user='doc')

        self.client.login(username='doc', password='doc')
        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [],
                'reviews': [review.pk],
            }),
        })
        self.assertEqual(response.status_code, 200)

        reply = self.create_reply(review, user='grumpy')
        self.client.login(username='grumpy', password='grumpy')
        response = self.client.post(self.url, data={
            'batch': json.dumps({
                'op': 'publish',
                'review_requests': [],
                'reviews': [reply.pk],
            }),
        })
        self.assertEqual(response.status_code, 200)

    def assertVisibility(
        self,
        review_request: ReviewRequest,
        user: str,
        visibility: str,
    ) -> None:
        """Assert a specific review request visibility state.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request to check.

            user (str):
                The username of the user to check.

            visibility (str):
                The expected visibility state.
        """
        visit = ReviewRequestVisit.objects.get(
            review_request=review_request,
            user__username=user)
        self.assertEqual(visit.visibility, visibility)

    def assertResponse(
        self,
        response: HttpResponse,
        status_code: int,
        data: dict,
    ) -> None:
        """Assert that a response matches the expected result.

        Args:
            response (django.http.HttpResponse):
                The response from the test client.

            status_code (int):
                The expected HTTP status.

            data (dict):
                The expected data contained in the response after decoding
                JSON.
        """
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(json.loads(response.content), data)

    def _get_review_request_list_queries(
        self,
        user: User,
        review_requests: List[ReviewRequest],
    ) -> List[dict]:
        """Return queries for the initial review requests list fetch.

        Args:
            user (django.contrib.auth.models.User):
                The user making the request.

            review_requests (list of reviewboard.reviews.models.ReviewRequest):
                The review requests being passed to the batch endpoint.

        Returns:
            list:
            A list of query info appropriate for assertQueries.
        """
        review_request_pks = [rr.pk for rr in review_requests]

        # 7 queries:
        #
        # 1. Fetch user
        # 2. Fetch user profile
        # 3. Fetch user's accessible repositories
        # 4. Fetch user's auth permissions
        # 5. Fetch user's group auth permissions
        # 6. Fetch user's accessible groups
        # 7. Get review requests
        return [
            {
                'model': User,
                'where': Q(pk=user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
            {
                'model': Repository,
                'values_select': ('pk',),
                'num_joins': 4,
                'tables': {
                    'scmtools_repository_users',
                    'scmtools_repository',
                    'reviews_group_users',
                    'scmtools_repository_review_groups',
                    'reviews_group',
                },
                'where': (
                    (Q(public=True) |
                     Q(users__pk=user.pk) |
                     Q(review_groups__users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 4,
                'tables': {
                    'auth_permission',
                    'auth_group',
                    'auth_user_groups',
                    'auth_group_permissions',
                    'django_content_type',
                },
                'where': Q(group__user=user),
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (
                    (Q(invite_only=False) |
                     Q(users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': ReviewRequest,
                'distinct': True,
                'num_joins': 3,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest_target_people',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest',
                },
                'where': (
                    Q(submitter__is_active=True) &
                    Q(local_site=None) &
                    Q(pk__in=review_request_pks) &
                    Q(Q(submitter=user) |
                      Q(Q(Q(repository=None) | Q(repository__in=[])) &
                        Q(Q(target_people=user) |
                          Q(target_groups=None) |
                          Q(target_groups__in=[]))))
                ),
            },
        ]

    def _get_review_request_close_queries(
        self,
        user: User,
        profile: Profile,
        site_profile: LocalSiteProfile,
        review_request: ReviewRequest,
    ) -> List[dict]:
        """Return queries associated with closing a review request.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the close.

            profile (reviewboard.accounts.models.Profile):
                The user's profile.

            site_profile (reviewboard.accounts.models.LocalSiteProfile):
                The user's local site profile.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request being closed.

        Returns:
            list:
            A list of query info appropriate for assertQueries.
        """
        # 15 queries
        #
        #  1. Fetch review request draft
        #  2. Create ChangeDescription
        #  3. Link ChangeDescription
        #  4. Fetch user's Profile
        #  5. Fetch user's LocalSiteProfile
        #  6. Check review request status
        #  7. Update local site profile
        #  8. Refresh local site profile
        #  9. Fetch target groups
        # 10. Fetch target users
        # 11. Update group counters
        # 12. Update LocalSiteProfile counters
        # 13. Fetch ReviewRequestVisit
        # 14. Update ReviewRequestVisit
        # 15. Fetch WebHook targets
        return [
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': ChangeDescription,
                'type': 'INSERT',
            },
            {
                'model': ReviewRequest.changedescs.through,
                'type': 'INSERT',
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
            {
                'model': LocalSiteProfile,
                'where': Q(local_site=None, profile=profile, user=user),
            },
            {
                'model': ReviewRequest,
                'where': Q(pk=review_request.pk),
                'only_fields': {'status', 'public'},
            },
            {
                'model': LocalSiteProfile,
                'type': 'UPDATE',
                'where': Q(pk=site_profile.pk),
            },
            {
                'model': LocalSiteProfile,
                'limit': 1,
                'values_select': ('pending_outgoing_request_count',),
                'where': Q(pk=site_profile.pk),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest_target_groups',
                    'reviews_group',
                },
                'where': Q(review_requests__id=review_request.pk),
                'values_select': ('pk',),
            },
            {
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest_target_people',
                },
                'where': Q(directed_review_requests__id=review_request.pk),
                'values_select': ('pk',),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest_target_groups',
                    'reviews_group',
                },
                'type': 'UPDATE',
            },
            {
                'model': LocalSiteProfile,
                'type': 'UPDATE',
                'num_joins': 2,
                'tables': {
                    'accounts_profile',
                    'accounts_localsiteprofile',
                    'accounts_profile_starred_review_requests',
                },
            },
            {
                'model': ReviewRequestVisit,
                'where': Q(review_request=review_request),
            },
            {
                'model': ReviewRequest,
                'type': 'UPDATE',
                'where': Q(pk=review_request.pk),
            },
            {
                'model': WebHookTarget,
                'where': Q(Q(enabled=True, local_site=None) &
                           Q(Q(apply_to='A') | Q(apply_to='N'))),
            },
        ]
