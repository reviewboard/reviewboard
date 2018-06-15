"""Unit tests for LDAPBackend."""

from __future__ import unicode_literals

import nose
from django.conf import settings
from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

try:
    import ldap
except ImportError:
    ldap = None

from reviewboard.accounts.backends import LDAPBackend
from reviewboard.testing import TestCase


class BaseTestLDAPObject(object):
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


class LDAPAuthBackendTests(SpyAgency, TestCase):
    """Unit tests for the LDAP authentication backend."""

    DEFAULT_FILTER_STR = '(objectClass=*)'

    def setUp(self):
        if ldap is None:
            raise nose.SkipTest()

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

    @add_fixtures(['test_users'])
    def test_authenticate_with_valid_credentials(self):
        """Testing LDAPBackend.authenticate with valid credentials"""
        class TestLDAPObject(BaseTestLDAPObject):
            def bind_s(ldapo, username, password):
                self.assertEqual(username,
                                 'CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM')
                self.assertEqual(password, 'mypass')

            def search_s(ldapo, base, scope,
                         filter_str=self.DEFAULT_FILTER_STR,
                         *args, **kwargs):
                self.assertEqual(base, 'CN=admin,DC=example,DC=com')
                self.assertEqual(scope, ldap.SCOPE_SUBTREE)
                self.assertEqual(filter_str, '(uid=doc)')

                return [['CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM']]

        self._patch_ldap(TestLDAPObject)

        user = self.backend.authenticate(username='doc', password='mypass')
        self.assertIsNotNone(user)

        self.assertEqual(user.username, 'doc')
        self.assertEqual(user.first_name, 'Doc')
        self.assertEqual(user.last_name, 'Dwarf')
        self.assertEqual(user.email, 'doc@example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_authenticate_with_invalid_credentials(self):
        """Testing LDAPBackend.authenticate with invalid credentials"""
        class TestLDAPObject(BaseTestLDAPObject):
            def bind_s(ldapo, username, password):
                self.assertEqual(username,
                                 'CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM')
                self.assertEqual(password, 'mypass')

                raise ldap.INVALID_CREDENTIALS()

            def search_s(ldapo, base, scope,
                         filter_str=self.DEFAULT_FILTER_STR,
                         *args, **kwargs):
                self.assertEqual(base, 'CN=admin,DC=example,DC=com')
                self.assertEqual(scope, ldap.SCOPE_SUBTREE)
                self.assertEqual(filter_str, '(uid=doc)')

                return [['CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM']]

        self._patch_ldap(TestLDAPObject)

        user = self.backend.authenticate(username='doc', password='mypass')
        self.assertIsNone(user)

    def test_authenticate_with_ldap_error(self):
        """Testing LDAPBackend.authenticate with LDAP error"""
        class TestLDAPObject(BaseTestLDAPObject):
            def bind_s(ldapo, username, password):
                self.assertEqual(username,
                                 'CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM')
                self.assertEqual(password, 'mypass')

                raise ldap.LDAPError()

            def search_s(ldapo, base, scope,
                         filter_str=self.DEFAULT_FILTER_STR,
                         *args, **kwargs):
                self.assertEqual(base, 'CN=admin,DC=example,DC=com')
                self.assertEqual(scope, ldap.SCOPE_SUBTREE)
                self.assertEqual(filter_str, '(uid=doc)')

                return [['CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM']]

        self._patch_ldap(TestLDAPObject)

        user = self.backend.authenticate(username='doc', password='mypass')
        self.assertIsNone(user)

    def test_authenticate_with_exception(self):
        """Testing LDAPBackend.authenticate with unexpected exception"""
        class TestLDAPObject(BaseTestLDAPObject):
            def bind_s(ldapo, username, password):
                self.assertEqual(username,
                                 'CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM')
                self.assertEqual(password, 'mypass')

                raise Exception('oh no!')

            def search_s(ldapo, base, scope,
                         filter_str=self.DEFAULT_FILTER_STR,
                         *args, **kwargs):
                self.assertEqual(base, 'CN=admin,DC=example,DC=com')
                self.assertEqual(scope, ldap.SCOPE_SUBTREE)
                self.assertEqual(filter_str, '(uid=doc)')

                return [['CN=Doc Dwarf,OU=MyOrg,DC=example,DC=COM']]

        self._patch_ldap(TestLDAPObject)

        user = self.backend.authenticate(username='doc', password='mypass')
        self.assertIsNone(user)

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
        class TestLDAPObject(BaseTestLDAPObject):
            def search_s(ldapo, base, scope,
                         filter_str=self.DEFAULT_FILTER_STR,
                         *args, **kwargs):
                user_dn = 'CN=Bob BobBob,OU=MyOrg,DC=example,DC=COM'

                if base == 'CN=admin,DC=example,DC=com':
                    self.assertEqual(scope, ldap.SCOPE_SUBTREE)
                    self.assertEqual(filter_str, '(uid=doc)')

                    return [[user_dn]]
                elif base == user_dn:
                    self.assertEqual(scope, ldap.SCOPE_BASE)
                    self.assertEqual(filter_str, self.DEFAULT_FILTER_STR)

                    return [[
                        user_dn,
                        {
                            'givenName': ['Bob'],
                            'sn': ['BobBob'],
                            'email': ['imbob@example.com'],
                        }
                    ]]
                else:
                    self.fail('Unexpected LDAP base "%s" in search_s() call.'
                              % base)

        self._patch_ldap(TestLDAPObject)

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
        class TestLDAPObject(BaseTestLDAPObject):
            def search_s(ldapo, base, scope,
                         filter_str=self.DEFAULT_FILTER_STR,
                         *args, **kwargs):
                self.assertEqual(base, 'CN=admin,DC=example,DC=com')
                self.assertEqual(scope, ldap.SCOPE_SUBTREE)
                self.assertEqual(filter_str, '(uid=doc)')

                return []

        self._patch_ldap(TestLDAPObject)

        self.assertEqual(User.objects.count(), 0)

        user = self.backend.get_or_create_user(username='doc', request=None)

        self.assertIsNone(user)
        self.assertEqual(User.objects.count(), 0)

    def test_get_or_create_user_with_fullname_without_space(self):
        """Testing LDAPBackend.get_or_create_user with a user whose full name
        does not contain a space
        """
        class TestLDAPObject(BaseTestLDAPObject):
            def search_s(ldapo, base, scope,
                         filter_str=self.DEFAULT_FILTER_STR,
                         *args, **kwargs):
                user_dn = 'CN=Bob,OU=MyOrg,DC=example,DC=COM'
                settings.LDAP_FULL_NAME_ATTRIBUTE = 'fn'

                if base == 'CN=admin,DC=example,DC=com':
                    self.assertEqual(scope, ldap.SCOPE_SUBTREE)
                    self.assertEqual(filter_str, '(uid=doc)')

                    return [[user_dn]]
                elif base == user_dn:
                    self.assertEqual(scope, ldap.SCOPE_BASE)
                    self.assertEqual(filter_str, self.DEFAULT_FILTER_STR)

                    return [[
                        user_dn,
                        {
                            'fn': ['Bob'],
                            'email': ['imbob@example.com']
                        }
                    ]]
                else:
                    self.fail('Unexpected LDAP base "%s" in search_s() call.'
                              % base)

        self._patch_ldap(TestLDAPObject)

        self.assertEqual(User.objects.count(), 0)

        user = self.backend.get_or_create_user(username='doc', request=None)
        self.assertIsNotNone(user)
        self.assertEqual(User.objects.count(), 1)

        self.assertEqual(user.first_name, 'Bob')
        self.assertEqual(user.last_name, '')

    def _patch_ldap(self, cls):
        self.spy_on(ldap.initialize,
                    call_fake=lambda uri, *args, **kwargs: cls(uri))
