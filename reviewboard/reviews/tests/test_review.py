from __future__ import unicode_literals

from datetime import datetime, timedelta
import logging

from django.contrib.auth.models import AnonymousUser, User
from django.utils import timezone
from djblets.testing.decorators import add_fixtures
from djblets.util.dates import get_tz_aware_utcnow
from kgb import SpyAgency, spy_on

from reviewboard.reviews.errors import RevokeShipItError
from reviewboard.reviews.models import Review, ReviewRequest
from reviewboard.reviews.signals import (review_ship_it_revoked,
                                         review_ship_it_revoking)
from reviewboard.testing import TestCase


class ReviewTests(SpyAgency, TestCase):
    """Unit tests for reviewboard.reviews.models.Review."""

    fixtures = ['test_users', 'test_scmtools']

    def test_duplicate_reviews(self):
        """Testing consolidation of duplicate reviews"""
        body_top = 'This is the body_top.'
        body_bottom = 'This is the body_bottom.'
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'
        comment_text_3 = 'Comment text 3'

        # Some objects we need.
        user = User.objects.get(username='doc')

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        # Create the first review.
        master_review = self.create_review(review_request, user=user,
                                           body_top=body_top,
                                           body_bottom='')
        self.create_diff_comment(master_review, filediff, text=comment_text_1,
                                 first_line=1, num_lines=1)

        # Create the second review.
        review = self.create_review(review_request, user=user,
                                    body_top='', body_bottom='')
        self.create_diff_comment(review, filediff, text=comment_text_2,
                                 first_line=1, num_lines=1)

        # Create the third review.
        review = self.create_review(review_request, user=user,
                                    body_top='',
                                    body_bottom=body_bottom)
        self.create_diff_comment(review, filediff, text=comment_text_3,
                                 first_line=1, num_lines=1)

        # Now that we've made a mess, see if we get a single review back.
        logging.disable(logging.WARNING)
        review = review_request.get_pending_review(user)
        self.assertTrue(review)
        self.assertEqual(review.id, master_review.id)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)

        comments = list(review.comments.all())
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_2)
        self.assertEqual(comments[2].text, comment_text_3)

    def test_all_participants_with_replies(self):
        """Testing Review.all_participants with replies"""
        user1 = User.objects.create_user(username='aaa',
                                         email='user1@example.com')
        user2 = User.objects.create_user(username='bbb',
                                         email='user2@example.com')
        user3 = User.objects.create_user(username='ccc',
                                         email='user3@example.com')
        user4 = User.objects.create_user(username='ddd',
                                         email='user4@example.com')

        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, user=user1)
        self.create_reply(review, user=user2, public=True)
        self.create_reply(review, user=user1, public=True)
        self.create_reply(review, user=user4, public=False)
        self.create_reply(review, user=user3, public=True)
        self.create_reply(review, user=user2, public=True)

        with self.assertNumQueries(2):
            self.assertEqual(review.all_participants, {user1, user2, user3})

    def test_all_participants_with_no_replies(self):
        """Testing Review.all_participants with no replies"""
        user = User.objects.create_user(username='aaa',
                                        email='user1@example.com')

        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, user=user)

        with self.assertNumQueries(1):
            self.assertEqual(review.all_participants, {user})

    def test_all_participants_with_only_owner_reply(self):
        """Testing Review.all_participants with only review owner replied"""
        user = User.objects.create_user(username='aaa',
                                        email='user1@example.com')

        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, user=user)
        self.create_reply(review, user=user, public=True)

        with self.assertNumQueries(1):
            self.assertEqual(review.all_participants, {user})

    def test_is_accessible_by_with_public_and_anonymous_user(self):
        """Testing Review.is_accessible_by with public and anonymous user"""
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request,
                                    user=user,
                                    public=True)

        self.assertTrue(review.is_accessible_by(AnonymousUser()))

    def test_is_accessible_by_with_public_and_private_review_request(self):
        """Testing Review.is_accessible_by with public review and private
        review request
        """
        user = User.objects.get(username='doc')
        other_user = User.objects.get(username='dopey')

        review_request = self.create_review_request(create_repository=True)
        review = self.create_review(review_request,
                                    user=user,
                                    public=True)

        review_request.repository.public = True
        review_request.repository.save(update_fields=('public',))

        self.assertFalse(review.is_accessible_by(other_user))

    def test_is_accessible_by_with_private_and_anonymous_user(self):
        """Testing Review.is_accessible_by with private and anonymous user"""
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request,
                                    user=user)

        self.assertFalse(review.is_accessible_by(AnonymousUser()))

    def test_is_accessible_by_with_private_and_owner(self):
        """Testing Review.is_accessible_by with private and owner"""
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request,
                                    user=user)

        self.assertTrue(review.is_accessible_by(user))

    def test_is_accessible_by_with_private_and_superuser(self):
        """Testing Review.is_accessible_by with private and superuser"""
        user = User.objects.get(username='doc')
        admin = User.objects.get(username='admin')
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request,
                                    user=user)

        self.assertTrue(review.is_accessible_by(admin))

    def test_is_mutable_by_with_public_and_owner(self):
        """Testing Review.is_mutable_by with public and owner"""
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request,
                                    user=user,
                                    public=True)

        self.assertFalse(review.is_mutable_by(user))

    def test_is_mutable_by_with_private_and_anonymous_user(self):
        """Testing Review.is_mutable_by with private and anonymous user"""
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request,
                                    user=user)

        self.assertFalse(review.is_mutable_by(AnonymousUser()))

    def test_is_mutable_by_with_private_and_owner(self):
        """Testing Review.is_mutable_by with private and owner"""
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request,
                                    user=user)

        self.assertTrue(review.is_mutable_by(user))

    def test_is_mutable_by_with_private_and_superuser(self):
        """Testing Review.is_mutable_by with private and superuser"""
        user = User.objects.get(username='doc')
        admin = User.objects.get(username='admin')
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request,
                                    user=user)

        self.assertTrue(review.is_mutable_by(admin))

    def test_is_new_for_user_with_non_owner(self):
        """Testing Review.is_new_for_user with non-owner"""
        user1 = User.objects.create_user(username='test-user-1',
                                         email='user1@example.com')
        user2 = User.objects.create_user(username='test-user-2',
                                         email='user2@example.com')

        review = Review(
            user=user1,
            timestamp=datetime(2017, 9, 7, 15, 27, 0))
        self.assertTrue(review.is_new_for_user(
            user=user2,
            last_visited=datetime(2017, 9, 7, 10, 0, 0)))
        self.assertFalse(review.is_new_for_user(
            user=user2,
            last_visited=datetime(2017, 9, 7, 16, 0, 0)))
        self.assertFalse(review.is_new_for_user(
            user=user2,
            last_visited=datetime(2017, 9, 7, 15, 27, 0)))

    def test_is_new_for_user_with_owner(self):
        """Testing Review.is_new_for_user with owner"""
        user = User.objects.create_user(username='test-user',
                                        email='user@example.com')

        review = Review(
            user=user,
            timestamp=datetime(2017, 9, 7, 15, 27, 0))
        self.assertFalse(review.is_new_for_user(
            user=user,
            last_visited=datetime(2017, 9, 7, 16, 0, 0)))

    def test_can_user_revoke_ship_it_with_owner(self):
        """Testing Review.can_user_revoke_ship_it with review owner"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review = self.create_review(review_request,
                                    body_top=Review.SHIP_IT_TEXT,
                                    ship_it=True,
                                    publish=True)

        self.assertTrue(review.can_user_revoke_ship_it(review.user))

    def test_can_user_revoke_ship_it_with_non_owner(self):
        """Testing Review.can_user_revoke_ship_it with non-owner"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review = self.create_review(review_request,
                                    body_top=Review.SHIP_IT_TEXT,
                                    ship_it=True,
                                    publish=True)

        user = User.objects.get(username='doc')
        self.assertNotEqual(review.user, user)

        self.assertFalse(review.can_user_revoke_ship_it(user))

    def test_can_user_revoke_ship_it_with_superuser(self):
        """Testing Review.can_user_revoke_ship_it with superuser"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review = self.create_review(review_request,
                                    body_top=Review.SHIP_IT_TEXT,
                                    ship_it=True,
                                    publish=True)

        user = User.objects.get(username='admin')
        self.assertNotEqual(review.user, user)

        self.assertTrue(review.can_user_revoke_ship_it(user))

    @add_fixtures(['test_site'])
    def test_can_user_revoke_ship_it_with_local_site_admin(self):
        """Testing Review.can_user_revoke_ship_it with LocalSite admin"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True,
                                                    with_local_site=True)
        review = self.create_review(review_request,
                                    body_top=Review.SHIP_IT_TEXT,
                                    ship_it=True,
                                    publish=True)

        user = User.objects.create_user(username='new-site-admin',
                                        email='new_site_admin@example.com')
        review_request.local_site.admins.add(user)
        review_request.local_site.users.add(user)

        self.assertTrue(review.can_user_revoke_ship_it(user))

    def test_can_user_revoke_ship_it_with_anonymous(self):
        """Testing Review.can_user_revoke_ship_it with anonymous user"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review = self.create_review(review_request,
                                    body_top=Review.SHIP_IT_TEXT,
                                    ship_it=True,
                                    publish=True)

        self.assertFalse(review.can_user_revoke_ship_it(AnonymousUser()))

    def test_can_user_revoke_ship_it_with_unpublished(self):
        """Testing Review.can_user_revoke_ship_it with unpublished review"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review = self.create_review(review_request,
                                    body_top=Review.SHIP_IT_TEXT,
                                    ship_it=True)

        self.assertFalse(review.can_user_revoke_ship_it(review.user))

    def test_can_user_revoke_ship_it_with_no_ship_it(self):
        """Testing Review.can_user_revoke_ship_it with no Ship It"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review = self.create_review(review_request)

        self.assertFalse(review.can_user_revoke_ship_it(review.user))

    def test_revoke_ship_it(self):
        """Testing Review.revoke_ship_it"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review = self.create_review(review_request,
                                    body_top=Review.SHIP_IT_TEXT,
                                    ship_it=True,
                                    publish=True)

        self.spy_on(review_ship_it_revoking.send)
        self.spy_on(review_ship_it_revoked.send)

        self.assertEqual(review_request.shipit_count, 1)

        review.revoke_ship_it(review.user)

        # Make sure the signals fired.
        self.assertTrue(review_ship_it_revoking.send.called_with(
            sender=Review, user=review.user, review=review))
        self.assertTrue(review_ship_it_revoked.send.called_with(
            sender=Review, user=review.user, review=review))

        # Check the state of the fields.
        self.assertEqual(review.body_top, Review.REVOKED_SHIP_IT_TEXT)
        self.assertFalse(review.ship_it)
        self.assertTrue(review.extra_data.get('revoked_ship_it'))
        self.assertEqual(review_request.shipit_count, 0)

        # Make sure they persisted to the database.
        review = Review.objects.get(pk=review.pk)
        self.assertEqual(review.body_top, Review.REVOKED_SHIP_IT_TEXT)
        self.assertFalse(review.ship_it)
        self.assertTrue(review.extra_data.get('revoked_ship_it'))

    def test_revoke_ship_it_with_no_ship_it(self):
        """Testing Review.revoke_ship_it with no Ship It"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review = self.create_review(review_request,
                                    body_top=Review.SHIP_IT_TEXT,
                                    publish=True)

        expected_error = 'This review is not marked Ship It!'

        with self.assertRaisesMessage(RevokeShipItError, expected_error):
            review.revoke_ship_it(review.user)

        self.assertEqual(review.body_top, Review.SHIP_IT_TEXT)
        self.assertFalse(review.ship_it)

    def test_revoke_ship_it_with_custom_body_top(self):
        """Testing Review.revoke_ship_it with custom existing body_top"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review = self.create_review(review_request,
                                    body_top='This is a test',
                                    ship_it=True,
                                    publish=True)

        review.revoke_ship_it(review.user)

        self.assertEqual(review.body_top, 'This is a test')
        self.assertFalse(review.ship_it)
        self.assertTrue(review.extra_data.get('revoked_ship_it'))

    def test_revoke_ship_it_with_revoking_signal_exception(self):
        """Testing Review.revoke_ship_it with exception in
        review_ship_it_revoking handler
        """
        def on_revoking(**kwargs):
            raise Exception('oh no')

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review = self.create_review(review_request,
                                    body_top=Review.SHIP_IT_TEXT,
                                    ship_it=True,
                                    publish=True)

        try:
            review_ship_it_revoking.connect(on_revoking)

            expected_error = 'Error revoking the Ship It: oh no'

            with self.assertRaisesMessage(RevokeShipItError, expected_error):
                review.revoke_ship_it(review.user)
        finally:
            review_ship_it_revoking.disconnect(on_revoking)

        self.assertEqual(review.body_top, Review.SHIP_IT_TEXT)
        self.assertTrue(review.ship_it)
        self.assertNotIn('revoked_ship_it', review.extra_data)

    def test_revoke_ship_it_with_revoked_signal_exception(self):
        """Testing Review.revoke_ship_it with exception in
        review_ship_it_revoked handler
        """
        def on_revoked(**kwargs):
            raise Exception('oh no')

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review = self.create_review(review_request,
                                    body_top=Review.SHIP_IT_TEXT,
                                    ship_it=True,
                                    publish=True)

        try:
            review_ship_it_revoked.connect(on_revoked)
            review.revoke_ship_it(review.user)
        finally:
            review_ship_it_revoked.disconnect(on_revoked)

        self.assertEqual(review.body_top, Review.REVOKED_SHIP_IT_TEXT)
        self.assertFalse(review.ship_it)
        self.assertTrue(review.extra_data.get('revoked_ship_it'))

    def test_revoke_ship_it_timestamp(self):
        """Testing Review.revoke_ship_it does not modify the review timestamp
        """
        # ReviewRequest.last_update is a
        # django.db.fields.ModificationTimestampField, which retrieves its
        # value from datetime.utcnow().replace(tzinfo=utc).
        #
        # django.utils.timezone.now has the same implementation.
        #
        # Unfortunately, we cannot spy on datetime.utcnow since it is a
        # builtin. So we replace get_tz_aware_utcnow with timezone.now and we
        # will replace that with a constant function in the spy_on calls below.
        self.spy_on(get_tz_aware_utcnow, call_fake=lambda: timezone.now())

        creation_timestamp = datetime.fromtimestamp(0, timezone.utc)
        review_timestamp = creation_timestamp + timedelta(hours=1)
        revoke_timestamp = review_timestamp + timedelta(hours=1)

        with spy_on(timezone.now, call_fake=lambda: creation_timestamp):
            review_request = self.create_review_request(publish=True)

        with spy_on(timezone.now, call_fake=lambda: review_timestamp):
            review = self.create_review(review_request,
                                        body_top=Review.SHIP_IT_TEXT,
                                        ship_it=True,
                                        publish=True)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)

        self.assertEqual(review_request.time_added, creation_timestamp)
        self.assertEqual(review_request.last_updated, review_timestamp)
        self.assertEqual(review.timestamp, review_timestamp)

        with spy_on(timezone.now, call_fake=lambda: revoke_timestamp):
            review.revoke_ship_it(review.user)

        review = Review.objects.get(pk=review.pk)
        review_request = ReviewRequest.objects.get(pk=review_request.pk)

        self.assertEqual(review_request.time_added, creation_timestamp)
        self.assertEqual(review_request.last_updated, review_timestamp)
        self.assertEqual(review.timestamp, review_timestamp)
