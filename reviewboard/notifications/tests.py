from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.template import TemplateSyntaxError
from django.utils.six.moves.urllib.request import urlopen
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.accounts.models import Profile
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.notifications.email import (build_email_address,
                                             get_email_address_for_user,
                                             get_email_addresses_for_group)
from reviewboard.notifications.models import WebHookTarget
from reviewboard.notifications.webhooks import (FakeHTTPRequest,
                                                dispatch_webhook_event,
                                                render_custom_content)
from reviewboard.reviews.models import (Group,
                                        Review,
                                        ReviewRequest,
                                        ReviewRequestDraft)
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

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
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
        self.assertEqual(email.extra_headers['X-ReviewBoard-URL'],
                         'http://example.com/')
        self.assertEqual(email.extra_headers['X-ReviewRequest-URL'],
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
        self.assertEqual(email.extra_headers['X-ReviewBoard-URL'],
                         'http://example.com/s/local-site-1/')
        self.assertEqual(email.extra_headers['X-ReviewRequest-URL'],
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
        review_request = self.create_review_request()
        review_request.summary = '\ud83d\ude04'.encode('utf-8')

        review_request.target_people.add(User.objects.get(username='grumpy'))
        review_request.target_people.add(User.objects.get(username='doc'))
        review_request.publish(review_request.submitter)

        from_email = get_email_address_for_user(review_request.submitter)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].extra_headers['From'], from_email)
        self.assertEqual(mail.outbox[0].subject,
                         'Review Request %s: \ud83d\ude04'
                         % review_request.pk)
        self.assertValidRecipients(['grumpy', 'doc'])

    def _get_sender(self, user):
        return build_email_address(user.get_full_name(), self.sender)


class WebHookCustomContentTests(TestCase):
    """Unit tests for render_custom_content."""
    def test_with_valid_template(self):
        """Tests render_custom_content with a valid template"""
        s = render_custom_content(
            '{% if mybool %}{{s1}}{% else %}{{s2}}{% endif %}',
            {
                'mybool': True,
                's1': 'Hi!',
                's2': 'Bye!',
            })

        self.assertEqual(s, 'Hi!')

    def test_with_blocked_block_tag(self):
        """Tests render_custom_content with blocked {% block %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'block'"):
            render_custom_content('{% block foo %}{% endblock %})')

    def test_with_blocked_debug_tag(self):
        """Tests render_custom_content with blocked {% debug %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'debug'"):
            render_custom_content('{% debug %}')

    def test_with_blocked_extends_tag(self):
        """Tests render_custom_content with blocked {% extends %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'extends'"):
            render_custom_content('{% extends "base.html" %}')

    def test_with_blocked_include_tag(self):
        """Tests render_custom_content with blocked {% include %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'include'"):
            render_custom_content('{% include "base.html" %}')

    def test_with_blocked_load_tag(self):
        """Tests render_custom_content with blocked {% load %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'load'"):
            render_custom_content('{% load i18n %}')

    def test_with_blocked_ssi_tag(self):
        """Tests render_custom_content with blocked {% ssi %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'ssi'"):
            render_custom_content('{% ssi "foo.html" %}')

    def test_with_unknown_vars(self):
        """Tests render_custom_content with unknown variables"""
        s = render_custom_content('{{settings.DEBUG}};{{settings.DATABASES}}')
        self.assertEqual(s, ';')


class WebHookDispatchTests(SpyAgency, TestCase):
    """Unit tests for dispatching webhooks."""
    ENDPOINT_URL = 'http://example.com/endpoint/'

    def test_dispatch_custom_payload(self):
        """Test dispatch_webhook_event with custom payload"""
        custom_content = (
            '{\n'
            '{% for i in items %}'
            '  "item{{i}}": true{% if not forloop.last %},{% endif %}\n'
            '{% endfor %}'
            '}')
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON,
                                use_custom_content=True,
                                custom_content=custom_content)

        self._test_dispatch(
            handler,
            'my-event',
            {
                'items': [1, 2, 3],
            },
            'application/json',
            ('{\n'
             '  "item1": true,\n'
             '  "item2": true,\n'
             '  "item3": true\n'
             '}'))

    def test_dispatch_form_data(self):
        """Test dispatch_webhook_event with Form Data payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_FORM_DATA)

        self._test_dispatch(
            handler,
            'my-event',
            {
                'items': [1, 2, 3],
            },
            'application/x-www-form-urlencoded',
            'payload=%7B%22items%22%3A+%5B1%2C+2%2C+3%5D%7D')

    def test_dispatch_json(self):
        """Test dispatch_webhook_event with JSON payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON)

        self._test_dispatch(
            handler,
            'my-event',
            {
                'items': [1, 2, 3],
            },
            'application/json',
            '{"items": [1, 2, 3]}')

    def test_dispatch_xml(self):
        """Test dispatch_webhook_event with XML payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_XML)

        self._test_dispatch(
            handler,
            'my-event',
            {
                'items': [1, 2, 3],
            },
            'application/xml',
            ('<?xml version="1.0" encoding="utf-8"?>\n'
             '<rsp>\n'
             ' <items>\n'
             '  <array>\n'
             '   <item>1</item>\n'
             '   <item>2</item>\n'
             '   <item>3</item>\n'
             '  </array>\n'
             ' </items>\n'
             '</rsp>'))

    def test_dispatch_with_secret(self):
        """Test dispatch_webhook_event with HMAC secret"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON,
                                secret='foobar123')

        self._test_dispatch(
            handler,
            'my-event',
            {
                'items': [1, 2, 3],
            },
            'application/json',
            '{"items": [1, 2, 3]}',
            'sha1=cf27ad0de6b5f0c4e77e45bec9f4846e')

    def _test_dispatch(self, handler, event, payload, expected_content_type,
                       expected_data, expected_sig_header=None):
        def _urlopen(request):
            self.assertEqual(request.get_full_url(), self.ENDPOINT_URL)
            self.assertEqual(request.headers['X-reviewboard-event'], event)
            self.assertEqual(request.headers['Content-type'],
                             expected_content_type)
            self.assertEqual(request.data, expected_data)
            self.assertEqual(request.headers['Content-length'],
                             len(expected_data))

            if expected_sig_header:
                self.assertIn('X-hub-signature', request.headers)
                self.assertEqual(request.headers['X-hub-signature'],
                                 expected_sig_header)
            else:
                self.assertNotIn('X-hub-signature', request.headers)

        self.spy_on(urlopen, call_fake=_urlopen)

        request = FakeHTTPRequest(None)
        dispatch_webhook_event(request, [handler], event, payload)


