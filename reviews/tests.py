import unittest

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.template import Token, TOKEN_TEXT
from django.test import TestCase

from djblets.util.testing import TagTest

import reviewboard.reviews.templatetags.emailtags as emailtags
from reviewboard.reviews.email import get_email_address_for_user, \
                                      get_email_addresses_for_group, \
                                      mail_review_request, mail_review, \
                                      mail_reply
from reviewboard.reviews.models import Group, ReviewRequest, Review


class EmailTests(TestCase):
    """Tests the e-mail support."""
    fixtures = ['email_test']

    def setUp(self):
        settings.SEND_REVIEW_MAIL = True
        mail.outbox = []

    def testNewReviewRequestEmail(self):
        """Testing sending an e-mail when creating a new review request."""
        review_request = ReviewRequest.objects.get(submitter__username="doc")
        mail_review_request(review_request.submitter, review_request)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         "Review Request: Make cleaned data work with " +
                         "older and newer newforms")
        self.assertValidRecipients(["grumpy", "doc"], ["reviewboard"])

    def testReviewEmail(self):
        """Testing sending an e-mail when replying to a review request."""
        review = Review.objects.get(pk=1)
        self.assertEqual(review.user.username, "grumpy")
        mail_review(review.user, review)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         "Re: Review Request: Make cleaned data work with " +
                         "older and newer newforms")
        self.assertValidRecipients(["grumpy", "doc"], ["reviewboard"])

    def testReviewReplyEmail(self):
        """Testing sending an e-mail when replying to a review."""
        base_review = Review.objects.get(pk=1)
        reply = Review.objects.get(base_reply_to=base_review,
                                   user__username="dopey")
        mail_reply(reply.user, reply)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         "Re: Review Request: Make cleaned data work with " +
                         "older and newer newforms")
        self.assertValidRecipients(["grumpy", "doc", "dopey"], ["reviewboard"])

    def testUpdateReviewRequestEmail(self):
        """Testing sending an e-mail when updating a review request."""
        review_request = ReviewRequest.objects.get(submitter__username="doc")
        review_request.email_message_id = "junk"
        mail_review_request(review_request.submitter, review_request)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         "Re: Review Request: Make cleaned data work with " +
                         "older and newer newforms")
        self.assertValidRecipients(["grumpy", "doc", "dopey"], ["reviewboard"])

    def testDiffUpdateEmail(self):
        """Testing sending an e-mail when replying to a review."""
        base_review = Review.objects.get(pk=1)
        reply = Review.objects.get(base_reply_to=base_review,
                                   user__username="dopey")
        mail_reply(reply.user, reply)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         "Re: Review Request: Make cleaned data work with " +
                         "older and newer newforms")
        self.assertValidRecipients(["grumpy", "doc", "dopey"], ["reviewboard"])

    def assertValidRecipients(self, user_list, group_list):
        recipient_list = mail.outbox[0].to
        self.assertEqual(len(recipient_list), len(user_list) + len(group_list))

        for user in user_list:
            self.assert_(get_email_address_for_user(
                User.objects.get(username=user)) in recipient_list)

        for group in Group.objects.filter(name__in=group_list):
            for address in get_email_addresses_for_group(group):
                self.assert_(address in recipient_list)


class CondenseTagTest(TagTest):
    def getContentText(self):
        return "foo\nbar\n\n\n\n\n\n\nfoobar!"

    def testPlain(self):
        """Testing condense tag"""
        node = emailtags.condense(self.parser, Token(TOKEN_TEXT, 'condense'))
        self.assertEqual(node.render({}), "foo\nbar\n\n\nfoobar!")


class QuoteTextFilterTest(unittest.TestCase):
    def testPlain(self):
        """Testing quote_text filter (default level)"""
        self.assertEqual(emailtags.quote_text("foo\nbar"),
                         "> foo\n> bar")

    def testLevel2(self):
        """Testing quote_text filter (level 2)"""
        self.assertEqual(emailtags.quote_text("foo\nbar", 2),
                         "> > foo\n> > bar")
