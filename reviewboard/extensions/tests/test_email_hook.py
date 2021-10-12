"""Unit tests for reviewboard.extensions.hooks.EmailHook and subclasses."""

from django.contrib.auth.models import User
from django.core import mail
from djblets.mail.utils import build_email_address_for_user
from kgb import SpyAgency

from reviewboard.extensions.hooks import (EmailHook,
                                          ReviewPublishedEmailHook,
                                          ReviewReplyPublishedEmailHook,
                                          ReviewRequestClosedEmailHook,
                                          ReviewRequestPublishedEmailHook)
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase
from reviewboard.reviews.models import ReviewRequest
from reviewboard.reviews.signals import (review_request_published,
                                         review_published,
                                         reply_published,
                                         review_request_closed)


class EmailHookTests(SpyAgency, BaseExtensionHookTestCase):
    """Testing the e-mail recipient filtering capacity of EmailHooks."""

    fixtures = ['test_users']

    def setUp(self):
        super(EmailHookTests, self).setUp()

        mail.outbox = []

    def test_review_request_published_email_hook(self):
        """Testing ReviewRequestPublishedEmailHook"""
        class DummyHook(ReviewRequestPublishedEmailHook):
            def get_to_field(self, to_field, review_request, user):
                return set([user])

            def get_cc_field(self, cc_field, review_request, user):
                return set([user])

        hook = DummyHook(self.extension)

        self.spy_on(hook.get_to_field)
        self.spy_on(hook.get_cc_field)

        review_request = self.create_review_request()
        admin = User.objects.get(username='admin')

        call_kwargs = {
            'user': admin,
            'review_request': review_request,
        }

        with self.siteconfig_settings({'mail_send_review_mail': True}):
            review_request.publish(admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to,
                         [build_email_address_for_user(admin)])
        self.assertTrue(hook.get_to_field.called)
        self.assertTrue(hook.get_to_field.called_with(**call_kwargs))
        self.assertTrue(hook.get_cc_field.called)
        self.assertTrue(hook.get_cc_field.called_with(**call_kwargs))

    def test_review_published_email_hook(self):
        """Testing ReviewPublishedEmailHook"""
        class DummyHook(ReviewPublishedEmailHook):
            def get_to_field(self, to_field, review, user, review_request,
                             to_owner_only):
                return set([user])

            def get_cc_field(self, cc_field, review, user, review_request,
                             to_owner_only):
                return set([user])

        hook = DummyHook(self.extension)

        self.spy_on(hook.get_to_field)
        self.spy_on(hook.get_cc_field)

        admin = User.objects.get(username='admin')
        review_request = self.create_review_request(public=True)
        review = self.create_review(review_request)

        call_kwargs = {
            'user': admin,
            'review_request': review_request,
            'review': review,
            'to_owner_only': False,
        }

        with self.siteconfig_settings({'mail_send_review_mail': True}):
            review.publish(admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to,
                         [build_email_address_for_user(admin)])
        self.assertTrue(hook.get_to_field.called)
        self.assertTrue(hook.get_to_field.called_with(**call_kwargs))
        self.assertTrue(hook.get_cc_field.called)
        self.assertTrue(hook.get_cc_field.called_with(**call_kwargs))

    def test_review_reply_published_email_hook(self):
        """Testing ReviewReplyPublishedEmailHook"""
        class DummyHook(ReviewReplyPublishedEmailHook):
            def get_to_field(self, to_field, reply, user, review,
                             review_request):
                return set([user])

            def get_cc_field(self, cc_field, reply, user, review,
                             review_request):
                return set([user])

        hook = DummyHook(self.extension)

        self.spy_on(hook.get_to_field)
        self.spy_on(hook.get_cc_field)

        admin = User.objects.get(username='admin')
        review_request = self.create_review_request(public=True)
        review = self.create_review(review_request)
        reply = self.create_reply(review)

        call_kwargs = {
            'user': admin,
            'review_request': review_request,
            'review': review,
            'reply': reply,
        }

        with self.siteconfig_settings({'mail_send_review_mail': True}):
            reply.publish(admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(hook.get_to_field.called)
        self.assertTrue(hook.get_to_field.called_with(**call_kwargs))
        self.assertTrue(hook.get_cc_field.called)
        self.assertTrue(hook.get_cc_field.called_with(**call_kwargs))

    def test_review_request_closed_email_hook_submitted(self):
        """Testing ReviewRequestClosedEmailHook for a review request being
        submitted
        """
        class DummyHook(ReviewRequestClosedEmailHook):
            def get_to_field(self, to_field, review_request, user, close_type):
                return set([user])

            def get_cc_field(self, cc_field, review_request, user, close_type):
                return set([user])

        hook = DummyHook(self.extension)

        self.spy_on(hook.get_to_field)
        self.spy_on(hook.get_cc_field)

        admin = User.objects.get(username='admin')
        review_request = self.create_review_request(public=True)

        call_kwargs = {
            'user': admin,
            'review_request': review_request,
            'close_type': ReviewRequest.SUBMITTED,
        }

        with self.siteconfig_settings({'mail_send_review_close_mail': True}):
            review_request.close(ReviewRequest.SUBMITTED, admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(hook.get_to_field.called)
        self.assertTrue(hook.get_to_field.called_with(**call_kwargs))
        self.assertTrue(hook.get_cc_field.called)
        self.assertTrue(hook.get_cc_field.called_with(**call_kwargs))

    def test_review_request_closed_email_hook_discarded(self):
        """Testing ReviewRequestClosedEmailHook for a review request being
        discarded
        """
        class DummyHook(ReviewRequestClosedEmailHook):
            def get_to_field(self, to_field, review_request, user, close_type):
                return set([user])

            def get_cc_field(self, cc_field, review_request, user, close_type):
                return set([user])

        hook = DummyHook(self.extension)

        self.spy_on(hook.get_to_field)
        self.spy_on(hook.get_cc_field)

        admin = User.objects.get(username='admin')
        review_request = self.create_review_request(public=True)

        call_kwargs = {
            'user': admin,
            'review_request': review_request,
            'close_type': ReviewRequest.DISCARDED,
        }

        with self.siteconfig_settings({'mail_send_review_close_mail': True}):
            review_request.close(ReviewRequest.DISCARDED, admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(hook.get_to_field.called)
        self.assertTrue(hook.get_to_field.called_with(**call_kwargs))
        self.assertTrue(hook.get_cc_field.called)
        self.assertTrue(hook.get_cc_field.called_with(**call_kwargs))

    def test_generic_hook(self):
        """Testing EmailHook connects to all signals"""
        hook = EmailHook(self.extension,
                         signals=[
                             review_request_published,
                             review_published,
                             reply_published,
                             review_request_closed,
                         ])

        self.spy_on(hook.get_to_field)
        self.spy_on(hook.get_cc_field)

        user = User.objects.create_user(username='testuser')
        review_request = self.create_review_request(public=True,
                                                    target_people=[user])
        review = self.create_review(review_request)
        reply = self.create_reply(review)

        siteconfig_settings = {
            'mail_send_review_mail': True,
            'mail_send_review_close_mail': True,
        }

        with self.siteconfig_settings(siteconfig_settings):
            self.assertEqual(len(mail.outbox), 0)

            review.publish()
            call_kwargs = {
                'user': review.user,
                'review': review,
                'review_request': review_request,
                'to_owner_only': False,
            }

            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(len(hook.get_to_field.spy.calls), 1)
            self.assertEqual(len(hook.get_cc_field.spy.calls), 1)
            self.assertEqual(hook.get_to_field.spy.calls[-1].kwargs,
                             call_kwargs)
            self.assertEqual(hook.get_cc_field.spy.calls[-1].kwargs,
                             call_kwargs)

            reply.publish(reply.user)

            call_kwargs.pop('to_owner_only')
            call_kwargs['reply'] = reply
            call_kwargs['user'] = reply.user

            self.assertEqual(len(mail.outbox), 2)
            self.assertEqual(len(hook.get_to_field.spy.calls), 2)
            self.assertEqual(len(hook.get_cc_field.spy.calls), 2)
            self.assertEqual(hook.get_to_field.spy.calls[-1].kwargs,
                             call_kwargs)
            self.assertEqual(hook.get_cc_field.spy.calls[-1].kwargs,
                             call_kwargs)

            review_request.close(ReviewRequest.DISCARDED)
            call_kwargs = {
                'review_request': review_request,
                'user': review_request.submitter,
                'close_type': ReviewRequest.DISCARDED,
            }

            self.assertEqual(len(mail.outbox), 3)
            self.assertEqual(len(hook.get_to_field.spy.calls), 3)
            self.assertEqual(len(hook.get_cc_field.spy.calls), 3)
            self.assertEqual(hook.get_to_field.spy.calls[-1].kwargs,
                             call_kwargs)
            self.assertEqual(hook.get_cc_field.spy.calls[-1].kwargs,
                             call_kwargs)

            review_request.reopen()
            review_request.publish(review_request.submitter)
            call_kwargs = {
                'review_request': review_request,
                'user': review_request.submitter,
            }

            self.assertEqual(len(mail.outbox), 4)
            self.assertEqual(len(hook.get_to_field.spy.calls), 4)
            self.assertEqual(len(hook.get_cc_field.spy.calls), 4)
            self.assertEqual(hook.get_to_field.spy.calls[-1].kwargs,
                             call_kwargs)
            self.assertEqual(hook.get_cc_field.spy.calls[-1].kwargs,
                             call_kwargs)

            review_request.close(ReviewRequest.SUBMITTED)
            call_kwargs['close_type'] = ReviewRequest.SUBMITTED

            self.assertEqual(len(mail.outbox), 5)
            self.assertEqual(len(hook.get_to_field.spy.calls), 5)
            self.assertEqual(len(hook.get_cc_field.spy.calls), 5)
            self.assertEqual(hook.get_to_field.spy.calls[-1].kwargs,
                             call_kwargs)
            self.assertEqual(hook.get_cc_field.spy.calls[-1].kwargs,
                             call_kwargs)