class WebHookTargetManagerTests(TestCase):
    """Unit tests for WebHookTargetManager."""
    ENDPOINT_URL = 'http://example.com/endpoint/'

    def test_for_event(self):
        """Testing WebHookTargetManager.for_event"""
        # These should not match.
        WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        WebHookTarget.objects.create(
            events='event3',
            url=self.ENDPOINT_URL,
            enabled=False,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        # These should match.
        target1 = WebHookTarget.objects.create(
            events='event2,event3',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        target2 = WebHookTarget.objects.create(
            events='*',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        targets = WebHookTarget.objects.for_event('event3')
        self.assertEqual(targets, [target1, target2])

    def test_for_event_with_local_site(self):
        """Testing WebHookTargetManager.for_event with Local Sites"""
        site = LocalSite.objects.create(name='test-site')

        # These should not match.
        WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=False,
            local_site=site,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        # This should match.
        target = WebHookTarget.objects.create(
            events='event1,event2',
            url=self.ENDPOINT_URL,
            enabled=True,
            local_site=site,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        targets = WebHookTarget.objects.for_event('event1',
                                                  local_site_id=site.pk)
        self.assertEqual(targets, [target])

    @add_fixtures(['test_scmtools'])
    def test_for_event_with_repository(self):
        """Testing WebHookTargetManager.for_event with repository"""
        repository1 = self.create_repository()
        repository2 = self.create_repository()

        # These should not match.
        unused_target1 = WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=False,
            apply_to=WebHookTarget.APPLY_TO_SELECTED_REPOS)
        unused_target1.repositories.add(repository2)

        unused_target2 = WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=False,
            apply_to=WebHookTarget.APPLY_TO_SELECTED_REPOS)
        unused_target2.repositories.add(repository1)

        WebHookTarget.objects.create(
            events='event3',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_NO_REPOS)

        # These should match.
        target1 = WebHookTarget.objects.create(
            events='event1,event2',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        target2 = WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_SELECTED_REPOS)
        target2.repositories.add(repository1)

        targets = WebHookTarget.objects.for_event('event1',
                                                  repository_id=repository1.pk)
        self.assertEqual(targets, [target1, target2])

    @add_fixtures(['test_scmtools'])
    def test_for_event_with_no_repository(self):
        """Testing WebHookTargetManager.for_event with no repository"""
        repository = self.create_repository()

        # These should not match.
        unused_target1 = WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_SELECTED_REPOS)
        unused_target1.repositories.add(repository)

        WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=False,
            apply_to=WebHookTarget.APPLY_TO_NO_REPOS)

        WebHookTarget.objects.create(
            events='event2',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_NO_REPOS)

        # These should match.
        target1 = WebHookTarget.objects.create(
            events='event1,event2',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        target2 = WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_NO_REPOS)

        targets = WebHookTarget.objects.for_event('event1')
        self.assertEqual(targets, [target1, target2])

    def test_for_event_with_all_events(self):
        """Testing WebHookTargetManager.for_event with ALL_EVENTS"""
        with self.assertRaisesMessage(ValueError,
                                      '"*" is not a valid event choice'):
            WebHookTarget.objects.for_event(WebHookTarget.ALL_EVENTS)


