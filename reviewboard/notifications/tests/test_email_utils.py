from __future__ import unicode_literals

from django.contrib.auth.models import User
from djblets.mail.utils import build_email_address_for_user
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import Profile
from reviewboard.notifications.email.utils import (
    build_recipients,
    get_email_addresses_for_group,
    recipients_to_addresses)
from reviewboard.reviews.models import Group
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


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
            build_email_address_for_user(u)
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
            build_email_address_for_user(u)
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

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create_user(username='user2', first_name='User',
                                         last_name='Two',
                                         email='user2@example.com')

        group1.users = [user1]
        group2.users = [user2]

        addresses = recipients_to_addresses([group1, group2])

        expected_addresses = set([
            build_email_address_for_user(user1),
            build_email_address_for_user(user2),
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

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create_user(username='user2', first_name='User',
                                         last_name='Two',
                                         email='user2@example.com')

        local_site1.users = [user1]

        group1.users = [user1]
        group2.users = [user2]

        addresses = recipients_to_addresses([group1, group2])
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses, set([build_email_address_for_user(user1)]))

    def test_recipients_to_addresses_with_groups_inactive_members(self):
        """Testing generating addresses form recipients that are groups with
        inactive members
        """
        group1 = self.create_review_group('group1')
        group2 = self.create_review_group('group2')

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', is_active=False,
                                    email='user1@example.com')

        group1.users = [user1]
        group2.users = [user2]

        addresses = recipients_to_addresses([group1, group2])
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses, set([build_email_address_for_user(user1)]))

    def test_recipients_to_addresses_groups_local_site_inactive_members(self):
        """Testing generating addresses from recipients that are groups in
        local sites that have inactive members
        """
        local_site1 = LocalSite.objects.create(name='local-site1')
        local_site2 = LocalSite.objects.create(name='local-site2')

        group1 = self.create_review_group('group1', local_site=local_site1)
        group2 = self.create_review_group('group2', local_site=local_site2)

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', is_active=False,
                                    email='user2@example.com')

        local_site1.users = [user1]
        local_site2.users = [user2]

        group1.users = [user1]
        group2.users = [user2]

        addresses = recipients_to_addresses([group1, group2])
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses, set([build_email_address_for_user(user1)]))

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
                                   last_name='Foo', is_active=False,
                                   email='user@example.com')

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

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', email='user2@example.com',
                                    is_active=False)

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

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create_user(username='user2', first_name='User',
                                         last_name='Two',
                                         email='user2@example.com')

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

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create_user(username='user2', first_name='User',
                                         last_name='Two',
                                         email='user2@example.com')

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

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', is_active=False,
                                    email='user2@example.com')

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

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create_user(username='user2', first_name='User',
                                         last_name='Two',
                                         email='user2@exmaple.com')

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
        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', email='user2@exmaple.com',
                                    is_active=False)

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

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create_user(username='user2', first_name='User',
                                         last_name='Two',
                                         email='user2@exmaple.com')

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
        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', email='user2@exmaple.com',
                                    is_active=False)

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

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create_user(username='user2', first_name='User',
                                         last_name='Two',
                                         email='user2@exmaple.com')

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
        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create_user(username='user2', first_name='User',
                                         last_name='Two',
                                         email='user2@exmaple.com')
        user3 = User.objects.create_user(username='user3', first_name='User',
                                         last_name='Three',
                                         email='user3@exmaple.com')

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
        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', email='user2@exmaple.com',
                                    is_active=False)
        user3 = User.objects.create_user(username='user3', first_name='User',
                                         last_name='Three',
                                         email='user3@exmaple.com')

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

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create_user(username='user2', first_name='User',
                                         last_name='Two',
                                         email='user2@exmaple.com')
        user3 = User.objects.create_user(username='user3', first_name='User',
                                         last_name='Three',
                                         email='user3@exmaple.com')

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

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create(username='user2', first_name='User',
                                    last_name='Two', email='user@exmaple.com',
                                    is_active=False)
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

        user1 = User.objects.create_user(username='user1', first_name='User',
                                         last_name='One',
                                         email='user1@example.com')
        user2 = User.objects.create_user(username='user2', first_name='User',
                                         last_name='Two',
                                         email='user@exmaple.com')

        local_site1.users = [user1]
        local_site2.users = [user2]

        profile1 = Profile.objects.create(user=user1)
        profile1.starred_review_requests = [review_request]

        profile2 = Profile.objects.create(user=user2)
        profile2.starred_review_requests = [review_request]

        to, cc = build_recipients(submitter, review_request)

        self.assertEqual(to, set([submitter, user1]))
        self.assertEqual(len(cc), 0)
