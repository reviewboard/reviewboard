from __future__ import unicode_literals

import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.utils.datastructures import MultiValueDict
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.accounts.models import Profile
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.diffviewer.models import FileDiff
from reviewboard.notifications.email import (SpiffyEmailMessage,
                                             build_email_address,
                                             build_recipients,
                                             get_email_address_for_user,
                                             get_email_addresses_for_group,
                                             recipients_to_addresses,
                                             send_review_mail)
from reviewboard.reviews.models import (Group,
                                        Review,
                                        ReviewRequest,
                                        ReviewRequestDraft)
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


_CONSOLE_EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


class EmailTestHelper(object):
    def setUp(self):
        super(EmailTestHelper, self).setUp()

        mail.outbox = []
        self.sender = 'noreply@example.com'

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


class GeneralEmailTests(EmailTestHelper, TestCase):
    """General unit tests for e-mail support."""

    def test_headers_from_sender(self):
        """Testing SpiffyEmailMessage From/Sender headers"""
        email = SpiffyEmailMessage(
            subject='Test email',
            text_body='This is a test.',
            html_body='<p>This is a test.</p>',
            from_email='doc@example.com',
            sender=self.sender,
            to=['sleepy@example.com'])

        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email.rb_headers)
        self.assertIn('X-Sender', email.rb_headers)
        self.assertNotIn('From', email.rb_headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertEqual(email.extra_headers['From'], 'doc@example.com')
        self.assertEqual(email.rb_headers['Sender'], self.sender)
        self.assertEqual(email.rb_headers['X-Sender'], self.sender)

        msg = email.message()
        self.assertEqual(msg['From'], 'doc@example.com')
        self.assertEqual(msg['Sender'], self.sender)
        self.assertEqual(msg['X-Sender'], self.sender)


class UserEmailTests(EmailTestHelper, TestCase):
    def setUp(self):
        super(UserEmailTests, self).setUp()

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

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.subject,
                         "New Review Board user registration for NewUser")

        self.assertEqual(email.from_email, self.sender)
        self.assertEqual(email.extra_headers['From'], settings.SERVER_EMAIL)
        self.assertEqual(email.to[0], build_email_address(admin_name,
                                                          admin_email_addr))


