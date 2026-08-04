"""Unit tests for reviewboard.accounts.service_accounts.ServiceAccountRegistry.

Version Added:
    8.1
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.db.models import Q
from django_assert_queries import assert_queries

from reviewboard.accounts.models import Profile
from reviewboard.accounts.service_accounts import (ServiceAccount,
                                                   ServiceAccountRegistry)
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from django_assert_queries import ExpectedQueries


class ServiceAccountRegistryTests(TestCase):
    """Unit tests for ServiceAccountRegistry.

    Version Added:
        8.1
    """

    def test_register_with_new_user(self) -> None:
        """Testing ServiceAccountRegistry.register with new user"""
        service_account = ServiceAccount(
            service_account_id='my-service-account',
        )

        registry = ServiceAccountRegistry()

        equeries: ExpectedQueries = [
            {
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-account'),
            },
            {
                'model': User,
                'type': 'INSERT',
            },
            {
                'model': User,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
            {
                'model': Profile,
                'type': 'INSERT',
            },
        ]

        with assert_queries(equeries):
            registry.register(service_account)

        self.assertEqual(
            registry._by_username,
            {
                'my-service-account': service_account,
            })

    def test_register_with_existing_user(self) -> None:
        """Testing ServiceAccountRegistry.register with existing user"""
        service_account = ServiceAccount(
            service_account_id='my-service-account',
        )
        service_account.get_user()
        service_account._user = None

        registry = ServiceAccountRegistry()

        equeries: ExpectedQueries = [
            {
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='my-service-account'),
            },
        ]

        with assert_queries(equeries):
            registry.register(service_account)

        self.assertEqual(
            registry._by_username,
            {
                'my-service-account': service_account,
            })

    def test_unregister(self) -> None:
        """Testing ServiceAccount.unregister"""
        service_account1 = ServiceAccount(
            service_account_id='my-service-account1',
        )
        service_account2 = ServiceAccount(
            service_account_id='my-service-account2',
        )

        registry = ServiceAccountRegistry()
        registry.register(service_account1)
        registry.register(service_account2)

        self.assertEqual(
            registry._by_username,
            {
                'my-service-account1': service_account1,
                'my-service-account2': service_account2,
            })

        registry.unregister(service_account2)

        self.assertEqual(
            registry._by_username,
            {
                'my-service-account1': service_account1,
            })

        registry.unregister(service_account1)

        self.assertEqual(registry._by_username, {})

    def test_get_for_service_account_id_found(self) -> None:
        """Testing ServiceAccountRegistry.get_for_service_account_id with
        service account found
        """
        service_account = ServiceAccount(
            service_account_id='my-service-account',
        )

        registry = ServiceAccountRegistry()
        registry.register(service_account)

        self.assertIs(
            registry.get_for_service_account_id('my-service-account'),
            service_account)

    def test_get_for_service_account_id_not_found(self) -> None:
        """Testing ServiceAccountRegistry.get_for_service_account_id with
        service account not found
        """
        registry = ServiceAccountRegistry()
        registry.register(ServiceAccount(
            service_account_id='my-service-account',
        ))

        self.assertIsNone(
            registry.get_for_service_account_id('other-service-account'))

    def test_get_for_username_found(self) -> None:
        """Testing ServiceAccountRegistry.get_for_username with service
        account found
        """
        service_account = ServiceAccount(
            service_account_id='my-service-account',
            preferred_username='my-service-user',
        )

        registry = ServiceAccountRegistry()
        registry.register(service_account)

        self.assertIs(registry.get_for_username('my-service-user'),
                      service_account)

    def test_get_for_username_not_found(self) -> None:
        """Testing ServiceAccountRegistry.get_for_username with service
        account not found
        """
        registry = ServiceAccountRegistry()
        registry.register(ServiceAccount(
            service_account_id='my-service-account',
            preferred_username='my-service-user',
        ))

        self.assertIsNone(registry.get_for_username('other-service-user'))
