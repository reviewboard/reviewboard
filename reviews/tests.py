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


class ViewTests(TestCase):
    """Tests for views in reviewboard.reviews.views"""
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools']

    def testReviewDetail0(self):
        """Testing review_detail redirect"""
        response = self.client.get('/r/1')
        self.assertEqual(response.status_code, 301)

    def testReviewDetail1(self):
        """Testing review_detail view (1)"""
        response = self.client.get('/r/1/')
        self.assertEqual(response.status_code, 200)

        context = response.context[0] # Since multiple templates were used to
                                      # render the page, this is a list with one
                                      # element.  I dunno, ask the django
                                      # developers why.
        request = context['review_request']

        self.assertEqual(request.submitter.username, 'doc')
        self.assertEqual(request.summary, 'Comments Improvements')
        self.assertEqual(request.description, '')
        self.assertEqual(request.testing_done, '')

        self.assertEqual(request.target_people.count(), 0)
        self.assertEqual(request.target_groups.count(), 1)
        self.assertEqual(request.target_groups.all()[0].name, 'devgroup')
        self.assertEqual(request.bugs_closed, '')
        self.assertEqual(request.status, 'P')

        # TODO - diff

    def testReviewDetail2(self):
        """Testing review_detail view (3)"""
        # Make sure this request is made while logged in, to catch the
        # login-only pieces of the review_detail view.
        self.client.login(username='admin', password='admin')

        response = self.client.get('/r/3/')
        print response.content
        self.assertEqual(response.status_code, 200)

        context = response.context[0] # Since multiple templates were used to
                                      # render the page, this is a list with one
                                      # element.  I dunno, ask the django
                                      # developers why.
        request = context['review_request']

        self.assertEqual(request.submitter.username, 'admin')
        self.assertEqual(request.summary, 'Add permission checking for JSON API')
        self.assertEqual(request.description,
                         'Added some user permissions checking for JSON API functions.')
        self.assertEqual(request.testing_done, 'Tested some functions.')

        self.assertEqual(request.target_people.count(), 2)
        self.assertEqual(request.target_people.all()[0].username, 'doc')
        self.assertEqual(request.target_people.all()[1].username, 'dopey')

        self.assertEqual(request.target_groups.count(), 1)
        self.assertEqual(request.target_groups.all()[0].name, 'privgroup')

        self.assertEqual(request.bugs_closed, '1234, 5678, 8765, 4321')
        self.assertEqual(request.status, 'P')

        # TODO - diff
        # TODO - reviews

        self.client.logout()

    def testNewReviewRequest0(self):
        """Testing new_review_request view (basic responses)"""
        response = self.client.get('/r/new')
        self.assertEqual(response.status_code, 301)

        response = self.client.get('/r/new/')
        self.assertEqual(response.status_code, 302)

        self.client.login(username='grumpy', password='grumpy')

        response = self.client.get('/r/new/')
        self.assertEqual(response.status_code, 200)

        self.client.logout()

    # TODO - test the rest of that form

    def testReviewList(self):
        """Testing all_review_requests view"""
        self.client.login(username='grumpy', password='grumpy')

        response = self.client.get('/r/')
        self.assertEqual(response.status_code, 200)

        context = response.context[0] # Since multiple templates were used to
                                      # render the page, this is a list with one
                                      # element.  I dunno, ask the django
                                      # developers why.

        review_requests = context['object_list']
        self.assertEqual(len(review_requests), 5)
        self.assertEqual(review_requests[0].summary,
                         'Made e-mail improvements')
        self.assertEqual(review_requests[1].summary,
                         'Improved login form')
        self.assertEqual(review_requests[2].summary,
                         'Error dialog')
        self.assertEqual(review_requests[3].summary,
                         'Update for cleaned_data changes')
        self.assertEqual(review_requests[4].summary,
                         'Add permission checking for JSON API')

        self.client.logout()

    def testSubmitterList(self):
        """Testing submitter_list view"""
        response = self.client.get('/users/')
        self.assertEqual(response.status_code, 200)

        # TODO - verify contents

    def testGroupList(self):
        """Testing group_list view"""
        response = self.client.get('/groups/')
        self.assertEqual(response.status_code, 200)

        # TODO - verify contents

    def testDashboard1(self):
        """Testing dashboard view (incoming)"""
        self.client.login(username='doc', password='doc')

        response = self.client.get('/dashboard/', {'view': 'incoming'})
        self.assertEqual(response.status_code, 200)

        context = response.context[0] # Since multiple templates were used to
                                      # render the page, this is a list with one
                                      # element.  I dunno, ask the django
                                      # developers why.

        review_requests = context['review_request_list']
        self.assertEqual(len(review_requests), 4)
        self.assertEqual(review_requests[0].summary,
                         'Made e-mail improvements')
        self.assertEqual(review_requests[1].summary,
                         'Update for cleaned_data changes')
        self.assertEqual(review_requests[2].summary,
                         'Comments Improvements')
        self.assertEqual(review_requests[3].summary,
                         'Add permission checking for JSON API')

        self.client.logout()

    def testDashboard2(self):
        """Testing dashboard view (outgoing)"""
        self.client.login(username='admin', password='admin')

        response = self.client.get('/dashboard/', {'view': 'outgoing'})
        self.assertEqual(response.status_code, 200)

        context = response.context[0] # Since multiple templates were used to
                                      # render the page, this is a list with one
                                      # element.  I dunno, ask the django
                                      # developers why.

        review_requests = context['review_request_list']
        self.assertEqual(len(review_requests), 1)
        self.assertEqual(review_requests[0].summary,
                         'Add permission checking for JSON API')

        self.client.logout()


    def testDashboard3(self):
        """Testing dashboard view (to-me)"""
        self.client.login(username='doc', password='doc')

        response = self.client.get('/dashboard/', {'view': 'to-me'})
        self.assertEqual(response.status_code, 200)

        context = response.context[0] # Since multiple templates were used to
                                      # render the page, this is a list with one
                                      # element.  I dunno, ask the django
                                      # developers why.

        review_requests = context['review_request_list']
        self.assertEqual(len(review_requests), 2)
        self.assertEqual(review_requests[0].summary, 'Made e-mail improvements')
        self.assertEqual(review_requests[1].summary,
                         'Add permission checking for JSON API')

        self.client.logout()


    def testDashboard4(self):
        """Testing dashboard view (to-group devgroup)"""
        self.client.login(username='doc', password='doc')

        response = self.client.get('/dashboard/',
                                   {'view': 'to-group',
                                    'group': 'devgroup'})
        self.assertEqual(response.status_code, 200)

        context = response.context[0] # Since multiple templates were used to
                                      # render the page, this is a list with one
                                      # element.  I dunno, ask the django
                                      # developers why.

        review_requests = context['review_request_list']
        self.assertEqual(len(review_requests), 2)
        self.assertEqual(review_requests[0].summary,
                         'Update for cleaned_data changes')
        self.assertEqual(review_requests[1].summary, 'Comments Improvements')

        self.client.logout()