class ReviewRequestEmailTests(EmailTestHelper, SpyAgency, TestCase):
    """Tests the e-mail support."""

    fixtures = ['test_users']

    def setUp(self):
        super(ReviewRequestEmailTests, self).setUp()

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

    def test_review_request_email_local_site_group(self):
        """Testing sending email when a group member is part of a Local Site"""
        # This was bug 3581.
        local_site = LocalSite.objects.create(name=self.local_site_name)

        group = self.create_review_group()
        user = User.objects.get(username='grumpy')

        local_site.users.add(user)
        local_site.admins.add(user)
        local_site.save()
        group.users.add(user)
        group.save()

        review_request = self.create_review_request()
        review_request.target_groups.add(group)
        review_request.publish(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        self.assertValidRecipients(['doc', 'grumpy'])

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
        email = mail.outbox[0]
        self.assertEqual(email.from_email, self.sender)
        self.assertEqual(email.extra_headers['From'], from_email)
        self.assertEqual(email.rb_headers['X-ReviewBoard-URL'],
                         'http://example.com/')
        self.assertEqual(email.rb_headers['X-ReviewRequest-URL'],
                         'http://example.com/r/%s/'
                         % review_request.display_id)
        self.assertEqual(email.subject,
                         'Re: Review Request %s: My test review request'
                         % review_request.display_id)
        self.assertValidRecipients([
            review_request.submitter.username,
            'grumpy',
            'doc',
        ])

        message = email.message()
        self.assertEqual(message['Sender'], self._get_sender(review.user))

    @add_fixtures(['test_site'])
    def test_review_email_with_site(self):
        """Testing sending an e-mail when replying to a review request
        on a Local Site
        """
        review_request = self.create_review_request(
            summary='My test review request',
            with_local_site=True)
        review_request.target_people.add(User.objects.get(username='grumpy'))
        review_request.target_people.add(User.objects.get(username='doc'))
        review_request.publish(review_request.submitter)

        # Ensure all the reviewers are on the site.
        site = review_request.local_site
        site.users.add(*list(review_request.target_people.all()))

        # Clear the outbox.
        mail.outbox = []

        review = self.create_review(review_request=review_request)
        review.publish()

        from_email = get_email_address_for_user(review.user)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.from_email, self.sender)
        self.assertEqual(email.extra_headers['From'], from_email)
        self.assertEqual(email.rb_headers['X-ReviewBoard-URL'],
                         'http://example.com/s/local-site-1/')
        self.assertEqual(email.rb_headers['X-ReviewRequest-URL'],
                         'http://example.com/s/local-site-1/r/%s/'
                         % review_request.display_id)
        self.assertEqual(email.subject,
                         'Re: Review Request %s: My test review request'
                         % review_request.display_id)
        self.assertValidRecipients([
            review_request.submitter.username,
            'grumpy',
            'doc',
        ])

        message = email.message()
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

    def test_add_reviewer_review_request_email(self):
        """Testing limited e-mail recipients
        when adding a reviewer to an existing review request
        """
        review_request = self.create_review_request(
            summary='My test review request',
            public=True)
        review_request.email_message_id = "junk"
        review_request.target_people.add(User.objects.get(username='dopey'))
        review_request.save()

        draft = ReviewRequestDraft.create(review_request)
        draft.target_people.add(User.objects.get(username='grumpy'))
        draft.publish(user=review_request.submitter)

        from_email = get_email_address_for_user(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].extra_headers['From'], from_email)
        self.assertEqual(mail.outbox[0].subject,
                         'Re: Review Request %s: My test review request'
                         % review_request.pk)
        # The only included users should be the submitter and 'grumpy' (not
        # 'dopey', since he was already included on the review request earlier)
        self.assertValidRecipients([review_request.submitter.username,
                                    'grumpy'])

        message = mail.outbox[0].message()
        self.assertEqual(message['Sender'],
                         self._get_sender(review_request.submitter))

    def test_add_group_review_request_email(self):
        """Testing limited e-mail recipients
        when adding a group to an existing review request
        """
        existing_group = Group.objects.create(
            name='existing', mailing_list='existing@example.com')
        review_request = self.create_review_request(
            summary='My test review request',
            public=True)
        review_request.email_message_id = "junk"
        review_request.target_groups.add(existing_group)
        review_request.target_people.add(User.objects.get(username='dopey'))
        review_request.save()

        new_group = Group.objects.create(name='devgroup',
                                         mailing_list='devgroup@example.com')
        draft = ReviewRequestDraft.create(review_request)
        draft.target_groups.add(new_group)
        draft.publish(user=review_request.submitter)

        from_email = get_email_address_for_user(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].extra_headers['From'], from_email)
        self.assertEqual(mail.outbox[0].subject,
                         'Re: Review Request %s: My test review request'
                         % review_request.pk)
        # The only included users should be the submitter and 'devgroup' (not
        # 'dopey' or 'existing', since they were already included on the
        # review request earlier)
        self.assertValidRecipients([review_request.submitter.username],
                                   ['devgroup'])

        message = mail.outbox[0].message()
        self.assertEqual(message['Sender'],
                         self._get_sender(review_request.submitter))

    def test_limited_recipients_other_fields(self):
        """Testing that recipient limiting only happens when adding reviewers
        """
        review_request = self.create_review_request(
            summary='My test review request',
            public=True)
        review_request.email_message_id = "junk"
        review_request.target_people.add(User.objects.get(username='dopey'))
        review_request.save()

        draft = ReviewRequestDraft.create(review_request)
        draft.summary = 'Changed summary'
        draft.target_people.add(User.objects.get(username='grumpy'))
        draft.publish(user=review_request.submitter)

        from_email = get_email_address_for_user(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].extra_headers['From'], from_email)
        self.assertEqual(mail.outbox[0].subject,
                         'Re: Review Request %s: Changed summary'
                         % review_request.pk)
        self.assertValidRecipients([review_request.submitter.username,
                                    'dopey', 'grumpy'])

        message = mail.outbox[0].message()
        self.assertEqual(message['Sender'],
                         self._get_sender(review_request.submitter))

    def test_limited_recipients_no_email(self):
        """Testing limited e-mail recipients when operation results in zero
        recipients
        """
        review_request = self.create_review_request(
            summary='My test review request',
            public=True)
        review_request.email_message_id = "junk"
        review_request.target_people.add(User.objects.get(username='dopey'))
        review_request.save()

        profile, is_new = Profile.objects.get_or_create(
            user=review_request.submitter)
        profile.should_send_own_updates = False
        profile.save()

        draft = ReviewRequestDraft.create(review_request)
        draft.target_people.remove(User.objects.get(username='dopey'))
        draft.publish(user=review_request.submitter)

        self.assertEqual(len(mail.outbox), 0)

    def test_group_member_not_receive_email(self):
        """Testing sending review e-mails and filtering out the review
        submitter when they are part of a review group assigned to the request
        """
        # See issue 3985.
        submitter = User.objects.get(username='doc')
        profile = Profile.objects.get_or_create(user=submitter)[0]
        profile.should_send_own_updates = False
        profile.save()

        reviewer = User.objects.get(username='dopey')

        group = self.create_review_group()
        group.users.add(submitter)

        review_request = self.create_review_request(public=True)
        review_request.target_groups.add(group)
        review_request.target_people.add(reviewer)
        review_request.save()

        review = self.create_review(review_request, user=submitter)
        review.publish()

        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]

        self.assertListEqual(
            msg.to,
            [get_email_address_for_user(reviewer)])

        self.assertListEqual(msg.cc, [])

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

    def test_review_request_email_with_unicode_summary(self):
        """Testing sending a review request e-mail with a unicode subject"""
        self.spy_on(logging.exception)

        with self.settings(EMAIL_BACKEND=_CONSOLE_EMAIL_BACKEND):
            review_request = self.create_review_request()
            review_request.summary = '\ud83d\ude04'

            review_request.target_people.add(User.objects.get(
                username='grumpy'))
            review_request.target_people.add(User.objects.get(username='doc'))
            review_request.publish(review_request.submitter)

        self.assertIsNotNone(review_request.email_message_id)
        self.assertFalse(logging.exception.spy.called)

    def test_review_request_email_with_unicode_description(self):
        """Testing sending a review request e-mail with a unicode
        description
        """
        self.spy_on(logging.exception)

        with self.settings(EMAIL_BACKEND=_CONSOLE_EMAIL_BACKEND):
            review_request = self.create_review_request()
            review_request.description = '\ud83d\ude04'

            review_request.target_people.add(
                User.objects.get(username='grumpy'))
            review_request.target_people.add(
                User.objects.get(username='doc'))
            review_request.publish(review_request.submitter)

        self.assertIsNotNone(review_request.email_message_id)
        self.assertFalse(logging.exception.spy.called)

    @add_fixtures(['test_scmtools'])
    def test_review_request_email_with_added_file(self):
        """Testing sending a review request e-mail with added files in the
        diffset
        """
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(repository=repository)
        diffset = self.create_diffset(review_request=review_request)
        filediff = self.create_filediff(diffset=diffset,
                                        source_file='/dev/null',
                                        source_revision=PRE_CREATION)

        review_request.publish(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertTrue('X-ReviewBoard-Diff-For' in message.rb_headers)
        diff_headers = message.rb_headers.getlist('X-ReviewBoard-Diff-For')

        self.assertEqual(len(diff_headers), 1)
        self.assertFalse(filediff.source_file in diff_headers)
        self.assertTrue(filediff.dest_file in diff_headers)

    @add_fixtures(['test_scmtools'])
    def test_review_request_email_with_deleted_file(self):
        """Testing sending a review request e-mail with deleted files in the
        diffset
        """
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(repository=repository)
        diffset = self.create_diffset(review_request=review_request)
        filediff = self.create_filediff(diffset=diffset,
                                        dest_file='/dev/null',
                                        status=FileDiff.DELETED)

        review_request.publish(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertTrue('X-ReviewBoard-Diff-For' in message.rb_headers)
        diff_headers = message.rb_headers.getlist('X-ReviewBoard-Diff-For')

        self.assertEqual(len(diff_headers), 1)
        self.assertTrue(filediff.source_file in diff_headers)
        self.assertFalse(filediff.dest_file in diff_headers)

    @add_fixtures(['test_scmtools'])
    def test_review_request_email_with_moved_file(self):
        """Testing sending a review request e-mail with moved files in the
        diffset
        """
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(repository=repository)
        diffset = self.create_diffset(review_request=review_request)
        filediff = self.create_filediff(diffset=diffset,
                                        source_file='foo',
                                        dest_file='bar',
                                        status=FileDiff.MOVED)

        review_request.publish(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertTrue('X-ReviewBoard-Diff-For' in message.rb_headers)
        diff_headers = message.rb_headers.getlist('X-ReviewBoard-Diff-For')

        self.assertEqual(len(diff_headers), 2)
        self.assertTrue(filediff.source_file in diff_headers)
        self.assertTrue(filediff.dest_file in diff_headers)

    @add_fixtures(['test_scmtools'])
    def test_review_request_email_with_copied_file(self):
        """Testing sending a review request e-mail with copied files in the
        diffset
        """
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(repository=repository)
        diffset = self.create_diffset(review_request=review_request)
        filediff = self.create_filediff(diffset=diffset,
                                        source_file='foo',
                                        dest_file='bar',
                                        status=FileDiff.COPIED)

        review_request.publish(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertTrue('X-ReviewBoard-Diff-For' in message.rb_headers)
        diff_headers = message.rb_headers.getlist('X-ReviewBoard-Diff-For')

        self.assertEqual(len(diff_headers), 2)
        self.assertTrue(filediff.source_file in diff_headers)
        self.assertTrue(filediff.dest_file in diff_headers)

    @add_fixtures(['test_scmtools'])
    def test_review_request_email_with_multiple_files(self):
        """Testing sending a review request e-mail with multiple files in the
        diffset
        """
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(repository=repository)
        diffset = self.create_diffset(review_request=review_request)
        filediffs = [
            self.create_filediff(diffset=diffset,
                                 source_file='foo',
                                 dest_file='bar',
                                 status=FileDiff.MOVED),
            self.create_filediff(diffset=diffset,
                                 source_file='baz',
                                 dest_file='/dev/null',
                                 status=FileDiff.DELETED)
        ]

        review_request.publish(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertTrue('X-ReviewBoard-Diff-For' in message.rb_headers)
        diff_headers = message.rb_headers.getlist('X-ReviewBoard-Diff-For')

        self.assertEqual(len(diff_headers), 3)
        self.assertTrue(filediffs[0].source_file in diff_headers)
        self.assertTrue(filediffs[0].dest_file in diff_headers)
        self.assertTrue(filediffs[1].source_file in diff_headers)
        self.assertFalse(filediffs[1].dest_file in diff_headers)

    def test_extra_headers_dict(self):
        """Testing sending extra headers as a dict with an e-mail message"""
        review_request = self.create_review_request()

        submitter = review_request.submitter

        send_review_mail(submitter,
                         review_request,
                         'Foo',
                         None,
                         [submitter],
                         [],
                         'notifications/review_request_email.txt',
                         'notifications/review_request_email.html',
                         extra_headers={
                             'X-Foo': 'Bar'
                         })

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertIn('X-Foo', message.rb_headers)
        self.assertEqual(message.rb_headers['X-Foo'], 'Bar')

    def test_extra_headers_multivalue_dict(self):
        """Testing sending extra headers as a MultiValueDict with an e-mail
        message
        """
        header_values = ['Bar', 'Baz']

        review_request = self.create_review_request()

        submitter = review_request.submitter

        send_review_mail(review_request.submitter,
                         review_request,
                         'Foo',
                         None,
                         [submitter],
                         [],
                         'notifications/review_request_email.txt',
                         'notifications/review_request_email.html',
                         extra_headers=MultiValueDict({
                             'X-Foo': header_values,
                         }))

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertIn('X-Foo', message.rb_headers)
        self.assertEqual(set(message.rb_headers.getlist('X-Foo')),
                         set(header_values))

    def test_review_no_shipit_headers(self):
        """Testing sending a review e-mail without a 'Ship It!'"""
        review_request = self.create_review_request(public=True)

        self.create_review(review_request,
                           body_top=Review.SHIP_IT_TEXT,
                           body_bottom='',
                           publish=True)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertNotIn('X-ReviewBoard-ShipIt', message.rb_headers)
        self.assertNotIn('X-ReviewBoard-ShipIt-Only', message.rb_headers)

    def test_review_shipit_only_headers(self):
        """Testing sending a review e-mail with only a 'Ship It!'"""
        review_request = self.create_review_request(public=True)

        self.create_review(review_request,
                           body_top=Review.SHIP_IT_TEXT,
                           body_bottom='',
                           ship_it=True,
                           publish=True)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertIn('X-ReviewBoard-ShipIt', message.rb_headers)
        self.assertIn('X-ReviewBoard-ShipIt-Only', message.rb_headers)

    def test_review_shipit_only_headers_no_text(self):
        """Testing sending a review e-mail with only a 'Ship It!' and no text
        """
        review_request = self.create_review_request(public=True)

        self.create_review(review_request,
                           body_top='',
                           body_bottom='',
                           ship_it=True,
                           publish=True)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertIn('X-ReviewBoard-ShipIt', message.rb_headers)
        self.assertIn('X-ReviewBoard-ShipIt-Only', message.rb_headers)

    def test_review_shipit_headers_custom_top_text(self):
        """Testing sending a review e-mail with a 'Ship It' and custom top text
        """
        review_request = self.create_review_request(public=True)

        self.create_review(review_request,
                           body_top='Some general information.',
                           body_bottom='',
                           ship_it=True,
                           publish=True)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertIn('X-ReviewBoard-ShipIt', message.rb_headers)
        self.assertNotIn('X-ReviewBoard-ShipIt-Only', message.rb_headers)

    def test_review_shipit_headers_bottom_text(self):
        """Testing sending a review e-mail with a 'Ship It' and bottom text"""
        review_request = self.create_review_request(public=True)

        self.create_review(review_request,
                           body_top=Review.SHIP_IT_TEXT,
                           body_bottom='Some comments',
                           ship_it=True,
                           publish=True)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertIn('X-ReviewBoard-ShipIt', message.rb_headers)
        self.assertNotIn('X-ReviewBoard-ShipIt-Only', message.rb_headers)

    @add_fixtures(['test_scmtools'])
    def test_review_shipit_headers_comments(self):
        """Testing sending a review e-mail with a 'Ship It' and diff comments
        """
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(repository=repository,
                                                    public=True)

        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        review = self.create_review(review_request,
                                    body_top=Review.SHIP_IT_TEXT,
                                    body_bottom='',
                                    ship_it=True,
                                    publish=False)

        self.create_diff_comment(review, filediff)

        review.publish()

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertIn('X-ReviewBoard-ShipIt', message.rb_headers)
        self.assertNotIn('X-ReviewBoard-ShipIt-Only', message.rb_headers)

    def test_review_shipit_headers_attachment_comments(self):
        """Testing sending a review e-mail with a 'Ship It' and file attachment
        comments
        """
        review_request = self.create_review_request(public=True)

        file_attachment = self.create_file_attachment(review_request)

        review = self.create_review(review_request,
                                    body_top=Review.SHIP_IT_TEXT,
                                    body_bottom='',
                                    ship_it=True,
                                    publish=False)

        self.create_file_attachment_comment(review, file_attachment)

        review.publish()

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertIn('X-ReviewBoard-ShipIt', message.rb_headers)
        self.assertNotIn('X-ReviewBoard-ShipIt-Only', message.rb_headers)

    def test_review_shipit_headers_screenshot_comments(self):
        """Testing sending a review e-mail with a 'Ship It' and screenshot
        comments
        """
        review_request = self.create_review_request(public=True)

        screenshot = self.create_screenshot(review_request)

        review = self.create_review(review_request,
                                    body_top=Review.SHIP_IT_TEXT,
                                    body_bottom='',
                                    ship_it=True,
                                    publish=False)

        self.create_screenshot_comment(review, screenshot)

        review.publish()

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertIn('X-ReviewBoard-ShipIt', message.rb_headers)
        self.assertNotIn('X-ReviewBoard-ShipIt-Only', message.rb_headers)

    def _get_sender(self, user):
        return build_email_address(user.get_full_name(), self.sender)


class EmailUtilsTests(TestCase):
    """Testing e-mail utilities that do not send e-mails."""

    def test_recipients_to_addresses_with_string_address(self):
        """Testing generating addresses from recipients with string recipients
        """
        with self.assertRaises(AssertionError):
            recipients_to_addresses(['foo@example.com'])

    @add_fixtures(['test_users'])
    def test_recipients_to_addresses_with_users(self):
        """Testing generating addresses from recipients with user recipients
        """
        users = list(User.objects.filter(username__in=['doc', 'grumpy']))

        addresses = recipients_to_addresses(users)
        self.assertEqual(len(addresses), 2)

        expected_addresses = set(
            get_email_address_for_user(u)
            for u in users
        )

        self.assertEqual(addresses, expected_addresses)

    def test_recipients_to_addresses_with_groups_single_mailinglist(self):
        """Testing generating addresses from recipients that are groups with a
        single mailing list address
        """
        groups = [
            Group(name='group1', display_name='Group One',
                  mailing_list='group1@example.com'),
            Group(name='group2', display_name='Group Two',
                  mailing_list='group2@example.com'),
        ]

        addresses = recipients_to_addresses(groups)
        self.assertEqual(len(addresses), 2)

        expected_addresses = set(sum(
            (
                get_email_addresses_for_group(group)
                for group in groups
            ),
            []))

        self.assertEqual(addresses, expected_addresses)

    def test_recipients_to_addresses_with_groups_many_mailinglist(self):
        """Testing generating addresses from recipients that are groups with
        multiple mailing list addresses
        """
        groups = [
            Group(name='group1', display_name='Group One',
                  mailing_list='group1a@example.com,group1b@example.com'),
            Group(name='group2', display_name='Group Two',
                  mailing_list='group2a@example.com,group2b@example.com'),
        ]

        addresses = recipients_to_addresses(groups)
        self.assertEqual(len(addresses), 4)

        expected_addresses = set(sum(
            (
                get_email_addresses_for_group(group)
                for group in groups
            ),
            []))

        self.assertEqual(addresses, expected_addresses)

    @add_fixtures(['test_users'])
    def test_recipients_to_addresses_with_groups_and_users(self):
        """Testing generating addresses from recipients that are users and
        groups with mailing list addresses
        """
        groups = [
            Group(name='group1', display_name='Group One',
                  mailing_list='group1@example.com'),
            Group(name='group2', display_name='Group Two',
                  mailing_list='group2@example.com'),
        ]

        users = list(User.objects.filter(username__in=['doc', 'grumpy']).all())

        addresses = recipients_to_addresses(groups + users)
        self.assertEqual(len(addresses), 4)

        user_addresses = [
            get_email_address_for_user(u)
            for u in users
        ]

        group_addresses = sum(
            (
                get_email_addresses_for_group(group)
                for group in groups
            ),
            [])

        self.assertEqual(addresses,
                         set(user_addresses + group_addresses))

    def test_recipients_to_addresses_with_groups_with_members(self):
        """Testing generating addresses from recipients that are groups with
        no mailing list addresses
        """
        group1 = Group.objects.create(name='group1')
        group2 = Group.objects.create(name='group2')

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two')

        group1.users = [user1]
        group2.users = [user2]

        addresses = recipients_to_addresses([group1, group2])

        expected_addresses = set([
            get_email_address_for_user(user1),
            get_email_address_for_user(user2),
        ])

        self.assertEqual(addresses, expected_addresses)

    def test_recipients_to_addresses_with_groups_local_site(self):
        """Testing generating addresses from recipients that are groups in
        local sites
        """
        local_site1 = LocalSite.objects.create(name='local-site1')
        local_site2 = LocalSite.objects.create(name='local-site2')

        group1 = Group.objects.create(name='group1', local_site=local_site1)
        group2 = Group.objects.create(name='group2', local_site=local_site2)

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two')

        local_site1.users = [user1]

        group1.users = [user1]
        group2.users = [user2]

        addresses = recipients_to_addresses([group1, group2])
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses, set([get_email_address_for_user(user1)]))

    def test_recipients_to_addresses_with_groups_inactive_members(self):
        """Testing generating addresses form recipients that are groups with
        inactive members
        """
        group1 = self.create_review_group('group1')
        group2 = self.create_review_group('group2')

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', is_active=False)

        group1.users = [user1]
        group2.users = [user2]

        addresses = recipients_to_addresses([group1, group2])
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses, set([get_email_address_for_user(user1)]))

    def test_recipients_to_addresses_groups_local_site_inactive_members(self):
        """Testing generating addresses from recipients that are groups in
        local sites that have inactive members
        """
        local_site1 = LocalSite.objects.create(name='local-site1')
        local_site2 = LocalSite.objects.create(name='local-site2')

        group1 = self.create_review_group('group1', local_site=local_site1)
        group2 = self.create_review_group('group2', local_site=local_site2)

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', is_active=False)

        local_site1.users = [user1]
        local_site2.users = [user2]

        group1.users = [user1]
        group2.users = [user2]

        addresses = recipients_to_addresses([group1, group2])
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses, set([get_email_address_for_user(user1)]))

    @add_fixtures(['test_users'])
    def test_build_recipients_user_receive_email(self):
        """Testing building recipients for a review request where the user
        wants to receive e-mail
        """
        review_request = self.create_review_request()
        submitter = review_request.submitter

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(to, set([submitter]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_user_not_receive_email(self):
        """Testing building recipients for a review request where the user
        does not want to receive e-mail
        """
        review_request = self.create_review_request()
        submitter = review_request.submitter

        profile = submitter.get_profile()
        profile.should_send_email = False
        profile.save()

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(len(to), 0)
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_user_not_receive_own_email(self):
        """Testing building recipients for a review request where the user
        does not want to receive e-mail about their updates
        """
        review_request = self.create_review_request()
        submitter = review_request.submitter

        profile = submitter.get_profile()
        profile.should_send_own_updates = False
        profile.save()

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(len(to), 0)
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_target_people_not_receive_own_email(self):
        """Testing building recipieints for a review request where the
        submitter is a reviewer and doesn't want to receive e-mail about their
        updates
        """
        review_request = self.create_review_request()
        submitter = review_request.submitter

        review_request.target_people = [submitter]

        profile = submitter.get_profile()
        profile.should_send_own_updates = False
        profile.save()

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(len(to), 0)
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_extra_recipient_user_not_receive_own_email(self):
        """Testing building recipients for a review request where the
        submitter is a reviewer and doesn't want to receive e-mail about their
        updates
        """
        review_request = self.create_review_request()
        submitter = review_request.submitter

        profile = submitter.get_profile()
        profile.should_send_own_updates = False
        profile.save()

        to, cc = build_recipients(submitter, review_request, [submitter])

        self.assertEqual(len(to), 0)
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_target_people_and_groups(self):
        """Testing building recipients for a review request where there are
        target users and groups
        """
        group = self.create_review_group()
        user = User.objects.get(username='grumpy')

        review_request = self.create_review_request()
        review_request.target_people = [user]
        review_request.target_groups = [group]

        submitter = review_request.submitter

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(to, set([user]))
        self.assertEqual(cc, set([submitter, group]))

    @add_fixtures(['test_users'])
    def test_build_recipients_target_people_inactive_and_groups(self):
        """Testing building recipients for a review request where there are
        target groups and inactive target users
        """
        group = self.create_review_group()
        user = User.objects.create(username='user', first_name='User',
                                   last_name='Foo', is_active=False)

        review_request = self.create_review_request()
        review_request.target_people = [user]
        review_request.target_groups = [group]

        submitter = review_request.submitter

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(to, set([submitter, group]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_target_groups(self):
        """Testing build recipients for a review request where there are target
        groups
        """
        group1 = self.create_review_group('group1')
        group2 = self.create_review_group('group2')

        review_request = self.create_review_request()
        review_request.target_groups = [group1, group2]
        submitter = review_request.submitter

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(len(to), 3)
        self.assertEqual(to, set([submitter, group1, group2]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_target_people(self):
        """Testing building recipients for a review request with target people
        """
        review_request = self.create_review_request()
        submitter = review_request.submitter

        grumpy = User.objects.get(username='grumpy')
        review_request.target_people = [grumpy]

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(to, set([grumpy]))
        self.assertEqual(cc, set([submitter]))

    @add_fixtures(['test_users'])
    def test_build_recipients_target_people_inactive(self):
        """Testing building recipients for a review request with target people
        who are inactive
        """
        review_request = self.create_review_request()
        submitter = review_request.submitter

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', is_active=False)

        review_request.target_people = [user1, user2]

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(to, set([user1]))
        self.assertEqual(cc, set([submitter]))

    @add_fixtures(['test_users'])
    def test_build_recipients_target_people_no_email(self):
        """Testing building recipients for a review request with target people
        who don't receive e-mail
        """
        review_request = self.create_review_request()
        submitter = review_request.submitter

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two')

        Profile.objects.create(user=user2, should_send_email=False)

        review_request.target_people = [user1, user2]

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(to, set([user1]))
        self.assertEqual(cc, set([submitter]))

    @add_fixtures(['test_users'])
    def test_build_recipients_target_people_local_site(self):
        """Testing building recipients for a review request where the target
        people are in local sites
        """
        local_site = LocalSite.objects.create(name=self.local_site_name)

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two')

        local_site.users = [user1]

        review_request = self.create_review_request(with_local_site=True)
        review_request.target_people = [user1, user2]

        submitter = review_request.submitter

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(to, set([user1]))
        self.assertEqual(cc, set([submitter]))

    @add_fixtures(['test_users'])
    def test_build_recipients_target_people_local_site_inactive(self):
        """Testing building recipients for a review request where the target
        people are in local sites and are inactive
        """
        local_site = LocalSite.objects.create(name=self.local_site_name)

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', is_active=False)

        local_site.users = [user1, user2]

        review_request = self.create_review_request(with_local_site=True)
        review_request.target_people = [user1, user2]

        submitter = review_request.submitter

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(to, set([user1]))
        self.assertEqual(cc, set([submitter]))

    @add_fixtures(['test_users'])
    def test_build_recipients_target_people_local_site_no_email(self):
        """Testing building recipients for a review request where the target
        people are in local sites don't receieve e-mail
        """
        local_site = LocalSite.objects.create(name=self.local_site_name)

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two')

        Profile.objects.create(user=user2,
                               should_send_email=False)

        local_site.users = [user1, user2]

        review_request = self.create_review_request(with_local_site=True)
        review_request.target_people = [user1, user2]

        submitter = review_request.submitter

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(to, set([user1]))
        self.assertEqual(cc, set([submitter]))

    @add_fixtures(['test_users'])
    def test_build_recipients_limit_to(self):
        """Testing building recipients with a limited recipients list"""
        dopey = User.objects.get(username='dopey')
        grumpy = User.objects.get(username='grumpy')
        group = self.create_review_group()

        review_request = self.create_review_request()
        submitter = review_request.submitter

        review_request.target_people = [dopey]
        review_request.target_groups = [group]

        to, cc = build_recipients(submitter, review_request,
                                  limit_recipients_to=[grumpy])

        self.assertEqual(to, set([submitter, grumpy]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_limit_to_inactive(self):
        """Testing building recipients with a limited recipients list that
        contains inactive users
        """
        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', is_active=False)

        review_request = self.create_review_request()
        submitter = review_request.submitter

        to, cc = build_recipients(submitter, review_request,
                                  limit_recipients_to=[user1, user2])

        self.assertEqual(to, set([submitter, user1]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_limit_to_local_site(self):
        """Testing building recipients with a limited recipients list that
        contains users in local sites
        """
        local_site1 = LocalSite.objects.create(name='local-site1')
        local_site2 = LocalSite.objects.create(name='local-site2')

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two')

        local_site1.users = [user1]
        local_site2.users = [user2]

        review_request = self.create_review_request(local_site=local_site1)
        submitter = review_request.submitter

        to, cc = build_recipients(submitter, review_request,
                                  limit_recipients_to=[user1, user2])

        self.assertEqual(to, set([submitter, user1]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_extra_recipients(self):
        """Testing building recipients with an extra recipients list"""
        review_request = self.create_review_request()
        submitter = review_request.submitter

        grumpy = User.objects.get(username='grumpy')

        to, cc = build_recipients(submitter, review_request,
                                  extra_recipients=[grumpy])

        self.assertEqual(to, set([submitter, grumpy]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_extra_recipients_inactive(self):
        """Testing building recipients with an extra recipients list that
        contains inactive users
        """
        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', is_active=False)

        review_request = self.create_review_request()
        submitter = review_request.submitter

        to, cc = build_recipients(submitter, review_request,
                                  extra_recipients=[user1, user2])

        self.assertEqual(to, set([submitter, user1]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_extra_recipients_local_site(self):
        """Testing building recipients with an extra recipients list that
        contains users in local sites
        """
        local_site1 = LocalSite.objects.create(name='local-site1')
        local_site2 = LocalSite.objects.create(name='local-site2')

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two')

        local_site1.users = [user1]
        local_site2.users = [user2]

        review_request = self.create_review_request(local_site=local_site1)
        submitter = review_request.submitter

        to, cc = build_recipients(submitter, review_request,
                                  extra_recipients=[user1, user2])

        self.assertEqual(to, set([submitter, user1]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_extra_recipients_and_limit_to(self):
        """Testing building recipients with an extra recipients list and
        a limited recipients list
        """
        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two')
        user3 = User.objects.create(username='user3', first_name='User',
                                    last_name='Three')

        group = self.create_review_group()

        review_request = self.create_review_request()
        submitter = review_request.submitter
        review_request.target_people = [user3]
        review_request.target_groups = [group]

        to, cc = build_recipients(submitter, review_request,
                                  extra_recipients=[user1],
                                  limit_recipients_to=[user2])

        self.assertEqual(to, set([submitter, user2]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_extra_recipients_and_limit_to_inactive(self):
        """Testing building recipients with an extra recipients list and a
        limited recipients list that contains inactive users
        """
        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', is_active=False)
        user3 = User.objects.create(username='user3', first_name='User',
                                    last_name='Three')

        group = self.create_review_group()

        review_request = self.create_review_request()
        submitter = review_request.submitter
        review_request.target_people = [user3]
        review_request.target_groups = [group]

        to, cc = build_recipients(submitter, review_request,
                                  extra_recipients=[user1],
                                  limit_recipients_to=[user2])

        self.assertEqual(to, set([submitter]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_extra_recipients_and_limit_to_local_site(self):
        """Testing building recipients with an extra recipients list and a
        limited recipients list that contains users in local sites
        """
        local_site1 = LocalSite.objects.create(name='local-site1')
        local_site2 = LocalSite.objects.create(name='local-site2')

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two')
        user3 = User.objects.create(username='user3', first_name='User',
                                    last_name='Three')

        local_site1.users = [user1, user3]
        local_site2.users = [user2]

        group = self.create_review_group()

        review_request = self.create_review_request(local_site=local_site1)
        submitter = review_request.submitter
        review_request.target_people = [user3]
        review_request.target_groups = [group]

        to, cc = build_recipients(submitter, review_request,
                                  extra_recipients=[user1],
                                  limit_recipients_to=[user2])

        self.assertEqual(to, set([submitter]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_starred(self):
        """Testing building recipients where the review request has been
        starred by a user
        """
        review_request = self.create_review_request()
        submitter = review_request.submitter

        grumpy = User.objects.get(username='grumpy')
        profile = grumpy.get_profile()
        profile.starred_review_requests = [review_request]
        profile.save()

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(to, set([submitter, grumpy]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_starred_inactive(self):
        """Testing building recipients where the review request has been
        starred by users that may be inactive
        """
        review_request = self.create_review_request()
        submitter = review_request.submitter

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', is_active=False)

        profile1 = Profile.objects.create(user=user1)
        profile1.starred_review_requests = [review_request]

        profile2 = Profile.objects.create(user=user2)
        profile2.starred_review_requests = [review_request]

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(to, set([submitter, user1]))
        self.assertEqual(len(cc), 0)

    @add_fixtures(['test_users'])
    def test_build_recipients_starred_local_site(self):
        """Testing building recipients where the review request has been
        starred by users that are in local sites
        """
        local_site1 = LocalSite.objects.create(name='local-site1')
        local_site2 = LocalSite.objects.create(name='local-site2')

        review_request = self.create_review_request(local_site=local_site1)
        submitter = review_request.submitter

        user1 = User.objects.create(username='user1', first_name='User',
                                    last_name='One')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two')

        local_site1.users = [user1]
        local_site2.users = [user2]

        profile1 = Profile.objects.create(user=user1)
        profile1.starred_review_requests = [review_request]

        profile2 = Profile.objects.create(user=user2)
        profile2.starred_review_requests = [review_request]

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(to, set([submitter, user1]))
        self.assertEqual(len(cc), 0)
