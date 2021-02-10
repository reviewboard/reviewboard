"""Unit tests for ActiveDirectoryBackend."""

from __future__ import unicode_literals

import dns
import kgb
import ldap
from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings

from reviewboard.accounts.backends import ActiveDirectoryBackend
from reviewboard.accounts.tests.test_ldap_auth_backend import TestLDAPObject
from reviewboard.testing import TestCase


class ActiveDirectoryBackendTests(kgb.SpyAgency, TestCase):
    """Unit tests for ActiveDirectoryBackend."""

    def setUp(self):
        super(ActiveDirectoryBackendTests, self).setUp()

        # These settings will get overridden on future test runs, since
        # they'll be reloaded from siteconfig.
        settings.AD_DOMAIN_CONTROLLER = 'ad1.example.com ad2.example.com:123'
        settings.AD_DOMAIN_NAME = 'example.com'
        settings.AD_RECURSION_DEPTH = -1

        self.backend = ActiveDirectoryBackend()

        self.spy_on(ldap.initialize,
                    call_fake=lambda uri, *args, **kwargs: TestLDAPObject(uri))

    def test_authenticate_with_valid_credentials(self):
        """Testing ActiveDirectoryBackend.authenticate with valid credentials
        """
        self.spy_on(TestLDAPObject.simple_bind_s,
                    owner=TestLDAPObject)
        self.spy_on(TestLDAPObject.search_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpReturn([
                        ('CN=Test User,OU=MyOrg,DC=example,DC=com', {
                            'givenName': [b'Test'],
                            'sn': [b'User'],
                            'mail': [b'test-user@corp.example.com'],
                        }),
                    ]))

        user = self.backend.authenticate(request=None,
                                         username='test-user',
                                         password='test-pass')

        self.assertIsNotNone(user)

        self.assertIsNotNone(user.pk)
        self.assertEqual(user.username, 'test-user')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.email, 'test-user@corp.example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        self.assertSpyCalledWith(
            TestLDAPObject.simple_bind_s,
            'test-user@example.com',
            'test-pass')
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=example,dc=com',
            filterstr='(&(objectClass=user)(sAMAccountName=test-user))',
            scope=ldap.SCOPE_SUBTREE)

    def test_authenticate_with_valid_credentials_with_at(self):
        """Testing ActiveDirectoryBackend.authenticate with valid credentials
        and "@" in username
        """
        self.spy_on(TestLDAPObject.simple_bind_s,
                    owner=TestLDAPObject)
        self.spy_on(TestLDAPObject.search_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpReturn([
                        ('CN=Test User,OU=MyOrg,DC=example,DC=com', {
                            'givenName': [b'Test'],
                            'sn': [b'User'],
                            'mail': [b'test-user@corp.example.com'],
                        }),
                    ]))

        user = self.backend.authenticate(request=None,
                                         username='test-user@test',
                                         password='test-pass')

        self.assertIsNotNone(user)

        self.assertIsNotNone(user.pk)
        self.assertEqual(user.username, 'test-user')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.email, 'test-user@corp.example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        self.assertSpyCalledWith(
            TestLDAPObject.simple_bind_s,
            'test-user@test.example.com',
            'test-pass')
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=test,dc=example,dc=com',
            filterstr='(&(objectClass=user)(sAMAccountName=test-user))',
            scope=ldap.SCOPE_SUBTREE)

    def test_authenticate_with_valid_credentials_with_backslash(self):
        """Testing ActiveDirectoryBackend.authenticate with valid credentials
        and "\\" in username
        """
        self.spy_on(TestLDAPObject.simple_bind_s,
                    owner=TestLDAPObject)
        self.spy_on(TestLDAPObject.search_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpReturn([
                        ('CN=Test User,OU=MyOrg,DC=example,DC=com', {
                            'givenName': [b'Test'],
                            'sn': [b'User'],
                            'mail': [b'test-user@corp.example.com'],
                        }),
                    ]))

        user = self.backend.authenticate(request=None,
                                         username='test\\test-user',
                                         password='test-pass')

        self.assertIsNotNone(user)

        self.assertIsNotNone(user.pk)
        self.assertEqual(user.username, 'test-user')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.email, 'test-user@corp.example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        self.assertSpyCalledWith(
            TestLDAPObject.simple_bind_s,
            'test-user@test.example.com',
            'test-pass')
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=test,dc=example,dc=com',
            filterstr='(&(objectClass=user)(sAMAccountName=test-user))',
            scope=ldap.SCOPE_SUBTREE)

    def test_authenticate_with_empty_attrs(self):
        """Testing ActiveDirectoryBackend.authenticate with valid credentials
        and empty user attributes
        """
        self.spy_on(TestLDAPObject.simple_bind_s,
                    owner=TestLDAPObject)
        self.spy_on(TestLDAPObject.search_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpReturn([
                        ('CN=Test User,OU=MyOrg,DC=example,DC=com', {}),
                    ]))

        user = self.backend.authenticate(request=None,
                                         username='test-user',
                                         password='test-pass')

        self.assertIsNotNone(user)

        self.assertIsNotNone(user.pk)
        self.assertEqual(user.username, 'test-user')
        self.assertEqual(user.first_name, 'test-user')
        self.assertEqual(user.last_name, '')
        self.assertEqual(user.email, 'test-user@example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        self.assertSpyCalledWith(
            TestLDAPObject.simple_bind_s,
            'test-user@example.com',
            'test-pass')
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=example,dc=com',
            filterstr='(&(objectClass=user)(sAMAccountName=test-user))',
            scope=ldap.SCOPE_SUBTREE)

    @override_settings(AD_GROUP_NAME='required')
    def test_authenticate_with_in_required_group(self):
        """Testing ActiveDirectoryBackend.authenticate with valid credentials
        and in required group
        """
        self.spy_on(TestLDAPObject.simple_bind_s,
                    owner=TestLDAPObject)
        self.spy_on(
            TestLDAPObject.search_s,
            owner=TestLDAPObject,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ['dc=test,dc=corp,dc=example,dc=com'],
                    'call_fake': lambda *args, **kwargs: [
                        ('CN=Test User,OU=MyOrg,DC=example,DC=com', {
                            'givenName': [b'Test'],
                            'sn': [b'User'],
                            'mail': [b'test-user@corp.example.com'],
                            'memberOf': [
                                b'cn=required,ou=Groups,dc=example,dc=com',
                            ],
                        }),
                    ],
                },
                {
                    'args': ['dc=example,dc=com'],
                    'kwargs': {
                        'filterstr': '(&(objectClass=group)(cn=required))',
                        'scope': ldap.SCOPE_SUBTREE,
                    },
                    'call_fake': lambda *args, **kwargs: [],
                },
            ]))

        user = self.backend.authenticate(request=None,
                                         username='test-user@test.corp',
                                         password='test-pass')

        self.assertIsNotNone(user)

        self.assertIsNotNone(user.pk)
        self.assertEqual(user.username, 'test-user')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.email, 'test-user@corp.example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        self.assertSpyCalledWith(
            TestLDAPObject.simple_bind_s,
            'test-user@test.corp.example.com',
            'test-pass')
        self.assertSpyCallCount(TestLDAPObject.search_s, 2)
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=test,dc=corp,dc=example,dc=com',
            filterstr='(&(objectClass=user)(sAMAccountName=test-user))',
            scope=ldap.SCOPE_SUBTREE)
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=example,dc=com',
            filterstr='(&(objectClass=group)(cn=required))',
            scope=ldap.SCOPE_SUBTREE)

    @override_settings(AD_GROUP_NAME='required')
    def test_authenticate_with_in_required_group_recurse(self):
        """Testing ActiveDirectoryBackend.authenticate with valid credentials
        and in required group with recursion
        """
        self.spy_on(TestLDAPObject.simple_bind_s,
                    owner=TestLDAPObject)
        self.spy_on(
            TestLDAPObject.search_s,
            owner=TestLDAPObject,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ['dc=test,dc=corp,dc=example,dc=com'],
                    'call_fake': lambda *args, **kwargs: [
                        ('CN=Test User,OU=MyOrg,DC=example,DC=com', {
                            'givenName': [b'Test'],
                            'sn': [b'User'],
                            'mail': [b'test-user@corp.example.com'],
                            'memberOf': [
                                b'cn=other,ou=Groups,dc=example,dc=com',
                            ],
                        }),
                    ],
                },
                {
                    'args': ['dc=example,dc=com'],
                    'kwargs': {
                        'filterstr': '(&(objectClass=group)(cn=other))',
                        'scope': ldap.SCOPE_SUBTREE,
                    },
                    'call_fake': lambda *args, **kwargs: [
                        ('cn=other,ou=Groups,dc=example,dc=com', {
                            'memberOf': [
                                b'cn=other2,ou=Groups,dc=example,dc=com',
                            ],
                        }),
                    ],
                },
                {
                    'args': ['dc=example,dc=com'],
                    'kwargs': {
                        'filterstr': '(&(objectClass=group)(cn=other2))',
                        'scope': ldap.SCOPE_SUBTREE,
                    },
                    'call_fake': lambda *args, **kwargs: [
                        ('cn=other2,ou=Groups,dc=example,dc=com', {
                            'memberOf': [
                                b'cn=other,ou=Groups,dc=example,dc=com',
                                b'cn=required,ou=Groups,dc=example,dc=com',
                            ],
                        }),
                    ],
                },
                {
                    'args': ['dc=example,dc=com'],
                    'kwargs': {
                        'filterstr': '(&(objectClass=group)(cn=required))',
                        'scope': ldap.SCOPE_SUBTREE,
                    },
                    'call_fake': lambda *args, **kwargs: [],
                },
            ]))

        user = self.backend.authenticate(request=None,
                                         username='test-user@test.corp',
                                         password='test-pass')

        self.assertIsNotNone(user)

        self.assertIsNotNone(user.pk)
        self.assertEqual(user.username, 'test-user')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.email, 'test-user@corp.example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        self.assertSpyCalledWith(
            TestLDAPObject.simple_bind_s,
            'test-user@test.corp.example.com',
            'test-pass')
        self.assertSpyCallCount(TestLDAPObject.search_s, 4)
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=test,dc=corp,dc=example,dc=com',
            filterstr='(&(objectClass=user)(sAMAccountName=test-user))',
            scope=ldap.SCOPE_SUBTREE)
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=example,dc=com',
            filterstr='(&(objectClass=group)(cn=other))',
            scope=ldap.SCOPE_SUBTREE)
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=example,dc=com',
            filterstr='(&(objectClass=group)(cn=other2))',
            scope=ldap.SCOPE_SUBTREE)
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=example,dc=com',
            filterstr='(&(objectClass=group)(cn=required))',
            scope=ldap.SCOPE_SUBTREE)

    @override_settings(AD_GROUP_NAME='required',
                       AD_RECURSION_DEPTH=1)
    def test_authenticate_with_required_group_recurse_limit_hit(self):
        """Testing ActiveDirectoryBackend.authenticate with valid credentials
        and in required group recursion limit hit
        """
        self.spy_on(TestLDAPObject.simple_bind_s,
                    owner=TestLDAPObject)
        self.spy_on(
            TestLDAPObject.search_s,
            owner=TestLDAPObject,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ['dc=test,dc=corp,dc=example,dc=com'],
                    'call_fake': lambda *args, **kwargs: [
                        ('CN=Test User,OU=MyOrg,DC=example,DC=com', {
                            'givenName': [b'Test'],
                            'sn': [b'User'],
                            'mail': [b'test-user@corp.example.com'],
                            'memberOf': [
                                b'cn=other,ou=Groups,dc=example,dc=com',
                            ],
                        }),
                    ],
                },
                {
                    'args': ['dc=example,dc=com'],
                    'kwargs': {
                        'filterstr': '(&(objectClass=group)(cn=other))',
                        'scope': ldap.SCOPE_SUBTREE,
                    },
                    'call_fake': lambda *args, **kwargs: [
                        ('cn=other,ou=Groups,dc=example,dc=com', {
                            'memberOf': [
                                b'cn=other2,ou=Groups,dc=example,dc=com',
                            ],
                        }),
                    ],
                },
            ]))

        user = self.backend.authenticate(request=None,
                                         username='test-user@test.corp',
                                         password='test-pass')

        self.assertIsNone(user)

        self.assertSpyCalledWith(
            TestLDAPObject.simple_bind_s,
            'test-user@test.corp.example.com',
            'test-pass')
        self.assertSpyCallCount(TestLDAPObject.search_s, 2)
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=test,dc=corp,dc=example,dc=com',
            filterstr='(&(objectClass=user)(sAMAccountName=test-user))',
            scope=ldap.SCOPE_SUBTREE)
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=example,dc=com',
            filterstr='(&(objectClass=group)(cn=other))',
            scope=ldap.SCOPE_SUBTREE)

    @override_settings(AD_GROUP_NAME='required')
    def test_authenticate_with_not_in_required_group(self):
        """Testing ActiveDirectoryBackend.authenticate with valid credentials
        and not in required group
        """
        self.spy_on(TestLDAPObject.simple_bind_s,
                    owner=TestLDAPObject)
        self.spy_on(
            TestLDAPObject.search_s,
            owner=TestLDAPObject,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ['dc=test,dc=corp,dc=example,dc=com'],
                    'kwargs': {
                        'filterstr': ('(&(objectClass=user)'
                                      '(sAMAccountName=test-user))'),
                        'scope': ldap.SCOPE_SUBTREE,
                    },
                    'call_fake': lambda *args, **kwargs: [
                        ('CN=Test User,OU=MyOrg,DC=example,DC=com', {
                            'givenName': [b'Test'],
                            'sn': [b'User'],
                            'mail': [b'test-user@corp.example.com'],
                            'memberOf': [
                                b'cn=other,ou=Groups,dc=example,dc=com',
                            ],
                        }),
                    ],
                },
                {
                    'args': ['dc=example,dc=com'],
                    'kwargs': {
                        'filterstr': '(&(objectClass=group)(cn=other))',
                        'scope': ldap.SCOPE_SUBTREE,
                    },
                    'call_fake': lambda *args, **kwargs: [],
                },
            ]))

        user = self.backend.authenticate(request=None,
                                         username='test-user@test.corp',
                                         password='test-pass')

        self.assertIsNone(user)

        self.assertSpyCalledWith(
            TestLDAPObject.simple_bind_s,
            'test-user@test.corp.example.com',
            'test-pass')
        self.assertSpyCallCount(TestLDAPObject.search_s, 2)
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=test,dc=corp,dc=example,dc=com',
            filterstr='(&(objectClass=user)(sAMAccountName=test-user))',
            scope=ldap.SCOPE_SUBTREE)
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'dc=example,dc=com',
            filterstr='(&(objectClass=group)(cn=other))',
            scope=ldap.SCOPE_SUBTREE)

    def test_authenticate_with_invalid_credentials(self):
        """Testing ActiveDirectoryBackend.authenticate with invalid credentials
        """
        self.spy_on(TestLDAPObject.simple_bind_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpRaise(ldap.INVALID_CREDENTIALS()))
        self.spy_on(TestLDAPObject.search_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpReturn([
                        ('CN=Test User,OU=MyOrg,DC=example,DC=com', {
                            'givenName': [b'Test'],
                            'sn': [b'User'],
                            'mail': [b'test-user@corp.example.com'],
                        }),
                    ]))

        user = self.backend.authenticate(request=None,
                                         username='test-user',
                                         password='test-pass')

        self.assertIsNone(user)

        self.assertSpyCalledWith(
            TestLDAPObject.simple_bind_s,
            'test-user@example.com',
            'test-pass')
        self.assertSpyNotCalled(TestLDAPObject.search_s)

    def test_authenticate_with_server_down(self):
        """Testing ActiveDirectoryBackend.authenticate with Server Down error
        """
        self.spy_on(TestLDAPObject.simple_bind_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpRaise(ldap.SERVER_DOWN()))
        self.spy_on(TestLDAPObject.search_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpReturn([
                        ('CN=Test User,OU=MyOrg,DC=example,DC=com', {
                            'givenName': [b'Test'],
                            'sn': [b'User'],
                            'mail': [b'test-user@corp.example.com'],
                        }),
                    ]))

        user = self.backend.authenticate(request=None,
                                         username='test-user',
                                         password='test-pass')

        self.assertIsNone(user)

        self.assertSpyCalledWith(
            TestLDAPObject.simple_bind_s,
            'test-user@example.com',
            'test-pass')
        self.assertSpyNotCalled(TestLDAPObject.search_s)

    def test_authenticate_with_exception(self):
        """Testing ActiveDirectoryBackend.authenticate with unexpected
        exception
        """
        self.spy_on(TestLDAPObject.simple_bind_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpRaise(Exception('Kaboom!')))
        self.spy_on(TestLDAPObject.search_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpReturn([
                        ('CN=Test User,OU=MyOrg,DC=example,DC=com', {
                            'givenName': [b'Test'],
                            'sn': [b'User'],
                            'mail': [b'test-user@corp.example.com'],
                        }),
                    ]))

        user = self.backend.authenticate(request=None,
                                         username='test-user',
                                         password='test-pass')

        self.assertIsNone(user)

        self.assertSpyCalledWith(
            TestLDAPObject.simple_bind_s,
            'test-user@example.com',
            'test-pass')
        self.assertSpyNotCalled(TestLDAPObject.search_s)

    def test_find_domain_controllers_from_dns(self):
        """Testing ActiveDirectoryBackend.find_domain_controllers_from_dns"""
        self.spy_on(
            dns.resolver.query,
            op=kgb.SpyOpReturn(dns.resolver.Answer(
                qname=dns.name.from_text('_ldap._tcp.example.com'),
                rdtype=dns.rdatatype.SRV,
                rdclass=dns.rdataclass.IN,
                response=dns.message.from_text(
                    'id 12345\n'
                    'opcode QUERY\n'
                    'rcode NOERROR\n'
                    'flags QR RD RA\n'
                    ';QUESTION\n'
                    '_ldap._tcp.example.com. IN SRV\n'
                    ';ANSWER\n'
                    '_ldap._tcp.example.com. 299 IN SRV 10 1 389'
                    ' my-ad3.example.com.\n'
                    '_ldap._tcp.example.com. 299 IN SRV 5 1 390'
                    ' my-ad2.example.com.\n'
                    '_ldap._tcp.example.com. 299 IN SRV 5 5 391'
                    ' my-ad1.example.com.\n'
                    ';AUTHORITY\n'
                    ';ADDITIONAL\n'))))

        self.assertEqual(
            self.backend.find_domain_controllers_from_dns(),
            [
                (391, 'my-ad1.example.com'),
                (390, 'my-ad2.example.com'),
                (389, 'my-ad3.example.com'),
            ])

        self.assertSpyCalledWith(dns.resolver.query,
                                 '_ldap._tcp.example.com',
                                 rdtype='SRV')

    def test_find_domain_controllers_from_dns_with_custom_domain(self):
        """Testing ActiveDirectoryBackend.find_domain_controllers_from_dns
        with custom domain
        """
        self.spy_on(
            dns.resolver.query,
            op=kgb.SpyOpReturn(dns.resolver.Answer(
                qname=dns.name.from_text('_ldap._tcp.corp.example.com'),
                rdtype=dns.rdatatype.SRV,
                rdclass=dns.rdataclass.IN,
                response=dns.message.from_text(
                    'id 12345\n'
                    'opcode QUERY\n'
                    'rcode NOERROR\n'
                    'flags QR RD RA\n'
                    ';QUESTION\n'
                    '_ldap._tcp.corp.example.com. IN SRV\n'
                    ';ANSWER\n'
                    '_ldap._tcp.corp.example.com. 299 IN SRV 10 1 389'
                    ' my-ad3.example.com.\n'
                    '_ldap._tcp.corp.example.com. 299 IN SRV 5 1 390'
                    ' my-ad2.example.com.\n'
                    '_ldap._tcp.corp.example.com. 299 IN SRV 5 5 391'
                    ' my-ad1.example.com.\n'
                    ';AUTHORITY\n'
                    ';ADDITIONAL\n'))))

        self.assertEqual(
            self.backend.find_domain_controllers_from_dns('corp.example.com'),
            [
                (391, 'my-ad1.example.com'),
                (390, 'my-ad2.example.com'),
                (389, 'my-ad3.example.com'),
            ])

        self.assertSpyCalledWith(dns.resolver.query,
                                 '_ldap._tcp.corp.example.com',
                                 rdtype='SRV')

    def test_find_domain_controllers_from_dns_with_not_found(self):
        """Testing ActiveDirectoryBackend.find_domain_controllers_from_dns
        with domain not found
        """
        self.spy_on(dns.resolver.query,
                    op=kgb.SpyOpRaise(dns.resolver.NXDOMAIN()))

        self.assertEqual(self.backend.find_domain_controllers_from_dns(), [])

        self.assertSpyCalledWith(dns.resolver.query,
                                 '_ldap._tcp.example.com',
                                 rdtype='SRV')

    def test_find_domain_controllers_from_dns_with_error(self):
        """Testing ActiveDirectoryBackend.find_domain_controllers_from_dns
        with error
        """
        self.spy_on(dns.resolver.query,
                    op=kgb.SpyOpRaise(Exception('Kaboom!')))

        self.assertEqual(self.backend.find_domain_controllers_from_dns(), [])

        self.assertSpyCalledWith(dns.resolver.query,
                                 '_ldap._tcp.example.com',
                                 rdtype='SRV')

    @override_settings(AD_SEARCH_ROOT='ou=Test,dc=example,dc=com')
    def test_get_ldap_search_root_with_setting(self):
        """Testing ActiveDirectoryBackend.get_ldap_search_root with
        AD_SEARCH_ROOT
        """
        self.assertEqual(self.backend.get_ldap_search_root(),
                         'ou=Test,dc=example,dc=com')

    def test_get_ldap_search_root_with_defaults(self):
        """Testing ActiveDirectoryBackend.get_ldap_search_root with
        defaults
        """
        self.assertEqual(self.backend.get_ldap_search_root(),
                         'dc=example,dc=com')

    def test_get_ldap_search_root_with_custom_domain(self):
        """Testing ActiveDirectoryBackend.get_ldap_search_root with
        custom user_domain
        """
        self.assertEqual(self.backend.get_ldap_search_root('corp.example.com'),
                         'dc=corp,dc=example,dc=com')

    @override_settings(AD_OU_NAME='Test')
    def test_get_ldap_search_root_with_ad_ou_name(self):
        """Testing ActiveDirectoryBackend.get_ldap_search_root with
        AD_OU_NAME
        """
        self.assertEqual(self.backend.get_ldap_search_root(),
                         'ou=Test,dc=example,dc=com')

    def test_get_or_create_user_without_ad_user_data_and_with_user(self):
        """Testing ActiveDirectoryBackend.get_or_create_user without
        ad_user_data and with user in database
        """
        user = User.objects.create(username='test')

        self.assertEqual(self.backend.get_or_create_user('test'), user)

    def test_get_or_create_user_without_ad_user_data_and_without_user(self):
        """Testing ActiveDirectoryBackend.get_or_create_user without
        ad_user_data and with user not in database
        """
        self.assertIsNone(self.backend.get_or_create_user('test'))

    def test_get_ldap_connections(self):
        """Testing ActiveDirectoryBackend.get_ldap_connections"""
        connections = list(self.backend.get_ldap_connections('example.com'))

        self.assertEqual(len(connections), 2)
        self.assertEqual(connections[0][0], 'ldap://ad1.example.com:389')
        self.assertEqual(connections[1][0], 'ldap://ad2.example.com:123')

    @override_settings(AD_FIND_DC_FROM_DNS=True)
    def test_get_ldap_connections_from_dns(self):
        """Testing ActiveDirectoryBackend.get_ldap_connections with
        AD_FIND_DC_FROM_DNS=True
        """
        self.spy_on(
            dns.resolver.query,
            op=kgb.SpyOpReturn(dns.resolver.Answer(
                qname=dns.name.from_text('_ldap._tcp.example.com'),
                rdtype=dns.rdatatype.SRV,
                rdclass=dns.rdataclass.IN,
                response=dns.message.from_text(
                    'id 12345\n'
                    'opcode QUERY\n'
                    'rcode NOERROR\n'
                    'flags QR RD RA\n'
                    ';QUESTION\n'
                    '_ldap._tcp.example.com. IN SRV\n'
                    ';ANSWER\n'
                    '_ldap._tcp.example.com. 299 IN SRV 10 1 389'
                    ' my-ad3.example.com.\n'
                    '_ldap._tcp.example.com. 299 IN SRV 5 1 390'
                    ' my-ad2.example.com.\n'
                    '_ldap._tcp.example.com. 299 IN SRV 5 5 391'
                    ' my-ad1.example.com.\n'
                    ';AUTHORITY\n'
                    ';ADDITIONAL\n'))))

        connections = list(self.backend.get_ldap_connections('example.com'))

        self.assertEqual(len(connections), 3)
        self.assertEqual(connections[0][0], 'ldap://my-ad1.example.com:391')
        self.assertEqual(connections[1][0], 'ldap://my-ad2.example.com:390')
        self.assertEqual(connections[2][0], 'ldap://my-ad3.example.com:389')

    @override_settings(AD_FIND_DC_FROM_DNS=True)
    def test_get_ldap_connections_from_dns_with_not_found(self):
        """Testing ActiveDirectoryBackend.get_ldap_connections with
        AD_FIND_DC_FROM_DNS=True with domain not found
        """
        self.spy_on(dns.resolver.query,
                    op=kgb.SpyOpRaise(dns.resolver.NXDOMAIN()))

        self.assertEqual(
            list(self.backend.get_ldap_connections('example.com')),
            [])

    @override_settings(AD_FIND_DC_FROM_DNS=True)
    def test_get_ldap_connections_from_dns_with_error(self):
        """Testing ActiveDirectoryBackend.get_ldap_connections with
        AD_FIND_DC_FROM_DNS=True with error
        """
        self.spy_on(dns.resolver.query,
                    op=kgb.SpyOpRaise(Exception('Kaboom!')))

        self.assertEqual(
            list(self.backend.get_ldap_connections('example.com')),
            [])
