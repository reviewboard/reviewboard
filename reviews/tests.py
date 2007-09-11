import unittest

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.template import Token, TOKEN_TEXT, TemplateSyntaxError
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
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools']

    def setUp(self):
        settings.SEND_REVIEW_MAIL = True
        mail.outbox = []

    def testNewReviewRequestEmail(self):
        """Testing sending an e-mail when creating a new review request"""
        review_request = ReviewRequest.objects.get(
            summary="Made e-mail improvements")
        mail_review_request(review_request.submitter, review_request)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         "Review Request: Made e-mail improvements")
        self.assertValidRecipients(["grumpy", "doc"], [])

    def testReviewEmail(self):
        """Testing sending an e-mail when replying to a review request"""
        review_request = ReviewRequest.objects.get(
            summary="Add permission checking for JSON API")
        review = Review.objects.get(review_request=review_request,
                                    user__username="doc",
                                    base_reply_to__isnull=True)
        self.assertEqual(review.body_top, "Test")
        mail_review(review.user, review)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         "Re: Review Request: Add permission checking " +
                         "for JSON API")
        self.assertValidRecipients(["admin", "doc", "dopey", "grumpy"], [])

    def testReviewReplyEmail(self):
        """Testing sending an e-mail when replying to a review"""
        review_request = ReviewRequest.objects.get(
            summary="Add permission checking for JSON API")
        base_review = Review.objects.get(review_request=review_request,
                                         user__username="doc",
                                         base_reply_to__isnull=True)
        reply = Review.objects.get(base_reply_to=base_review,
                                   user__username="dopey")
        mail_reply(reply.user, reply)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         "Re: Review Request: Add permission checking " +
                         "for JSON API")
        self.assertValidRecipients(["admin", "doc", "dopey", "admin"], [])

    def testUpdateReviewRequestEmail(self):
        """Testing sending an e-mail when updating a review request"""
        review_request = ReviewRequest.objects.get(
            summary="Update for cleaned_data changes")
        review_request.email_message_id = "junk"
        mail_review_request(review_request.submitter, review_request)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         "Re: Review Request: Update for cleaned_data changes")
        self.assertValidRecipients(["dopey", "doc"], ["devgroup"])

    def assertValidRecipients(self, user_list, group_list):
        recipient_list = mail.outbox[0].to
        self.assertEqual(len(recipient_list), len(user_list) + len(group_list))

        for user in user_list:
            self.assert_(get_email_address_for_user(
                User.objects.get(username=user)) in recipient_list,
                u"user %s was not found in the recipient list" % user)

        for group in Group.objects.filter(name__in=group_list):
            for address in get_email_addresses_for_group(group):
                self.assert_(address in recipient_list,
                    u"group %s was not found in the recipient list" % address)


class QuotedEmailTagTest(TagTest):
    def testInvalid(self):
        """Testing quoted_email tag (invalid usage)"""
        self.assertRaises(TemplateSyntaxError,
                          lambda: emailtags.quoted_email(self.parser,
                              Token(TOKEN_TEXT, 'quoted_email')))


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


class DbQueryTests(TestCase):
    """Tests review request query utility functions."""
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools']

    def testAllReviewRequests(self):
        """Testing get_all_review_requests"""
        self.assertValidSummaries(
            ReviewRequest.objects.public(
                User.objects.get(username="doc")),
            ["Comments Improvements",
             "Update for cleaned_data changes",
             "Add permission checking for JSON API",
             "Made e-mail improvements",
             "Error dialog"])

        self.assertValidSummaries(
            ReviewRequest.objects.public(status=None),
            ["Update for cleaned_data changes",
             "Add permission checking for JSON API",
             "Made e-mail improvements",
             "Error dialog",
             "Improved login form"])

        self.assertValidSummaries(
            ReviewRequest.objects.public(
                User.objects.get(username="doc"), status=None),
            ["Comments Improvements",
             "Update for cleaned_data changes",
             "Add permission checking for JSON API",
             "Made e-mail improvements",
             "Added interdiff support",
             "Error dialog",
             "Improved login form"])

    def testReviewRequestsToGroup(self):
        """Testing get_review_requests_to_group"""
        self.assertValidSummaries(
            ReviewRequest.objects.to_group("privgroup"),
            ["Add permission checking for JSON API"])

        self.assertValidSummaries(
            ReviewRequest.objects.to_group("privgroup", status=None),
            ["Add permission checking for JSON API"])

    def testReviewRequestsToUserGroups(self):
        """Testing get_review_requests_to_user_groups"""
        self.assertValidSummaries(
            ReviewRequest.objects.to_user_groups("doc"),
            ["Update for cleaned_data changes",
             "Add permission checking for JSON API"])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_groups("doc", status=None),
            ["Update for cleaned_data changes",
             "Add permission checking for JSON API"])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_groups("doc",
                User.objects.get(username="doc")),
            ["Comments Improvements",
             "Update for cleaned_data changes",
             "Add permission checking for JSON API"])

    def testReviewRequestsToUserDirectly(self):
        """Testing get_review_requests_to_user_directly"""
        self.assertValidSummaries(
            ReviewRequest.objects.to_user_directly("doc"),
            ["Add permission checking for JSON API",
             "Made e-mail improvements"])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_directly("doc", status=None),
            ["Add permission checking for JSON API",
             "Made e-mail improvements",
             "Improved login form"])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_directly("doc",
                User.objects.get(username="doc"), status=None),
            ["Add permission checking for JSON API",
             "Made e-mail improvements",
             "Added interdiff support",
             "Improved login form"])

    def testReviewRequestsFromUser(self):
        """Testing get_review_requests_from_user"""
        self.assertValidSummaries(
            ReviewRequest.objects.from_user("doc"), [])

        self.assertValidSummaries(
            ReviewRequest.objects.from_user("doc", status=None),
            ["Improved login form"])

        self.assertValidSummaries(
            ReviewRequest.objects.from_user("doc",
                user=User.objects.get(username="doc"), status=None),
            ["Comments Improvements",
             "Added interdiff support",
             "Improved login form"])

    def testReviewRequestsToUser(self):
        """Testing get_review_requests_to_user"""
        self.assertValidSummaries(
            ReviewRequest.objects.to_user("doc"),
            ["Update for cleaned_data changes",
             "Add permission checking for JSON API",
             "Made e-mail improvements"])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user("doc", status=None),
            ["Update for cleaned_data changes",
             "Add permission checking for JSON API",
             "Made e-mail improvements",
             "Improved login form"])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user("doc",
                User.objects.get(username="doc"), status=None),
            ["Comments Improvements",
             "Update for cleaned_data changes",
             "Add permission checking for JSON API",
             "Made e-mail improvements",
             "Added interdiff support",
             "Improved login form"])

    def assertValidSummaries(self, review_requests, summaries):
        r_summaries = [r.summary for r in review_requests]

        for summary in r_summaries:
            self.assert_(summary in summaries,
                         u'summary "%s" not found in summary list' % summary)

        for summary in summaries:
            self.assert_(summary in r_summaries,
                         u'summary "%s" not found in review request list' %
                         summary)
