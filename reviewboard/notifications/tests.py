from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from djblets.siteconfig.models import SiteConfiguration

from reviewboard import initialize
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.notifications.email import build_email_address, \
                                            get_email_address_for_user, \
                                            get_email_addresses_for_group
from reviewboard.reviews.models import Group, Review, ReviewRequest
from reviewboard.site.models import LocalSite


class EmailTestHelper(object):
    def assertValidRecipients(self, user_list, group_list):
        recipient_list = mail.outbox[0].to + mail.outbox[0].cc
        self.assertEqual(len(recipient_list), len(user_list) + len(group_list))

        for user in user_list:
            self.assert_(get_email_address_for_user(
                User.objects.get(username=user)) in recipient_list,
                u"user %s was not found in the recipient list" % user)

        groups = Group.objects.filter(name__in=group_list, local_site=None)
        for group in groups:
            for address in get_email_addresses_for_group(group):
                self.assert_(address in recipient_list,
                    u"group %s was not found in the recipient list" % address)


class UserEmailTests(TestCase, EmailTestHelper):
    def setUp(self):
        initialize()

        mail.outbox = []
        self.sender = 'noreply@example.com'

        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set("mail_send_new_user_mail", True)
        siteconfig.save()
        load_site_config()

    def test_new_user_email(self):
        """
        Testing sending an e-mail after a new user has successfully registered.
        """
        # Clear the outbox.
        mail.outbox = []

        new_user_info = {
            'username': 'NewUser',
            'password1': 'password',
            'password2': 'password',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User'
            }

        # Registration request have to be sent twice since djblets need to
        # validate cookies on the second request.
        self.client.get('/account/register/', new_user_info)
        self.client.post('/account/register/', new_user_info)

        siteconfig = SiteConfiguration.objects.get_current()
        admin_name = siteconfig.get('site_admin_name')
        admin_email_addr = siteconfig.get('site_admin_email')
        email = mail.outbox[0]

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(email.subject,
                         "New Review Board user registration for NewUser")

        self.assertEqual(email.from_email, self.sender)
        self.assertEqual(email.extra_headers['From'], settings.SERVER_EMAIL)
        self.assertEqual(email.to[0], build_email_address(admin_name,
                                                          admin_email_addr))


