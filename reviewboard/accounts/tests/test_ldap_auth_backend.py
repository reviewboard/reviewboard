"""Unit tests for LDAPBackend."""

from __future__ import unicode_literals

import kgb
import ldap
from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.backends import LDAPBackend
from reviewboard.testing import TestCase


class TestLDAPObject(object):
    def __init__(self, *args, **kwargs):
        pass

    def set_option(self, option, value):
        pass

    def start_tls_s(self):
        pass

    def simple_bind_s(self, *args, **kwargs):
        pass

    def bind_s(self, *args, **kwargs):
        pass

    def search_s(self, *args, **kwargs):
        pass


class LDAPAuthBackendTests(kgb.SpyAgency, TestCase):
    """Unit tests for the LDAP authentication backend."""

    DEFAULT_FILTER_STR = '(objectClass=*)'

    def setUp(self):
        super(LDAPAuthBackendTests, self).setUp()

        # These settings will get overridden on future test runs, since
        # they'll be reloaded from siteconfig.
        settings.LDAP_BASE_DN = 'CN=admin,DC=example,DC=com'
        settings.LDAP_GIVEN_NAME_ATTRIBUTE = 'givenName'
        settings.LDAP_SURNAME_ATTRIBUTE = 'sn'
        settings.LDAP_EMAIL_ATTRIBUTE = 'email'
        settings.LDAP_UID = 'uid'
        settings.LDAP_UID_MASK = None
        settings.LDAP_FULL_NAME_ATTRIBUTE = None

        self.backend = LDAPBackend()

        self.spy_on(ldap.initialize,
                    call_fake=lambda uri, *args, **kwargs: TestLDAPObject(uri))

    @add_fixtures(['test_users'])
    def test_authenticate_with_valid_credentials(self):
        """Testing LDAPBackend.authenticate with valid credentials"""
        self.spy_on(TestLDAPObject.bind_s,
                    owner=TestLDAPObject)
        self.spy_on(TestLDAPObject.search_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpReturn([
                        ('CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM', {}),
                    ]))

        user = self.backend.authenticate(request=None,
                                         username='doc',
                                         password='mypass')
        self.assertIsNotNone(user)

        self.assertEqual(user.username, 'doc')
        self.assertEqual(user.first_name, 'Doc')
        self.assertEqual(user.last_name, 'Dwarf')
        self.assertEqual(user.email, 'doc@example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        self.assertSpyCalledWith(TestLDAPObject.bind_s,
                                 'CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM',
                                 'mypass')
        self.assertSpyCalledWith(TestLDAPObject.search_s,
                                 'CN=admin,DC=example,DC=com',
                                 ldap.SCOPE_SUBTREE,
                                 '(uid=doc)')

    def test_authenticate_with_invalid_credentials(self):
        """Testing LDAPBackend.authenticate with invalid credentials"""
        self.spy_on(TestLDAPObject.bind_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpRaise(ldap.INVALID_CREDENTIALS()))
        self.spy_on(TestLDAPObject.search_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpReturn([
                        ('CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM', {}),
                    ]))

        user = self.backend.authenticate(request=None,
                                         username='doc',
                                         password='mypass')
        self.assertIsNone(user)

        self.assertSpyCalledWith(
            TestLDAPObject.bind_s,
            'CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM',
            'mypass')
        self.assertSpyCalledWith(
            TestLDAPObject.search_s,
            'CN=admin,DC=example,DC=com',
            ldap.SCOPE_SUBTREE,
            '(uid=doc)')

    def test_authenticate_with_ldap_error(self):
        """Testing LDAPBackend.authenticate with LDAP error"""
        self.spy_on(TestLDAPObject.bind_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpRaise(ldap.LDAPError()))
        self.spy_on(TestLDAPObject.search_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpReturn([
                        ('CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM', {}),
                    ]))

        user = self.backend.authenticate(request=None,
                                         username='doc',
                                         password='mypass')
        self.assertIsNone(user)

        self.assertSpyCalledWith(TestLDAPObject.bind_s,
                                 'CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM',
                                 'mypass')
        self.assertSpyCalledWith(TestLDAPObject.search_s,
                                 'CN=admin,DC=example,DC=com',
                                 ldap.SCOPE_SUBTREE,
                                 '(uid=doc)')

    def test_authenticate_with_exception(self):
        """Testing LDAPBackend.authenticate with unexpected exception"""
        self.spy_on(TestLDAPObject.bind_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpRaise(Exception('oh no!')))
        self.spy_on(TestLDAPObject.search_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpReturn([
                        ('CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM', {}),
                    ]))

        user = self.backend.authenticate(request=None,
                                         username='doc',
                                         password='mypass')
        self.assertIsNone(user)

        self.assertSpyCalledWith(TestLDAPObject.bind_s,
                                 'CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM',
                                 'mypass')
        self.assertSpyCalledWith(TestLDAPObject.search_s,
                                 'CN=admin,DC=example,DC=com',
                                 ldap.SCOPE_SUBTREE,
                                 '(uid=doc)')

    @add_fixtures(['test_users'])
    def test_get_or_create_user_with_existing_user(self):
        """Testing LDAPBackend.get_or_create_user with existing user"""
        original_count = User.objects.count()
        user = User.objects.get(username='doc')
        result = self.backend.get_or_create_user(username='doc', request=None)

        self.assertEqual(original_count, User.objects.count())
        self.assertEqual(user, result)

    def test_get_or_create_user_in_ldap(self):
        """Testing LDAPBackend.get_or_create_user with new user found in LDAP
        """
        user_dn = 'CN=Bob BobBob,OU=MyOrg,DC=example,DC=COM'

        self.spy_on(
            TestLDAPObject.search_s,
            owner=TestLDAPObject,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ('CN=admin,DC=example,DC=com',
                             ldap.SCOPE_SUBTREE, '(uid=doc)'),
                    'call_fake': lambda *args, **kwargs: [(user_dn, {})],
                },
                {
                    'args': (user_dn, ldap.SCOPE_BASE),
                    'call_fake': lambda *args, **kwargs: [
                        (user_dn, {
                            'givenName': [b'Bob'],
                            'sn': [b'BobBob'],
                            'email': [b'imbob@example.com'],
                        }),
                    ],
                },
            ]))

        self.assertEqual(User.objects.count(), 0)

        user = self.backend.get_or_create_user(username='doc', request=None)
        self.assertIsNotNone(user)
        self.assertEqual(User.objects.count(), 1)

        self.assertEqual(user.username, 'doc')
        self.assertEqual(user.first_name, 'Bob')
        self.assertEqual(user.last_name, 'BobBob')
        self.assertEqual(user.email, 'imbob@example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_get_or_create_user_not_in_ldap(self):
        """Testing LDAPBackend.get_or_create_user with new user not found in
        LDAP
        """
        self.spy_on(TestLDAPObject.search_s,
                    owner=TestLDAPObject,
                    op=kgb.SpyOpReturn([]))

        self.assertEqual(User.objects.count(), 0)

        user = self.backend.get_or_create_user(username='doc', request=None)

        self.assertIsNone(user)
        self.assertEqual(User.objects.count(), 0)

        self.assertSpyCalledWith(TestLDAPObject.search_s,
                                 'CN=admin,DC=example,DC=com',
                                 ldap.SCOPE_SUBTREE,
                                 '(uid=doc)')

    @override_settings(LDAP_GIVEN_NAME_ATTRIBUTE='myFirstName')
    def test_get_or_create_user_with_empty_info(self):
        """Testing LDAPBackend.get_or_create_user with empty information in
        LDAP
        """
        user_dn = 'CN=Bob,OU=MyOrg,DC=example,DC=COM'

        self.spy_on(
            TestLDAPObject.search_s,
            owner=TestLDAPObject,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ('CN=admin,DC=example,DC=com',
                             ldap.SCOPE_SUBTREE, '(uid=doc)'),
                    'call_fake': lambda *args, **kwargs: [(user_dn, {})],
                },
                {
                    'args': (user_dn, ldap.SCOPE_BASE),
                    'call_fake': lambda *args, **kwargs: [(user_dn, {})]
                },
            ]))

        self.assertEqual(User.objects.count(), 0)

        user = self.backend.get_or_create_user(username='doc',
                                               request=None)

        self.assertIsNotNone(user)
        self.assertEqual(User.objects.count(), 1)

        self.assertEqual(user.first_name, 'doc')
        self.assertEqual(user.last_name, '')
        self.assertEqual(user.email, '')

    @override_settings(LDAP_GIVEN_NAME_ATTRIBUTE='myFirstName')
    def test_get_or_create_user_with_given_name_attr(self):
        """Testing LDAPBackend.get_or_create_user with
        LDAP_GIVEN_NAME_ATTRIBUTE
        """
        user_dn = 'CN=Bob,OU=MyOrg,DC=example,DC=COM'

        self.spy_on(
            TestLDAPObject.search_s,
            owner=TestLDAPObject,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ('CN=admin,DC=example,DC=com',
                             ldap.SCOPE_SUBTREE, '(uid=doc)'),
                    'call_fake': lambda *args, **kwargs: [(user_dn, {})],
                },
                {
                    'args': (user_dn, ldap.SCOPE_BASE),
                    'call_fake': lambda *args, **kwargs: [
                        (user_dn, {
                            'myFirstName': [b'Bob'],
                            'email': [b'imbob@example.com'],
                        }),
                    ],
                },
            ]))

        self.assertEqual(User.objects.count(), 0)

        user = self.backend.get_or_create_user(username='doc',
                                               request=None)

        self.assertIsNotNone(user)
        self.assertEqual(User.objects.count(), 1)

        self.assertEqual(user.first_name, 'Bob')
        self.assertEqual(user.last_name, '')
        self.assertEqual(user.email, 'imbob@example.com')

    @override_settings(LDAP_SURNAME_ATTRIBUTE='myLastName')
    def test_get_or_create_user_with_surname_attr(self):
        """Testing LDAPBackend.get_or_create_user with LDAP_SURNAME_ATTRIBUTE
        """
        user_dn = 'CN=Bob,OU=MyOrg,DC=example,DC=COM'

        self.spy_on(
            TestLDAPObject.search_s,
            owner=TestLDAPObject,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ('CN=admin,DC=example,DC=com',
                             ldap.SCOPE_SUBTREE, '(uid=doc)'),
                    'call_fake': lambda *args, **kwargs: [(user_dn, {})],
                },
                {
                    'args': (user_dn, ldap.SCOPE_BASE),
                    'call_fake': lambda *args, **kwargs: [
                        (user_dn, {
                            'givenName': [b'Bob'],
                            'myLastName': [b'Bub'],
                            'email': [b'imbob@example.com'],
                        }),
                    ],
                },
            ]))

        self.assertEqual(User.objects.count(), 0)

        user = self.backend.get_or_create_user(username='doc',
                                               request=None)

        self.assertIsNotNone(user)
        self.assertEqual(User.objects.count(), 1)

        self.assertEqual(user.first_name, 'Bob')
        self.assertEqual(user.last_name, 'Bub')
        self.assertEqual(user.email, 'imbob@example.com')

    @override_settings(LDAP_FULL_NAME_ATTRIBUTE='fn')
    def test_get_or_create_user_with_fullname(self):
        """Testing LDAPBackend.get_or_create_user with LDAP_FULL_NAME_ATTRIBUTE
        """
        user_dn = 'CN=Bob,OU=MyOrg,DC=example,DC=COM'

        self.spy_on(
            TestLDAPObject.search_s,
            owner=TestLDAPObject,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ('CN=admin,DC=example,DC=com',
                             ldap.SCOPE_SUBTREE, '(uid=doc)'),
                    'call_fake': lambda *args, **kwargs: [(user_dn, {})],
                },
                {
                    'args': (user_dn, ldap.SCOPE_BASE),
                    'call_fake': lambda *args, **kwargs: [
                        (user_dn, {
                            'fn': [b'Bob Bab Bub'],
                            'email': [b'imbob@example.com'],
                        }),
                    ],
                },
            ]))

        self.assertEqual(User.objects.count(), 0)

        user = self.backend.get_or_create_user(username='doc',
                                               request=None)

        self.assertIsNotNone(user)
        self.assertEqual(User.objects.count(), 1)

        self.assertEqual(user.first_name, 'Bob')
        self.assertEqual(user.last_name, 'Bab Bub')
        self.assertEqual(user.email, 'imbob@example.com')

    @override_settings(LDAP_FULL_NAME_ATTRIBUTE='fn')
    def test_get_or_create_user_with_fullname_without_space(self):
        """Testing LDAPBackend.get_or_create_user with LDAP_FULL_NAME_ATTRIBUTE
        and user whose full name does not contain a space
        """
        user_dn = 'CN=Bob,OU=MyOrg,DC=example,DC=COM'

        self.spy_on(
            TestLDAPObject.search_s,
            owner=TestLDAPObject,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ('CN=admin,DC=example,DC=com',
                             ldap.SCOPE_SUBTREE, '(uid=doc)'),
                    'call_fake': lambda *args, **kwargs: [(user_dn, {})],
                },
                {
                    'args': (user_dn, ldap.SCOPE_BASE),
                    'call_fake': lambda *args, **kwargs: [
                        (user_dn, {
                            'fn': [b'Bob'],
                            'email': [b'imbob@example.com'],
                        }),
                    ],
                },
            ]))

        self.assertEqual(User.objects.count(), 0)

        user = self.backend.get_or_create_user(username='doc',
                                               request=None)

        self.assertIsNotNone(user)
        self.assertEqual(User.objects.count(), 1)

        self.assertEqual(user.first_name, 'Bob')
        self.assertEqual(user.last_name, '')
        self.assertEqual(user.email, 'imbob@example.com')
