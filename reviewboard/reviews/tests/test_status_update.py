"""Unit tests for reviewboard.reviews.models.status_update.StatusUpdate."""

from django.contrib.auth.models import AnonymousUser, Permission, User
from django.db.models import Q
from djblets.testing.decorators import add_fixtures

from reviewboard.integrations.models import IntegrationConfig
from reviewboard.reviews.models.base_comment import BaseComment
from reviewboard.reviews.models.review_request import fetch_issue_counts
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class StatusUpdateTests(TestCase):
    """Unit tests for reviewboard.reviews.models.base_comment.StatusUpdate."""

    fixtures = ['test_users', 'test_scmtools']

    def test_is_mutable_by_with_anonymous(self):
        """Testing StatusUpdate.is_mutable_by with anonymous user"""
        review_request = self.create_review_request()
        status_update = self.create_status_update(review_request)

        self.assertFalse(status_update.is_mutable_by(AnonymousUser()))

    def test_is_mutable_by_with_owner(self):
        """Testing StatusUpdate.is_mutable_by with owner"""
        review_request = self.create_review_request()
        status_update = self.create_status_update(review_request)

        self.assertTrue(status_update.is_mutable_by(status_update.user))

    def test_is_mutable_by_with_other_user(self):
        """Testing StatusUpdate.is_mutable_by with other user"""
        other_user = User.objects.create(username='other-user')
        review_request = self.create_review_request()
        status_update = self.create_status_update(review_request)

        self.assertFalse(status_update.is_mutable_by(other_user))

    def test_is_mutable_by_with_other_user_and_can_change_status_perm(self):
        """Testing StatusUpdate.is_mutable_by with other user with
        change_statusupdate permission
        """
        other_user = User.objects.create(username='other-user')
        other_user.user_permissions.add(
            Permission.objects.get(codename='change_statusupdate'))

        review_request = self.create_review_request()
        status_update = self.create_status_update(review_request)

        self.assertTrue(status_update.is_mutable_by(other_user))

    @add_fixtures(['test_site'])
    def test_is_mutable_by_with_other_user_with_perm_same_local_site(self):
        """Testing StatusUpdate.is_mutable_by with other user on same
        LocalSite with change_statusupdate permission
        """
        review_request = self.create_review_request(with_local_site=True)
        status_update = self.create_status_update(review_request)

        other_user = User.objects.create(username='other-user')

        site = review_request.local_site
        site.users.add(other_user)

        site_profile = other_user.get_site_profile(site)
        site_profile.permissions = {
            'reviews.change_statusupdate': True,
        }
        site_profile.save(update_fields=('permissions',))

        self.assertTrue(status_update.is_mutable_by(other_user))

    def test_drop_open_issues_with_no_review(self):
        """Testing StatusUpdate.drop_open_issues with no associated Review"""
        review_request = self.create_review_request(publish=True)
        status_update = self.create_status_update(review_request, review=None)
        status_update.drop_open_issues()

    def test_drop_open_issues_multiple_issue_status(self):
        """Testing StatusUpdate.drop_open_issues with multiple issues
        statuses
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request, publish=True)

        self.create_diff_comment(review, filediff, issue_opened=True)
        self.create_diff_comment(review, filediff, issue_opened=True,
                                 issue_status=BaseComment.RESOLVED)
        self.create_diff_comment(review, filediff, issue_opened=True,
                                 issue_status=BaseComment.DROPPED)

        status_update = self.create_status_update(review_request,
                                                  review=review)

        status_update.drop_open_issues()

        comments = list(review.comments.all().order_by('id'))
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0].issue_status, BaseComment.DROPPED)
        self.assertEqual(comments[1].issue_status, BaseComment.RESOLVED)
        self.assertEqual(comments[2].issue_status, BaseComment.DROPPED)

    def test_drop_open_issues_updates_timestamps(self):
        """Testing StatusUpdate.drop_open_issues updates timestamps"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request, publish=True)
        open_comment = self.create_diff_comment(
            review, filediff, issue_opened=True)
        resolved_comment = self.create_diff_comment(
            review, filediff, issue_opened=True,
            issue_status=BaseComment.RESOLVED)
        status_update = self.create_status_update(review_request,
                                                  review=review)

        open_comment_timestamp = open_comment.timestamp
        resolved_comment_timestamp = resolved_comment.timestamp
        review_request_timestamp = \
            review_request.last_review_activity_timestamp

        status_update.drop_open_issues()

        comments = list(review.comments.all().order_by('id'))
        self.assertEqual(len(comments), 2)
        self.assertGreater(comments[0].timestamp, open_comment_timestamp)
        self.assertEqual(comments[1].timestamp, resolved_comment_timestamp)

        self.assertGreater(review_request.last_review_activity_timestamp,
                           review_request_timestamp)

    def test_drop_open_issues_updates_issue_counts(self):
        """Testing StatusUpdate.drop_open_issues updates issue counts"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request, publish=True)

        self.create_diff_comment(review, filediff, issue_opened=True)

        status_update = self.create_status_update(review_request,
                                                  review=review)

        issues = fetch_issue_counts(review_request)
        self.assertEqual(issues[BaseComment.OPEN], 1)
        self.assertEqual(issues[BaseComment.DROPPED], 0)
        self.assertEqual(issues[BaseComment.RESOLVED], 0)

        status_update.drop_open_issues()

        issues = fetch_issue_counts(review_request)
        self.assertEqual(issues[BaseComment.OPEN], 0)
        self.assertEqual(issues[BaseComment.DROPPED], 1)
        self.assertEqual(issues[BaseComment.RESOLVED], 0)

    def test_get_integration_config(self) -> None:
        """Testing StatusUpdate.integration_config getter"""
        # Pre-fetch the LocalSite cache.
        LocalSite.objects.has_local_sites()

        review_request = self.create_review_request()
        config = IntegrationConfig.objects.create(name='my-config')
        status_update = self.create_status_update(
            review_request,
            extra_data={
                '__integration_config_id': config.pk,
            })

        queries = [
            {
                'model': IntegrationConfig,
                'where': Q(pk=config.pk),
            },
        ]

        with self.assertQueries(queries):
            config2 = status_update.integration_config

        self.assertEqual(config, config2)

        # Check that the configuration is cached.
        with self.assertNumQueries(0):
            status_update.integration_config

    @add_fixtures(['test_site'])
    def test_get_integration_config_with_local_site(self) -> None:
        """Testing StatusUpdate.integration_config getter with Local Site"""
        # Pre-fetch the LocalSite cache.
        LocalSite.objects.has_local_sites()

        local_site = self.get_local_site(self.local_site_name)
        review_request = self.create_review_request(local_site=local_site)
        config = IntegrationConfig.objects.create(name='my-config',
                                                  local_site=local_site)
        status_update = self.create_status_update(
            review_request,
            extra_data={
                '__integration_config_id': config.pk,
            })

        queries = [
            {
                'model': IntegrationConfig,
                'where': Q(pk=config.pk) & Q(local_site=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            config2 = status_update.integration_config

        self.assertEqual(config, config2)

        # Check that the configuration is cached.
        with self.assertNumQueries(0):
            status_update.integration_config

    @add_fixtures(['test_site'])
    def test_get_integration_config_with_bad_local_site(self) -> None:
        """Testing StatusUpdate.integration_config getter with Local Site
        mismatch
        """
        # Pre-fetch the LocalSite cache.
        LocalSite.objects.has_local_sites()

        local_site = self.get_local_site(self.local_site_name)
        review_request = self.create_review_request(local_site=local_site)
        config = IntegrationConfig.objects.create(name='my-config')
        status_update = self.create_status_update(
            review_request,
            extra_data={
                '__integration_config_id': config.pk,
            })

        queries = [
            {
                'model': IntegrationConfig,
                'where': Q(pk=config.pk) & Q(local_site=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            config2 = status_update.integration_config

        self.assertIsNone(config2)

        # Check that the result is cached.
        with self.assertNumQueries(0):
            status_update.integration_config

    def test_get_integration_config_with_missing(self) -> None:
        """Testing StatusUpdate.integration_config getter with missing
        IntegrationConfig
        """
        # Pre-fetch the LocalSite cache.
        LocalSite.objects.has_local_sites()

        review_request = self.create_review_request()
        status_update = self.create_status_update(
            review_request,
            extra_data={
                '__integration_config_id': 123,
            })

        queries = [
            {
                'model': IntegrationConfig,
                'where': Q(pk=123),
            },
        ]

        with self.assertQueries(queries):
            config2 = status_update.integration_config

        self.assertIsNone(config2)

        # Check that the result is cached.
        with self.assertNumQueries(0):
            status_update.integration_config

    def test_set_integration_config(self) -> None:
        """Testing StatusUpdate.integration_config setter"""
        review_request = self.create_review_request()
        status_update = self.create_status_update(review_request)

        self.assertEqual(status_update.extra_data, {})

        # Set the configuration.
        config = IntegrationConfig.objects.create(name='my-config')
        status_update.integration_config = config

        self.assertEqual(status_update.extra_data, {
            '__integration_config_id': config.pk,
        })
        self.assertEqual(status_update.integration_config, config)

    def test_set_integration_config_with_none(self) -> None:
        """Testing StatusUpdate.integration_config setter with None"""
        review_request = self.create_review_request()
        status_update = self.create_status_update(review_request)

        self.assertEqual(status_update.extra_data, {})

        # Set the initial configuration.
        config = IntegrationConfig.objects.create(name='my-config')
        status_update.integration_config = config

        self.assertEqual(status_update.extra_data, {
            '__integration_config_id': config.pk,
        })
        self.assertEqual(status_update.integration_config, config)

        # Set it back to None.
        status_update.integration_config = None

        self.assertEqual(status_update.extra_data, {})
        self.assertIsNone(status_update.integration_config)

    def test_set_integration_config_with_bad_local_site(self) -> None:
        """Testing StatusUpdate.integration_config setter with LocalSite
        mismatch
        """
        review_request = self.create_review_request()
        status_update = self.create_status_update(review_request)

        self.assertEqual(status_update.extra_data, {})

        # Set the initial configuration.
        local_site = self.create_local_site(name='test-site-1')
        config = IntegrationConfig.objects.create(name='my-config',
                                                  local_site=local_site)

        message = (
            'The integration configuration and Status Update must have the '
            'same Local Site.'
        )

        with self.assertRaisesMessage(ValueError, message):
            status_update.integration_config = config

        self.assertEqual(status_update.extra_data, {})
        self.assertIsNone(status_update.integration_config)