class ReviewRequestEmailTests(TestCase, EmailTestHelper):
    """Tests the e-mail support."""
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools',
                'test_site']

    def setUp(self):
        initialize()

        mail.outbox = []
        self.sender = 'noreply@example.com'

        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set("mail_send_review_mail", True)
        siteconfig.set("mail_default_from", self.sender)
        siteconfig.save()
        load_site_config()

    def testNewReviewRequestEmail(self):
        """Testing sending an e-mail when creating a new review request"""
        review_request = ReviewRequest.objects.get(
            summary="Made e-mail improvements")
        review_request.publish(review_request.submitter)
        from_email = get_email_address_for_user(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].extra_headers['From'], from_email)
        self.assertEqual(mail.outbox[0].subject,
                         "Review Request 4: Made e-mail improvements")
        self.assertValidRecipients(["grumpy", "doc"], [])

        message = mail.outbox[0].message()
        print review_request.submitter
        self.assertEqual(message['Sender'],
                         self._get_sender(review_request.submitter))

    def testReviewEmail(self):
        """Testing sending an e-mail when replying to a review request"""
        review_request = ReviewRequest.objects.get(
            summary="Add permission checking for JSON API")
        review_request.publish(review_request.submitter)

        # Clear the outbox.
        mail.outbox = []

        review = Review.objects.get(review_request=review_request,
                                    user__username="doc",
                                    base_reply_to__isnull=True)
        self.assertEqual(review.body_top, "Test")
        review.publish()

        from_email = get_email_address_for_user(review.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].extra_headers['From'], from_email)
        self.assertEqual(mail.outbox[0].subject,
                         "Re: Review Request 3: Add permission checking " +
                         "for JSON API")
        self.assertValidRecipients(["admin", "doc", "dopey", "grumpy"], [])

        message = mail.outbox[0].message()
        self.assertEqual(message['Sender'], self._get_sender(review.user))

    def test_review_close_no_email(self):
        """Tests email is not generated when a review is closed and email setting is False"""
        user1 = User.objects.get(username="dopey")
        review_request = ReviewRequest.objects.create(user1, None)
        review_request.summary = "Test no email notification on close"
        review_request.publish(user1)

        # Clear the outbox.
        mail.outbox = []

        review_request.close(ReviewRequest.SUBMITTED, user1)

        # Verify that no email is generated as option is false by default
        self.assertEqual(len(mail.outbox), 0)

    def test_review_close_with_email(self):
        """Tests email is generated when a review is closed and email setting is True"""
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set("mail_send_review_close_mail", True)
        siteconfig.save()
        load_site_config()

        user1 = User.objects.get(username="dopey")
        review_request = ReviewRequest.objects.create(user1, None)
        review_request.summary = "Test email notification on close"
        review_request.publish(user1)

        # Clear the outbox.
        mail.outbox = []

        review_request.close(ReviewRequest.SUBMITTED, user1)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0].message()
        self.assertTrue("This change has been marked as submitted"
                        in message.as_string())

        # Reset settings for review close requests
        siteconfig.set("mail_send_review_close_mail", False)
        siteconfig.save()
        load_site_config()

    def testReviewReplyEmail(self):
        """Testing sending an e-mail when replying to a review"""
        review_request = ReviewRequest.objects.get(
            summary="Add permission checking for JSON API")
        review_request.publish(review_request.submitter)

        base_review = Review.objects.get(review_request=review_request,
                                         user__username="doc",
                                         base_reply_to__isnull=True)
        base_review.publish()

        # Clear the outbox.
        mail.outbox = []

        reply = Review.objects.get(base_reply_to=base_review,
                                   user__username="dopey")
        reply.publish()

        from_email = get_email_address_for_user(reply.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].extra_headers['From'], from_email)
        self.assertEqual(mail.outbox[0].subject,
                         "Re: Review Request 3: Add permission checking " +
                         "for JSON API")
        self.assertValidRecipients(["admin", "doc", "dopey", "admin"], [])

        message = mail.outbox[0].message()
        self.assertEqual(message['Sender'], self._get_sender(reply.user))

    def testUpdateReviewRequestEmail(self):
        """Testing sending an e-mail when updating a review request"""
        review_request = ReviewRequest.objects.get(
            summary="Update for cleaned_data changes")
        review_request.email_message_id = "junk"
        review_request.publish(review_request.submitter)

        from_email = get_email_address_for_user(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].extra_headers['From'], from_email)
        self.assertEqual(mail.outbox[0].subject,
                         "Re: Review Request 2: Update for cleaned_data changes")
        self.assertValidRecipients(["dopey", "doc"], ["devgroup"])

        message = mail.outbox[0].message()
        self.assertEqual(message['Sender'],
                         self._get_sender(review_request.submitter))

    def test_local_site_user_filters(self):
        """Testing sending e-mails and filtering out users not on a local site"""
        test_site = LocalSite.objects.create(name='test')

        site_user1 = User.objects.create(
            username='site_user1',
            email='site_user1@example.com')
        site_user2 = User.objects.create(
            username='site_user2',
            email='site_user2@example.com')
        site_user3 = User.objects.create(
            username='site_user3',
            email='site_user3@example.com')
        site_user4 = User.objects.create(
            username='site_user4',
            email='site_user4@example.com')
        site_user5 = User.objects.create(
            username='site_user5',
            email='site_user5@example.com')
        non_site_user1 = User.objects.create(
            username='non_site_user1',
            email='non_site_user1@example.com')
        non_site_user2 = User.objects.create(
            username='non_site_user2',
            email='non_site_user2@example.com')
        non_site_user3 = User.objects.create(
            username='non_site_user3',
            email='non_site_user3@example.com')

        test_site.admins.add(site_user1)
        test_site.users.add(site_user2)
        test_site.users.add(site_user3)
        test_site.users.add(site_user4)
        test_site.users.add(site_user5)

        group = Group.objects.create(name='my-group',
                                     display_name='My Group',
                                     local_site=test_site)
        group.users.add(site_user5)
        group.users.add(non_site_user3)

        review_request = ReviewRequest.objects.get(
            summary='Made e-mail improvements')
        review_request.local_site = test_site
        review_request.local_id = 123
        review_request.email_message_id = "junk"
        review_request.target_people = [site_user1, site_user2, site_user3,
                                        non_site_user1]
        review_request.target_groups = [group]

        review = Review.objects.create(review_request=review_request,
                                       user=site_user4)
        review.publish()

        review = Review.objects.create(review_request=review_request,
                                       user=non_site_user2)
        review.publish()

        from_email = get_email_address_for_user(review_request.submitter)

        # Now that we're set up, send another e-mail.
        mail.outbox = []
        review_request.publish(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].extra_headers['From'], from_email)
        self.assertValidRecipients(
            ['site_user1', 'site_user2', 'site_user3', 'site_user4',
             'site_user5', review_request.submitter.username], [])

        message = mail.outbox[0].message()
        self.assertEqual(message['Sender'],
                         self._get_sender(review_request.submitter))

    def _get_sender(self, user):
        return build_email_address(user.get_full_name(), self.sender)
