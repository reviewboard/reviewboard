"""Unit tests for reviewboard.accounts.service_accounts.ServiceAccount.

Version Added:
    8.1
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from django_assert_queries import assert_queries

from reviewboard.accounts.errors import ServiceAccountUserError
from reviewboard.accounts.models import Profile
from reviewboard.accounts.service_accounts import ServiceAccount
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from django_assert_queries import ExpectedQueries


class ServiceAccountTests(TestCase):
    """Unit tests for ServiceAccount.

    Version Added:
        8.1
    """

    def test_init_with_minimum_subclass(self) -> None:
        """Testing ServiceAccount.__init__ with minimum subclass"""
        class MyServiceAccount(ServiceAccount):
            service_account_id = 'my-service-account'

        self.assertAttrsEqual(
            MyServiceAccount(),
            {
                '_claim_username': False,
                '_user': None,
                'api_token_expiration_secs': 60 * 60 * 24 * 30,
                'api_token_policy': None,
                'api_token_version': 1,
                'avatar_urls': None,
                'email': 'noreply@example.com',
                'name': 'Service Account',
                'preferred_username': 'my-service-account',
                'profile_version': 1,
                'service_account_id': 'my-service-account',
            })

    def test_init_with_minimum_init(self) -> None:
        """Testing ServiceAccount.__init__ with minimum init"""
        self.assertAttrsEqual(
            ServiceAccount(service_account_id='my-service-account'),
            {
                '_claim_username': False,
                '_user': None,
                'api_token_expiration_secs': 60 * 60 * 24 * 30,
                'api_token_policy': None,
                'api_token_version': 1,
                'avatar_urls': None,
                'email': 'noreply@example.com',
                'name': 'Service Account',
                'preferred_username': 'my-service-account',
                'profile_version': 1,
                'service_account_id': 'my-service-account',
            })

    def test_init_with_subclass_all(self) -> None:
        """Testing ServiceAccount.__init__ with overriding all attributes
        in subclass
        """
        class MyServiceAccount(ServiceAccount):
            service_account_id = 'my-super-service-account'

            name = 'My Super Service Account'
            email = 'super@example.com'
            preferred_username = 'super'
            profile_version = 2
            avatar_urls = {
                '1x': '/super.png',
                '2x': '/super@2x.png',
            }

            api_token_policy = {
                'resources': {
                    '*': {
                        'allow': ['DELETE'],
                    },
                },
            }
            api_token_expiration_secs = 60 * 60 * 24 * 120
            api_token_version = 2

        self.assertAttrsEqual(
            MyServiceAccount(),
            {
                '_claim_username': False,
                '_user': None,
                'api_token_expiration_secs': 60 * 60 * 24 * 120,
                'api_token_policy': {
                    'resources': {
                        '*': {
                            'allow': ['DELETE'],
                        },
                    },
                },
                'api_token_version': 2,
                'avatar_urls': {
                    '1x': '/super.png',
                    '2x': '/super@2x.png',
                },
                'email': 'super@example.com',
                'name': 'My Super Service Account',
                'preferred_username': 'super',
                'profile_version': 2,
                'service_account_id': 'my-super-service-account',
            })

    def test_init_with_override_all(self) -> None:
        """Testing ServiceAccount.__init__ with overriding all attributes
        during init
        """
        class MyServiceAccount(ServiceAccount):
            service_account_id = 'my-boring-service-account'

            name = 'My Boring Service Account'
            email = 'boring@example.com'
            preferred_username = 'boring'
            profile_version = 1
            avatar_urls = {
                '1x': '/boring.png',
            }

            api_token_policy = {
                'resources': {
                    '*': {
                        'block': ['*'],
                    },
                },
            }
            api_token_expiration_secs = 35
            api_token_version = 1

        self.assertAttrsEqual(
            MyServiceAccount(
                service_account_id='my-super-service-account',
                name='My Super Service Account',
                claim_username=True,
                email='super@example.com',
                preferred_username='super',
                profile_version=2,
                avatar_urls={
                    '1x': '/super.png',
                    '2x': '/super@2x.png',
                },
                api_token_policy={
                    'resources': {
                        '*': {
                            'allow': ['DELETE'],
                        },
                    },
                },
                api_token_expiration_secs=60 * 60 * 24 * 120,
                api_token_version=2,
            ),
            {
                '_claim_username': True,
                '_user': None,
                'api_token_expiration_secs': 60 * 60 * 24 * 120,
                'api_token_policy': {
                    'resources': {
                        '*': {
                            'allow': ['DELETE'],
                        },
                    },
                },
                'api_token_version': 2,
                'avatar_urls': {
                    '1x': '/super.png',
                    '2x': '/super@2x.png',
                },
                'email': 'super@example.com',
                'name': 'My Super Service Account',
                'preferred_username': 'super',
                'profile_version': 2,
                'service_account_id': 'my-super-service-account',
            })

    def test_init_with_missing_service_account_id(self) -> None:
        """Testing ServiceAccount.__init__ with missing service_account_id"""
        message = (
            'ServiceAccount.service_account_id must be set or provided '
            'during construction.'
        )

        with self.assertRaisesMessage(ValueError, message):
            ServiceAccount()

    def test_get_user_with_cached(self) -> None:
        """Testing ServiceAccount.get_user with cached result"""
        user = self.create_user()

        service_account = ServiceAccount(
            service_account_id='my-service-account',
        )
        service_account._user = user

        with self.assertNumQueries(0):
            self.assertIs(service_account.get_user(), user)

    def test_get_user_create_preferred(self) -> None:
        """Testing ServiceAccount.get_user with creating preferred username"""
        service_account = ServiceAccount(
            service_account_id='my-service-account',
            preferred_username='my-service-user',
            email='service-account@example.com',
            name='My Service Account',
        )

        claim_map: dict[str, ServiceAccount] = {}

        equeries: ExpectedQueries = [
            {
                '__note__': 'Initial fetch for the user',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user'),
            },
            {
                '__note__': 'Creation of the user',
                'model': User,
                'type': 'INSERT',
            },
            {
                '__note__': 'Population of user state',
                'model': User,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
            {
                '__note__': 'Creation of the profile',
                'model': Profile,
                'type': 'INSERT',
            },
        ]

        with assert_queries(equeries):
            user = service_account.get_user(_claim_map=claim_map)

        self.assertIsNotNone(user)

        user.refresh_from_db()
        self.assertAttrsEqual(
            user,
            {
                'email': 'service-account@example.com',
                'first_name': 'My',
                'last_name': 'Service Account',
                'username': 'my-service-user',
            })
        self.assertFalse(user.has_usable_password())

        with self.assertNumQueries(0):
            self.assertAttrsEqual(
                user.get_profile(), {
                    'extra_data': {
                        '_profile_ver': 1,
                        'service_account_id': 'my-service-account',
                    },
                    'should_send_email': False,
                    'settings': {},
                })

        # Another fetch should use cache.
        with self.assertNumQueries(0):
            self.assertIs(service_account.get_user(), user)

        self.assertEqual(claim_map, {
            'my-service-user': service_account,
        })

    def test_get_user_create_preferred_with_avatars(self) -> None:
        """Testing ServiceAccount.get_user with creating preferred username
        with avatars
        """
        service_account = ServiceAccount(
            service_account_id='my-service-account',
            preferred_username='my-service-user',
            email='service-account@example.com',
            name='My Service Account',
            avatar_urls={
                '1x': '/user.png',
                '2x': '/user@2x.png',
            },
        )

        claim_map: dict[str, ServiceAccount] = {}

        equeries: ExpectedQueries = [
            {
                '__note__': 'Initial fetch for the user',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user'),
            },
            {
                '__note__': 'Creation of the user',
                'model': User,
                'type': 'INSERT',
            },
            {
                '__note__': 'Population of user state',
                'model': User,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
            {
                '__note__': 'Creation of the profile',
                'model': Profile,
                'type': 'INSERT',
            },
            {
                '__note__': 'Population of the avatar',
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
        ]

        with assert_queries(equeries):
            user = service_account.get_user(_claim_map=claim_map)

        self.assertIsNotNone(user)

        user.refresh_from_db()
        self.assertAttrsEqual(
            user,
            {
                'email': 'service-account@example.com',
                'first_name': 'My',
                'last_name': 'Service Account',
                'username': 'my-service-user',
            })
        self.assertFalse(user.has_usable_password())

        with self.assertNumQueries(0):
            self.assertAttrsEqual(
                user.get_profile(), {
                    'extra_data': {
                        '_profile_ver': 1,
                        'service_account_id': 'my-service-account',
                    },
                    'should_send_email': False,
                    'settings': {
                        'avatars': {
                            'avatar_service_id': 'url',
                            'configuration': {
                                'url': {
                                    '1x': '/user.png',
                                    '2x': '/user@2x.png',
                                },
                            },
                        },
                    },
                })

        # Another fetch should use cache.
        with self.assertNumQueries(0):
            self.assertIs(service_account.get_user(), user)

        self.assertEqual(claim_map, {
            'my-service-user': service_account,
        })

    def test_get_user_create_after_conflict(self) -> None:
        """Testing ServiceAccount.get_user with creating preferred username
        after conflict
        """
        # Create 2 users, one with a profile, one without.
        user = self.create_user(username='my-service-user')
        user.get_profile()

        self.create_user(username='my-service-user-1')

        service_account = ServiceAccount(
            service_account_id='my-service-account',
            preferred_username='my-service-user',
            email='service-account@example.com',
            name='My Account',
            avatar_urls={
                '1x': '/user.png',
                '2x': '/user@2x.png',
            },
        )

        claim_map: dict[str, ServiceAccount] = {}

        equeries: ExpectedQueries = [
            {
                '__note__': 'Fetch of "my-service-user"',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user'),
            },
            {
                '__note__': 'Fetch of "my-service-user-1"',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user-1'),
            },
            {
                '__note__': 'Fetch of "my-service-user-2"',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user-2'),
            },
            {
                '__note__': 'Creation of the user',
                'model': User,
                'type': 'INSERT',
            },
            {
                '__note__': 'Population of user state',
                'model': User,
                'type': 'UPDATE',
                'where': Q(pk=3),
            },
            {
                '__note__': 'Creation of the profile',
                'model': Profile,
                'type': 'INSERT',
            },
            {
                '__note__': 'Population of the avatar',
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=2),
            },
        ]

        with assert_queries(equeries, with_tracebacks=True):
            user = service_account.get_user(_claim_map=claim_map)

        self.assertIsNotNone(user)

        user.refresh_from_db()
        self.assertAttrsEqual(
            user,
            {
                'email': 'service-account@example.com',
                'first_name': 'My',
                'last_name': 'Account',
                'username': 'my-service-user-2',
            })
        self.assertFalse(user.has_usable_password())

        with self.assertNumQueries(0):
            self.assertAttrsEqual(
                user.get_profile(), {
                    'extra_data': {
                        '_profile_ver': 1,
                        'service_account_id': 'my-service-account',
                    },
                    'should_send_email': False,
                    'settings': {
                        'avatars': {
                            'avatar_service_id': 'url',
                            'configuration': {
                                'url': {
                                    '1x': '/user.png',
                                    '2x': '/user@2x.png',
                                },
                            },
                        },
                    },
                })

        # Another fetch should use cache.
        with self.assertNumQueries(0):
            self.assertIs(service_account.get_user(), user)

        self.assertEqual(claim_map, {
            'my-service-user-2': service_account,
        })

    def test_get_user_with_claim(self) -> None:
        """Testing ServiceAccount.get_user with claimed username"""
        self.create_user(username='my-service-user')

        service_account = ServiceAccount(
            service_account_id='my-service-account',
            preferred_username='my-service-user',
            email='service-account@example.com',
            name='My Account',
            avatar_urls={
                '1x': '/user.png',
                '2x': '/user@2x.png',
            },
            claim_username=True,
        )

        claim_map: dict[str, ServiceAccount] = {}

        equeries: ExpectedQueries = [
            {
                '__note__': 'Fetch of "my-service-user"',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user'),
            },
            {
                '__note__': 'Population of user state',
                'model': User,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
            {
                '__note__': 'Creation of the profile',
                'model': Profile,
                'type': 'INSERT',
            },
            {
                '__note__': 'Population of the avatar',
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
        ]

        with assert_queries(equeries, with_tracebacks=True):
            user = service_account.get_user(_claim_map=claim_map)

        self.assertIsNotNone(user)

        user.refresh_from_db()
        self.assertAttrsEqual(
            user,
            {
                'email': 'service-account@example.com',
                'first_name': 'My',
                'last_name': 'Account',
                'username': 'my-service-user',
            })
        self.assertFalse(user.has_usable_password())

        with self.assertNumQueries(0):
            self.assertAttrsEqual(
                user.get_profile(), {
                    'extra_data': {
                        '_profile_ver': 1,
                        'service_account_id': 'my-service-account',
                    },
                    'should_send_email': False,
                    'settings': {
                        'avatars': {
                            'avatar_service_id': 'url',
                            'configuration': {
                                'url': {
                                    '1x': '/user.png',
                                    '2x': '/user@2x.png',
                                },
                            },
                        },
                    },
                })

        # Another fetch should use cache.
        with self.assertNumQueries(0):
            self.assertIs(service_account.get_user(), user)

        self.assertEqual(claim_map, {
            'my-service-user': service_account,
        })

    def test_get_user_with_claim_and_profile(self) -> None:
        """Testing ServiceAccount.get_user with claimed username with
        profile
        """
        user = self.create_user(username='my-service-user')
        user.get_profile()

        service_account = ServiceAccount(
            service_account_id='my-service-account',
            preferred_username='my-service-user',
            email='service-account@example.com',
            name='My Account',
            avatar_urls={
                '1x': '/user.png',
                '2x': '/user@2x.png',
            },
            claim_username=True,
        )

        claim_map: dict[str, ServiceAccount] = {}

        equeries: ExpectedQueries = [
            {
                '__note__': 'Fetch of "my-service-user"',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user'),
            },
            {
                '__note__': 'Population of user state',
                'model': User,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
            {
                '__note__': 'Update of the profile',
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
            {
                '__note__': 'Population of the avatar',
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
        ]

        with assert_queries(equeries, with_tracebacks=True):
            user = service_account.get_user(_claim_map=claim_map)

        self.assertIsNotNone(user)

        user.refresh_from_db()
        self.assertAttrsEqual(
            user,
            {
                'email': 'service-account@example.com',
                'first_name': 'My',
                'last_name': 'Account',
                'username': 'my-service-user',
            })
        self.assertFalse(user.has_usable_password())

        with self.assertNumQueries(0):
            self.assertAttrsEqual(
                user.get_profile(), {
                    'extra_data': {
                        '_profile_ver': 1,
                        'service_account_id': 'my-service-account',
                    },
                    'should_send_email': False,
                    'settings': {
                        'avatars': {
                            'avatar_service_id': 'url',
                            'configuration': {
                                'url': {
                                    '1x': '/user.png',
                                    '2x': '/user@2x.png',
                                },
                            },
                        },
                    },
                })

        # Another fetch should use cache.
        with self.assertNumQueries(0):
            self.assertIs(service_account.get_user(), user)

        self.assertEqual(claim_map, {
            'my-service-user': service_account,
        })

    def test_get_user_with_claim_conflict(self) -> None:
        """Testing ServiceAccount.get_user with claiming username claimed
        by another service account
        """
        self.create_user(username='my-service-user')

        service_account1 = ServiceAccount(
            service_account_id='my-service-account-1',
            preferred_username='my-service-user',
            email='service-account1@example.com',
            name='First Service Account',
            claim_username=True,
        )

        service_account2 = ServiceAccount(
            service_account_id='my-service-account-2',
            preferred_username='my-service-user',
            email='service-account2@example.com',
            name='Second Service Account',
            avatar_urls={
                '1x': '/user.png',
                '2x': '/user@2x.png',
            },
            claim_username=True,
        )

        claim_map: dict[str, ServiceAccount] = {
            'my-service-user': service_account1,
        }

        message = (
            'Cannot claim the service account username "my-service-user". '
            'It has already been claimed by another service account. This '
            'may be a conflict between two extensions or a configuration '
            'error. Contact support if you need assistance.'
        )

        with self.assertNumQueries(0), \
             self.assertRaisesMessage(ServiceAccountUserError, message):
            service_account2.get_user(_claim_map=claim_map)

        self.assertEqual(claim_map, {
            'my-service-user': service_account1,
        })

    def test_get_user_with_max_attempts(self) -> None:
        """Testing ServiceAccount.get_user with max attempts reached
        after too many tries
        """
        user = self.create_user(username='my-service-user')
        self.assertIsNotNone(user.get_profile())

        service_account = ServiceAccount(
            service_account_id='my-service-account-1',
            preferred_username='my-service-user',
            email='service-account1@example.com',
            name='First Service Account',
        )

        claim_map: dict[str, ServiceAccount] = {}

        message = (
            r'Failed to create a unique service account user for '
            r'"my-service-user" \(error ID [0-9a-f-]+\)\. Please contact '
            r'support\.'
        )

        equeries: ExpectedQueries = [
            {
                '__note__': 'Fetch of "my-service-user"',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user'),
            },
        ]

        with assert_queries(equeries):
            with self.assertRaisesRegex(ServiceAccountUserError, message):
                service_account.get_user(_max_attempts=1)

        self.assertEqual(claim_map, {})

    def test_get_user_with_id_match(self) -> None:
        """Testing ServiceAccount.get_user with service account ID match"""
        user = self.create_user(
            username='my-service-user',
            email='old@example.com',
            first_name='Old First',
            last_name='Old Last',
        )
        profile = user.get_profile()
        profile.extra_data['_profile_ver'] = 1
        profile.extra_data['service_account_id'] = 'my-service-account'
        profile.save(update_fields=('extra_data',))

        service_account = ServiceAccount(
            service_account_id='my-service-account',
            preferred_username='my-service-user',
            email='service-account@example.com',
            name='Super Duper Service Account',
            avatar_urls={
                '1x': '/user.png',
                '2x': '/user@2x.png',
            },
        )

        claim_map: dict[str, ServiceAccount] = {}

        equeries: ExpectedQueries = [
            {
                '__note__': 'Fetch of "my-service-user"',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user'),
            },
        ]

        with assert_queries(equeries, with_tracebacks=True):
            user = service_account.get_user(_claim_map=claim_map)

        self.assertIsNotNone(user)

        user.refresh_from_db()

        # This will keep old state, since the profile version didn't change.
        self.assertAttrsEqual(
            user,
            {
                'email': 'old@example.com',
                'first_name': 'Old First',
                'last_name': 'Old Last',
                'username': 'my-service-user',
            })
        self.assertTrue(user.has_usable_password())

        with self.assertNumQueries(0):
            self.assertAttrsEqual(
                user.get_profile(), {
                    'extra_data': {
                        '_profile_ver': 1,
                        'service_account_id': 'my-service-account',
                    },
                    'should_send_email': True,
                    'settings': {},
                })

        # Another fetch should use cache.
        with self.assertNumQueries(0):
            self.assertIs(service_account.get_user(), user)

        self.assertEqual(claim_map, {
            'my-service-user': service_account,
        })

    def test_get_user_with_id_match_new_profile_ver(self) -> None:
        """Testing ServiceAccount.get_user with service account ID match
        and new profile version
        """
        user = self.create_user(username='my-service-user')
        profile = user.get_profile()
        profile.extra_data['_profile_ver'] = 1
        profile.extra_data['service_account_id'] = 'my-service-account'
        profile.save(update_fields=('extra_data',))

        service_account = ServiceAccount(
            service_account_id='my-service-account',
            preferred_username='my-service-user',
            email='service-account@example.com',
            name='Super Duper Service Account',
            avatar_urls={
                '1x': '/user.png',
                '2x': '/user@2x.png',
            },
            profile_version=2,
        )

        claim_map: dict[str, ServiceAccount] = {}

        equeries: ExpectedQueries = [
            {
                '__note__': 'Fetch of "my-service-user"',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user'),
            },
            {
                '__note__': 'Population of user state',
                'model': User,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
            {
                '__note__': 'Update of the profile',
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
            {
                '__note__': 'Population of the avatar',
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
        ]

        with assert_queries(equeries, with_tracebacks=True):
            user = service_account.get_user(_claim_map=claim_map)

        self.assertIsNotNone(user)

        user.refresh_from_db()
        self.assertAttrsEqual(
            user,
            {
                'email': 'service-account@example.com',
                'first_name': 'Super Duper',
                'last_name': 'Service Account',
                'username': 'my-service-user',
            })
        self.assertFalse(user.has_usable_password())

        with self.assertNumQueries(0):
            self.assertAttrsEqual(
                user.get_profile(), {
                    'extra_data': {
                        '_profile_ver': 2,
                        'service_account_id': 'my-service-account',
                    },
                    'should_send_email': False,
                    'settings': {
                        'avatars': {
                            'avatar_service_id': 'url',
                            'configuration': {
                                'url': {
                                    '1x': '/user.png',
                                    '2x': '/user@2x.png',
                                },
                            },
                        },
                    },
                })

        # Another fetch should use cache.
        with self.assertNumQueries(0):
            self.assertIs(service_account.get_user(), user)

        self.assertEqual(claim_map, {
            'my-service-user': service_account,
        })

    def test_get_user_with_id_match_scan(self) -> None:
        """Testing ServiceAccount.get_user with service account ID match
        after user scan
        """
        self.create_user(username='my-service-user')

        user = self.create_user(
            username='my-service-user-1',
            email='old@example.com',
            first_name='Old First',
            last_name='Old Last',
        )
        user.set_password('ohboy')

        profile = user.get_profile()
        profile.extra_data['_profile_ver'] = 1
        profile.extra_data['service_account_id'] = 'my-service-account'
        profile.save(update_fields=('extra_data',))

        service_account = ServiceAccount(
            service_account_id='my-service-account',
            preferred_username='my-service-user',
            email='service-account@example.com',
            name='Super Duper Service Account',
            avatar_urls={
                '1x': '/user.png',
                '2x': '/user@2x.png',
            },
        )

        claim_map: dict[str, ServiceAccount] = {}

        equeries: ExpectedQueries = [
            {
                '__note__': 'Fetch of "my-service-user"',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user'),
            },
            {
                '__note__': 'Fetch of "my-service-user-1"',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user-1'),
            },
        ]

        with assert_queries(equeries, with_tracebacks=True):
            user = service_account.get_user(_claim_map=claim_map)

        self.assertIsNotNone(user)

        user.refresh_from_db()

        # This will keep old state, since the profile version didn't change.
        self.assertAttrsEqual(
            user,
            {
                'email': 'old@example.com',
                'first_name': 'Old First',
                'last_name': 'Old Last',
                'username': 'my-service-user-1',
            })
        self.assertTrue(user.has_usable_password())

        with self.assertNumQueries(0):
            self.assertAttrsEqual(
                user.get_profile(), {
                    'extra_data': {
                        '_profile_ver': 1,
                        'service_account_id': 'my-service-account',
                    },
                    'should_send_email': True,
                    'settings': {},
                })

        # Another fetch should use cache.
        with self.assertNumQueries(0):
            self.assertIs(service_account.get_user(), user)

        self.assertEqual(claim_map, {
            'my-service-user-1': service_account,
        })

    def test_get_user_with_id_match_scan_new_profile_ver(self) -> None:
        """Testing ServiceAccount.get_user with service account ID match
        after user scan and new profile version
        """
        self.create_user(username='my-service-user')

        user = self.create_user(username='my-service-user-1')
        profile = user.get_profile()
        profile.extra_data['_profile_ver'] = 1
        profile.extra_data['service_account_id'] = 'my-service-account'
        profile.save(update_fields=('extra_data',))

        service_account = ServiceAccount(
            service_account_id='my-service-account',
            preferred_username='my-service-user',
            email='service-account@example.com',
            name='Super Duper Service Account',
            avatar_urls={
                '1x': '/user.png',
                '2x': '/user@2x.png',
            },
            profile_version=2,
        )

        claim_map: dict[str, ServiceAccount] = {}

        equeries: ExpectedQueries = [
            {
                '__note__': 'Fetch of "my-service-user"',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user'),
            },
            {
                '__note__': 'Fetch of "my-service-user-1"',
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-user-1'),
            },
            {
                '__note__': 'Population of user state',
                'model': User,
                'type': 'UPDATE',
                'where': Q(pk=2),
            },
            {
                '__note__': 'Update of the profile',
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
            {
                '__note__': 'Population of the avatar',
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
        ]

        with assert_queries(equeries, with_tracebacks=True):
            user = service_account.get_user(_claim_map=claim_map)

        self.assertIsNotNone(user)

        user.refresh_from_db()
        self.assertAttrsEqual(
            user,
            {
                'email': 'service-account@example.com',
                'first_name': 'Super Duper',
                'last_name': 'Service Account',
                'username': 'my-service-user-1',
            })
        self.assertFalse(user.has_usable_password())

        with self.assertNumQueries(0):
            self.assertAttrsEqual(
                user.get_profile(), {
                    'extra_data': {
                        '_profile_ver': 2,
                        'service_account_id': 'my-service-account',
                    },
                    'should_send_email': False,
                    'settings': {
                        'avatars': {
                            'avatar_service_id': 'url',
                            'configuration': {
                                'url': {
                                    '1x': '/user.png',
                                    '2x': '/user@2x.png',
                                },
                            },
                        },
                    },
                })

        # Another fetch should use cache.
        with self.assertNumQueries(0):
            self.assertIs(service_account.get_user(), user)

        self.assertEqual(claim_map, {
            'my-service-user-1': service_account,
        })

    def test_get_api_token_with_create(self) -> None:
        """Testing ServiceAccount.get_api_token with creating new token"""
        service_account = ServiceAccount(
            service_account_id='my-service-account',
        )
        user = service_account.get_user()
        api_token = service_account.get_api_token(local_site=None)

        self.assertAttrsEqual(
            api_token,
            {
                'note': (
                    'API token automatically created for '
                    'my-service-account_v1.'
                ),
                'local_site': None,
                'user': user,
                'policy': {},
            })

    def test_get_api_token_with_create_and_policy(self) -> None:
        """Testing ServiceAccount.get_api_token with creating new token
        and policy
        """
        service_account = ServiceAccount(
            service_account_id='my-service-account',
            api_token_policy={
                'resources': {
                    '*': {
                        'allow': ['DELETE'],
                    },
                }
            },
        )
        user = service_account.get_user()
        api_token = service_account.get_api_token(local_site=None)

        self.assertAttrsEqual(
            api_token,
            {
                'note': (
                    'API token automatically created for '
                    'my-service-account_v1.'
                ),
                'local_site': None,
                'user': user,
                'policy': {
                    'resources': {
                        '*': {
                            'allow': ['DELETE'],
                        },
                    }
                },
            })

    def test_get_api_token_with_create_and_deprecated(self) -> None:
        """Testing ServiceAccount.get_api_token with creating new token
        and existing token deprecated
        """
        service_account = ServiceAccount(
            service_account_id='my-service-account',
        )
        user = service_account.get_user()

        # Create one token, which we'll mark deprecated.
        existing_api_token = service_account.get_api_token(local_site=None)
        existing_api_token.token_generator_id = 'legacy_sha1'
        existing_api_token.save(update_fields=('token_generator_id',))

        # Now create the new one.
        api_token = service_account.get_api_token(local_site=None)

        self.assertNotEqual(api_token, existing_api_token)
        self.assertAttrsEqual(
            api_token,
            {
                'note': (
                    'API token automatically created for '
                    'my-service-account_v1.'
                ),
                'local_site': None,
                'user': user,
                'policy': {},
            })

    def test_get_api_token_with_create_and_expired(self) -> None:
        """Testing ServiceAccount.get_api_token with creating new token
        and existing expired token
        """
        service_account = ServiceAccount(
            service_account_id='my-service-account',
        )
        user = service_account.get_user()

        # Create one token, which we'll mark expired.
        existing_api_token = service_account.get_api_token(local_site=None)
        existing_api_token.expires = timezone.now() - timedelta(days=1)
        existing_api_token.save(update_fields=('expires',))

        # Now create the new one.
        api_token = service_account.get_api_token(local_site=None)

        self.assertNotEqual(api_token, existing_api_token)
        self.assertAttrsEqual(
            api_token,
            {
                'note': (
                    'API token automatically created for '
                    'my-service-account_v1.'
                ),
                'local_site': None,
                'user': user,
                'policy': {},
            })

    def test_get_api_token_with_create_and_expires_soon(self) -> None:
        """Testing ServiceAccount.get_api_token with creating new token
        and existing expired token
        """
        service_account = ServiceAccount(
            service_account_id='my-service-account',
        )
        user = service_account.get_user()

        # Create one token, which we'll mark as expiring soon.
        existing_api_token = service_account.get_api_token(local_site=None)
        existing_api_token.expires = \
            timezone.now() + timedelta(seconds=60 * 60)
        existing_api_token.save(update_fields=('expires',))

        # Now create the new one.
        api_token = service_account.get_api_token(local_site=None)

        self.assertNotEqual(api_token, existing_api_token)
        self.assertAttrsEqual(
            api_token,
            {
                'note': (
                    'API token automatically created for '
                    'my-service-account_v1.'
                ),
                'local_site': None,
                'user': user,
                'policy': {},
            })

    def test_get_api_token_with_create_and_version_change(self) -> None:
        """Testing ServiceAccount.get_api_token with creating new token
        and version change
        """
        service_account = ServiceAccount(
            service_account_id='my-service-account',
        )
        user = service_account.get_user()

        # Create one token, which we'll soon replace.
        existing_api_token = service_account.get_api_token(local_site=None)

        # Now create the new one.
        service_account.api_token_version = 2
        api_token = service_account.get_api_token(local_site=None)

        self.assertNotEqual(api_token, existing_api_token)
        self.assertAttrsEqual(
            api_token,
            {
                'note': (
                    'API token automatically created for '
                    'my-service-account_v2.'
                ),
                'local_site': None,
                'user': user,
                'policy': {},
            })

    def test_get_api_token_with_existing(self) -> None:
        """Testing ServiceAccount.get_api_token with existing token"""
        service_account = ServiceAccount(
            service_account_id='my-service-account',
        )
        user = service_account.get_user()

        # Create one token, which we'll fetch again.
        existing_api_token = service_account.get_api_token(local_site=None)

        # Now fetch one.
        api_token = service_account.get_api_token(local_site=None)

        self.assertEqual(api_token, existing_api_token)
        self.assertAttrsEqual(
            api_token,
            {
                'note': (
                    'API token automatically created for '
                    'my-service-account_v1.'
                ),
                'local_site': None,
                'user': user,
                'policy': {},
            })