class WebHookSignalDispatchTests(SpyAgency, TestCase):
    """Unit tests for dispatching webhooks by signals."""
    ENDPOINT_URL = 'http://example.com/endpoint/'

    def setUp(self):
        super(WebHookSignalDispatchTests, self).setUp()

        self.spy_on(dispatch_webhook_event, call_original=False)

    @add_fixtures(['test_users'])
    def test_review_request_closed_submitted(self):
        """Testing webhook dispatch from 'review_request_closed' signal
        with submitted
        """
        target = WebHookTarget.objects.create(events='review_request_closed',
                                              url=self.ENDPOINT_URL)

        review_request = self.create_review_request()
        review_request.close(review_request.SUBMITTED)

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_request_closed')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_request_closed')
        self.assertEqual(payload['closed_by']['id'],
                         review_request.submitter.pk)
        self.assertEqual(payload['close_type'], 'submitted')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    @add_fixtures(['test_users'])
    def test_review_request_closed_discarded(self):
        """Testing webhook dispatch from 'review_request_closed' signal
        with discarded
        """
        target = WebHookTarget.objects.create(events='review_request_closed',
                                              url=self.ENDPOINT_URL)

        review_request = self.create_review_request()
        review_request.close(review_request.DISCARDED)

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_request_closed')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_request_closed')
        self.assertEqual(payload['closed_by']['id'],
                         review_request.submitter.pk)
        self.assertEqual(payload['close_type'], 'discarded')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    @add_fixtures(['test_users'])
    def test_review_request_published(self):
        """Testing webhook dispatch from 'review_request_published' signal"""
        target = WebHookTarget.objects.create(
            events='review_request_published',
            url=self.ENDPOINT_URL)

        review_request = self.create_review_request()
        review_request.publish(review_request.submitter)

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_request_published')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_request_published')
        self.assertIn('is_new', payload)
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    @add_fixtures(['test_users'])
    def test_review_request_reopened(self):
        """Testing webhook dispatch from 'review_request_reopened' signal"""
        target = WebHookTarget.objects.create(
            events='review_request_reopened',
            url=self.ENDPOINT_URL)

        review_request = self.create_review_request()
        review_request.close(review_request.SUBMITTED)
        review_request.reopen()

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_request_reopened')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_request_reopened')
        self.assertEqual(payload['reopened_by']['id'],
                         review_request.submitter.pk)
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    @add_fixtures(['test_users'])
    def test_review_published(self):
        """Testing webhook dispatch from 'review_published' signal"""
        target = WebHookTarget.objects.create(events='review_published',
                                              url=self.ENDPOINT_URL)

        review_request = self.create_review_request()
        review = self.create_review(review_request)
        review.publish()

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_published')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_published')
        self.assertEqual(payload['review']['id'], review.pk)
        self.assertIn('diff_comments', payload)
        self.assertIn('screenshot_comments', payload)
        self.assertIn('file_attachment_comments', payload)

    @add_fixtures(['test_users'])
    def test_reply_published(self):
        """Testing webhook dispatch from 'reply_published' signal"""
        target = WebHookTarget.objects.create(events='reply_published',
                                              url=self.ENDPOINT_URL)

        review_request = self.create_review_request()
        review = self.create_review(review_request)
        reply = self.create_reply(review)
        reply.publish()

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'reply_published')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'reply_published')
        self.assertEqual(payload['reply']['id'], reply.pk)
        self.assertIn('diff_comments', payload)
        self.assertIn('screenshot_comments', payload)
        self.assertIn('file_attachment_comments', payload)
