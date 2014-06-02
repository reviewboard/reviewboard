from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin.siteconfig import load_site_config
from reviewboard.notifications.email import (build_email_address,
                                             get_email_address_for_user,
                                             get_email_addresses_for_group)
from reviewboard.reviews.models import Group, Review, ReviewRequest
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class EmailTestHelper(object):
    def assertValidRecipients(self, user_list, group_list=[]):
        recipient_list = mail.outbox[0].to + mail.outbox[0].cc
        self.assertEqual(len(recipient_list), len(user_list) + len(group_list))

        for user in user_list:
            self.assertTrue(get_email_address_for_user(
                User.objects.get(username=user)) in recipient_list,
                "user %s was not found in the recipient list" % user)

        groups = Group.objects.filter(name__in=group_list, local_site=None)
        for group in groups:
            for address in get_email_addresses_for_group(group):
                self.assertTrue(
                    address in recipient_list,
                    "group %s was not found in the recipient list" % address)


class UserEmailTests(TestCase, EmailTestHelper):
    def setUp(self):
        super(UserEmailTests, self).setUp()

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
    fixtures = ['test_users']

    def setUp(self):
        super(ReviewRequestEmailTests, self).setUp()

        mail.outbox = []
        self.sender = 'noreply@example.com'

        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set("mail_send_review_mail", True)
        siteconfig.set("mail_default_from", self.sender)
        siteconfig.save()
        load_site_config()

    def test_new_review_request_email(self):
        """Testing sending an e-mail when creating a new review request"""
        review_request = self.create_review_request(
            summary='My test review request')
        review_request.target_people.add(User.objects.get(username='grumpy'))
        review_request.target_people.add(User.objects.get(username='doc'))
        review_request.publish(review_request.submitter)

        from_email = get_email_address_for_user(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].extra_headers['From'], from_email)
        self.assertEqual(mail.outbox[0].subject,
                         'Review Request %s: My test review request'
                         % review_request.pk)
        self.assertValidRecipients(['grumpy', 'doc'])

        message = mail.outbox[0].message()
        self.assertEqual(message['Sender'],
                         self._get_sender(review_request.submitter))

    def test_review_email(self):
        """Testing sending an e-mail when replying to a review request"""
        review_request = self.create_review_request(
            summary='My test review request')
        review_request.target_people.add(User.objects.get(username='grumpy'))
        review_request.target_people.add(User.objects.get(username='doc'))
        review_request.publish(review_request.submitter)

        # Clear the outbox.
        mail.outbox = []

        review = self.create_review(review_request=review_request)
        review.publish()

        from_email = get_email_address_for_user(review.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].extra_headers['From'], from_email)
        self.assertEqual(mail.outbox[0].subject,
                         'Re: Review Request %s: My test review request'
                         % review_request.pk)
        self.assertValidRecipients([
            review_request.submitter.username,
            'grumpy',
            'doc',
        ])

        message = mail.outbox[0].message()
        self.assertEqual(message['Sender'], self._get_sender(review.user))

    def test_profile_should_send_email_setting(self):
        """Testing the Profile.should_send_email setting"""
        grumpy = User.objects.get(username='grumpy')
        profile = grumpy.get_profile()
        profile.should_send_email = False
        profile.save()

        review_request = self.create_review_request(
            summary='My test review request')
        review_request.target_people.add(grumpy)
        review_request.target_people.add(User.objects.get(username='doc'))
        review_request.publish(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        self.assertValidRecipients(['doc'])

    def test_review_close_no_email(self):
        """Tests e-mail is not generated when a review is closed and e-mail
        setting is False
        """
        review_request = self.create_review_request()
        review_request.publish(review_request.submitter)

        # Clear the outbox.
        mail.outbox = []

        review_request.close(ReviewRequest.SUBMITTED, review_request.submitter)

        # Verify that no email is generated as option is false by default
        self.assertEqual(len(mail.outbox), 0)

    def test_review_close_with_email(self):
        """Tests e-mail is generated when a review is closed and e-mail setting
        is True
        """
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set("mail_send_review_close_mail", True)
        siteconfig.save()
        load_site_config()

        review_request = self.create_review_request()
        review_request.publish(review_request.submitter)

        # Clear the outbox.
        mail.outbox = []

        review_request.close(ReviewRequest.SUBMITTED, review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0].message()
        self.assertTrue("This change has been marked as submitted"
                        in message.as_string())

        # Reset settings for review close requests
        siteconfig.set("mail_send_review_close_mail", False)
        siteconfig.save()
        load_site_config()

    def test_review_reply_email(self):
        """Testing sending an e-mail when replying to a review"""
        review_request = self.create_review_request(
            summary='My test review request')
        review_request.publish(review_request.submitter)

        base_review = self.create_review(review_request=review_request)
        base_review.publish()

        # Clear the outbox.
        mail.outbox = []

        reply = self.create_reply(base_review)
        reply.publish()

        from_email = get_email_address_for_user(reply.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].extra_headers['From'], from_email)
        self.assertEqual(mail.outbox[0].subject,
                         'Re: Review Request %s: My test review request'
                         % review_request.pk)
        self.assertValidRecipients([
            review_request.submitter.username,
            base_review.user.username,
            reply.user.username,
        ])

        message = mail.outbox[0].message()
        self.assertEqual(message['Sender'], self._get_sender(reply.user))

    def test_update_review_request_email(self):
        """Testing sending an e-mail when updating a review request"""
        group = Group.objects.create(name='devgroup',
                                     mailing_list='devgroup@example.com')

        review_request = self.create_review_request(
            summary='My test review request')
        review_request.target_groups.add(group)
        review_request.email_message_id = "junk"
        review_request.publish(review_request.submitter)

        from_email = get_email_address_for_user(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].extra_headers['From'], from_email)
        self.assertEqual(mail.outbox[0].subject,
                         'Re: Review Request %s: My test review request'
                         % review_request.pk)
        self.assertValidRecipients([review_request.submitter.username],
                                   ['devgroup'])

        message = mail.outbox[0].message()
        self.assertEqual(message['Sender'],
                         self._get_sender(review_request.submitter))

    def test_local_site_user_filters(self):
        """Testing sending e-mails and filtering out users not on a local site
        """
        test_site = LocalSite.objects.create(name=self.local_site_name)

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

        review_request = self.create_review_request(with_local_site=True,
                                                    local_id=123)
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
