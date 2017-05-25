from __future__ import unicode_literals

import hashlib
import logging
import pkg_resources
import re
import sre_constants
from warnings import warn

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.contrib.auth import get_backends
from django.contrib.auth import hashers
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from djblets.db.query import get_object_or_none
from djblets.siteconfig.models import SiteConfiguration
try:
    import ldap
    from ldap.filter import filter_format
except ImportError:
    ldap = None

from reviewboard.accounts.forms.auth import (ActiveDirectorySettingsForm,
                                             LDAPSettingsForm,
                                             NISSettingsForm,
                                             StandardAuthSettingsForm,
                                             X509SettingsForm,
                                             HTTPBasicSettingsForm)
from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.site.models import LocalSite


_registered_auth_backends = {}
_enabled_auth_backends = []
_auth_backend_setting = None
_populated = False


INVALID_USERNAME_CHAR_REGEX = re.compile(r'[^\w.@+-]')


class AuthBackend(object):
    """The base class for Review Board authentication backends."""

    backend_id = None
    name = None
    settings_form = None
    supports_anonymous_user = True
    supports_object_permissions = True
    supports_registration = False
    supports_change_name = False
    supports_change_email = False
    supports_change_password = False
    login_instructions = None

    def authenticate(self, username, password):
        """Authenticate the user.

        This will authenticate the username and return the appropriate User
        object, or None.
        """
        raise NotImplementedError

    def get_or_create_user(self, username, request):
        """Get an existing user, or create one if it does not exist."""
        raise NotImplementedError

    def get_user(self, user_id):
        """Get an existing user, or None if it does not exist."""
        return get_object_or_none(User, pk=user_id)

    def update_password(self, user, password):
        """Update the user's password on the backend.

        Authentication backends can override this to update the password
        on the backend. This will only be called if
        :py:attr:`supports_change_password` is ``True``.

        By default, this will raise NotImplementedError.
        """
        raise NotImplementedError

    def update_name(self, user):
        """Update the user's name on the backend.

        The first name and last name will already be stored in the provided
        ``user`` object.

        Authentication backends can override this to update the name
        on the backend based on the values in ``user``. This will only be
        called if :py:attr:`supports_change_name` is ``True``.

        By default, this will do nothing.
        """
        pass

    def update_email(self, user):
        """Update the user's e-mail address on the backend.

        The e-mail address will already be stored in the provided
        ``user`` object.

        Authentication backends can override this to update the e-mail
        address on the backend based on the values in ``user``. This will only
        be called if :py:attr:`supports_change_email` is ``True``.

        By default, this will do nothing.
        """
        pass

    def query_users(self, query, request):
        """Search for users on the back end.

        This call is executed when the User List web API resource is called,
        before the database is queried.

        Authentication backends can override this to perform an external
        query. Results should be written to the database as standard
        Review Board users, which will be matched and returned by the web API
        call.

        The ``query`` parameter contains the value of the ``q`` search
        parameter of the web API call (e.g. /users/?q=foo), if any.

        Errors can be passed up to the web API layer by raising a
        reviewboard.accounts.errors.UserQueryError exception.

        By default, this will do nothing.
        """
        pass

    def search_users(self, query, request):
        """Custom user-database search.

        This call is executed when the User List web API resource is called
        and the ``q`` search parameter is provided, indicating a search
        query.

        It must return either a django.db.models.Q object or None.  All
        enabled backends are called until a Q object is returned.  If one
        isn't returned, a default search is executed.
        """
        return None


class StandardAuthBackend(AuthBackend, ModelBackend):
    """Authenticate users against the local database.

    This will authenticate a user against their entry in the database, if
    the user has a local password stored. This is the default form of
    authentication in Review Board.

    This backend also handles permission checking for users on LocalSites.
    In Django, this is the responsibility of at least one auth backend in
    the list of configured backends.

    Regardless of the specific type of authentication chosen for the
    installation, StandardAuthBackend will always be provided in the list
    of configured backends. Because of this, it will always be able to
    handle authentication against locally added users and handle
    LocalSite-based permissions for all configurations.
    """

    backend_id = 'builtin'
    name = _('Standard Registration')
    settings_form = StandardAuthSettingsForm
    supports_registration = True
    supports_change_name = True
    supports_change_email = True
    supports_change_password = True

    _VALID_LOCAL_SITE_PERMISSIONS = [
        'hostingsvcs.change_hostingserviceaccount',
        'hostingsvcs.create_hostingserviceaccount',
        'reviews.add_group',
        'reviews.can_change_status',
        'reviews.can_edit_reviewrequest',
        'reviews.can_submit_as_another_user',
        'reviews.change_default_reviewer',
        'reviews.change_group',
        'reviews.delete_file',
        'reviews.delete_screenshot',
        'scmtools.add_repository',
        'scmtools.change_repository',
    ]

    def authenticate(self, username, password):
        """Authenticate the user.

        This will authenticate the username and return the appropriate User
        object, or None.
        """
        return ModelBackend.authenticate(self, username, password)

    def get_or_create_user(self, username, request):
        """Get an existing user, or create one if it does not exist."""
        return get_object_or_none(User, username=username)

    def update_password(self, user, password):
        """Update the given user's password."""
        user.password = hashers.make_password(password)

    def get_all_permissions(self, user, obj=None):
        """Get a list of all permissions for a user.

        If a LocalSite instance is passed as ``obj``, then the permissions
        returned will be those that the user has on that LocalSite. Otherwise,
        they will be their global permissions.

        It is not legal to pass any other object.
        """
        if obj is not None and not isinstance(obj, LocalSite):
            logging.error('Unexpected object %r passed to '
                          'StandardAuthBackend.get_all_permissions. '
                          'Returning an empty list.',
                          obj)

            if settings.DEBUG:
                raise ValueError('Unexpected object %r' % obj)

            return set()

        if user.is_anonymous():
            return set()

        # First, get the list of all global permissions.
        #
        # Django's ModelBackend doesn't support passing an object, and will
        # return an empty set, so don't pass an object for this attempt.
        permissions = \
            super(StandardAuthBackend, self).get_all_permissions(user)

        if obj is not None:
            # We know now that this is a LocalSite, due to the assertion
            # above.
            if not hasattr(user, '_local_site_perm_cache'):
                user._local_site_perm_cache = {}

            if obj.pk not in user._local_site_perm_cache:
                perm_cache = set()

                try:
                    site_profile = user.get_site_profile(obj)
                    site_perms = site_profile.permissions or {}

                    if site_perms:
                        perm_cache = set([
                            key
                            for key, value in six.iteritems(site_perms)
                            if value
                        ])
                except LocalSiteProfile.DoesNotExist:
                    pass

                user._local_site_perm_cache[obj.pk] = perm_cache

            permissions = permissions.copy()
            permissions.update(user._local_site_perm_cache[obj.pk])

        return permissions

    def has_perm(self, user, perm, obj=None):
        """Get whether or not a user has the given permission.

        If a LocalSite instance is passed as ``obj``, then the permissions
        checked will be those that the user has on that LocalSite. Otherwise,
        they will be their global permissions.

        It is not legal to pass any other object.
        """
        if obj is not None and not isinstance(obj, LocalSite):
            logging.error('Unexpected object %r passed to has_perm. '
                          'Returning False.', obj)

            if settings.DEBUG:
                raise ValueError('Unexpected object %r' % obj)

            return False

        if not user.is_active:
            return False

        if obj is not None:
            if not hasattr(user, '_local_site_admin_for'):
                user._local_site_admin_for = {}

            if obj.pk not in user._local_site_admin_for:
                user._local_site_admin_for[obj.pk] = obj.is_mutable_by(user)

            if user._local_site_admin_for[obj.pk]:
                return perm in self._VALID_LOCAL_SITE_PERMISSIONS

        return super(StandardAuthBackend, self).has_perm(user, perm, obj)


class HTTPDigestBackend(AuthBackend):
    """Authenticate against a user in a digest password file."""

    backend_id = 'digest'
    name = _('HTTP Digest Authentication')
    settings_form = HTTPBasicSettingsForm
    login_instructions = \
        _('Use your standard username and password.')

    def authenticate(self, username, password):
        """Authenticate the user.

        This will authenticate the username and return the appropriate User
        object, or None.
        """
        username = username.strip()

        digest_text = '%s:%s:%s' % (username, settings.DIGEST_REALM, password)
        digest_password = hashlib.md5(digest_text).hexdigest()

        try:
            with open(settings.DIGEST_FILE_LOCATION, 'r') as passwd_file:
                for line_no, line in enumerate(passwd_file):
                    try:
                        user, realm, passwd = line.strip().split(':')

                        if user == username and passwd == digest_password:
                            return self.get_or_create_user(username, None)
                        else:
                            continue
                    except ValueError as e:
                        logging.error('Error parsing HTTP Digest password '
                                      'file at line %d: %s',
                                      line_no, e, exc_info=True)
                        break

        except IOError as e:
            logging.error('Could not open the HTTP Digest password file: %s',
                          e, exc_info=True)

        return None

    def get_or_create_user(self, username, request):
        """Get an existing user, or create one if it does not exist."""
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User(username=username, password='')
            user.is_staff = False
            user.is_superuser = False
            user.set_unusable_password()
            user.save()

        return user


class NISBackend(AuthBackend):
    """Authenticate against a user on an NIS server."""

    backend_id = 'nis'
    name = _('NIS')
    settings_form = NISSettingsForm
    login_instructions = \
        _('Use your standard NIS username and password.')

    def authenticate(self, username, password):
        """Authenticate the user.

        This will authenticate the username and return the appropriate User
        object, or None.
        """
        import crypt
        import nis

        username = username.strip()

        try:
            passwd = nis.match(username, 'passwd').split(':')
            original_crypted = passwd[1]
            new_crypted = crypt.crypt(password, original_crypted)

            if original_crypted == new_crypted:
                return self.get_or_create_user(username, None, passwd)
        except nis.error:
            # FIXME I'm not sure under what situations this would fail (maybe
            # if their NIS server is down), but it'd be nice to inform the
            # user.
            pass

        return None

    def get_or_create_user(self, username, request, passwd=None):
        """Get an existing user, or create one if it does not exist."""
        import nis

        username = username.strip()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                if not passwd:
                    passwd = nis.match(username, 'passwd').split(':')

                names = passwd[4].split(',')[0].split(' ', 1)
                first_name = names[0]
                last_name = None
                if len(names) > 1:
                    last_name = names[1]

                email = '%s@%s' % (username, settings.NIS_EMAIL_DOMAIN)

                user = User(username=username,
                            password='',
                            first_name=first_name,
                            last_name=last_name or '',
                            email=email)
                user.is_staff = False
                user.is_superuser = False
                user.set_unusable_password()
                user.save()
            except nis.error:
                pass
        return user


class LDAPBackend(AuthBackend):
    """Authentication backend for LDAP servers.

    This allows the use of LDAP servers for authenticating users in Review
    Board, and for importing individual users on-demand. It allows for a lot of
    customization in terms of how the LDAP server is queried, providing
    compatibility with most open source and commercial LDAP servers.

    The following Django settings are supported:

    ``LDAP_ANON_BIND_UID``:
        The full DN (distinguished name) of a user account with
        sufficient access to perform lookups of users and groups in the LDAP
        server. This is treated as a general or "anonymous" user for servers
        requiring authentication, and will not be otherwise imported into the
        Review Board server (unless attempting to log in with the same name).

        This can be unset if the LDAP server supports actual anonymous binds
        without a DN.

    ``LDAP_ANON_BIND_PASSWD``:
        The password used for the account specified in ``LDAP_ANON_BIND_UID``.

    ``LDAP_ANON_BIND_UID``:
        The full distinguished name of a user account with sufficient access
        to perform lookups of users and groups in the LDAP server. This can
        be unset if the LDAP server supports anonymous binds.

    ``LDAP_BASE_DN``:
        The base DN (distinguished name) used to perform LDAP searches.

    ``LDAP_EMAIL_ATTRIBUTE``:
        The attribute designating the e-mail address of a user in the
        directory. E-mail attributes are only used if this is set and if
        ``LDAP_EMAIL_DOMAIN`` is not set.

    ``LDAP_EMAIL_DOMAIN``:
        The domain name to use for e-mail addresses. If set, users imported
        from LDAP will have an e-mail address in the form of
        :samp:`{username}@{LDAP_EMAIL_DOMAIN}`. This takes priority over
        ``LDAP_EMAIL_ATTRIBUTE``.

    ``LDAP_GIVEN_NAME_ATTRIBUTE``:
        The attribute designating the given name (or first name) of a user
        in the directory. This defaults to ``givenName`` if not provided.

    ``LDAP_SURNAME_ATTRIBUTE``:
        The attribute designating the surname (or last name) of a user in the
        directory. This defaults to ``sn`` if not provided.

    ``LDAP_TLS``:
        Whether to use TLS to communicate with the LDAP server.

    ``LDAP_UID``:
        The attribute indicating a user's unique ID in the directory. This
        is used to compute a user lookup filter in the format of
        :samp:`({LDAP_UID}={username})`.

    ``LDAP_UID_MASK``:
        A mask defining a filter for looking up users. This must contain
        ``%s`` somewhere in the string, representing the username.
        For example: ``(something_special=%s)``.

    ``LDAP_URI``:
        The URI to the LDAP server to connect to for all communication.
    """

    backend_id = 'ldap'
    name = _('LDAP')
    settings_form = LDAPSettingsForm
    login_instructions = \
        _('Use your standard LDAP username and password.')

    def authenticate(self, username, password):
        """Authenticate a user.

        This will attempt to authenticate the user against the LDAP server.
        If the username and password are valid, a
        :py:class:`~django.contrib.auth.models.User` will be returned, and
        added to the database if it doesn't already exist.

        Args:
            username (unicode):
                The username used to authenticate.

            password (unicode):
                The password used to authenticate.

        Returns:
            django.contrib.auth.models.User:
            The resulting user, if authentication was successful. If
            unsuccessful, ``None`` is returned.
        """
        username = username.strip()

        if not password:
            # Don't try to bind using an empty password; the server will
            # return success, which doesn't mean we have authenticated.
            # http://tools.ietf.org/html/rfc4513#section-5.1.2
            # http://tools.ietf.org/html/rfc4513#section-6.3.1
            logging.warning('Attempted to authenticate "%s" with an empty '
                            'password against LDAP.',
                            username)
            return None

        ldapo = self._connect()

        if ldapo is None:
            return None

        if isinstance(username, six.text_type):
            username_bytes = username.encode('utf-8')
        else:
            username_bytes = username

        if isinstance(password, six.text_type):
            password = password.encode('utf-8')

        userdn = self._get_user_dn(ldapo, username)

        try:
            # Now that we have the user, attempt to bind to verify
            # authentication.
            logging.debug('Attempting to authenticate user DN "%s" '
                          '(username %s) in LDAP',
                          userdn.decode('utf-8'), username)
            ldapo.bind_s(userdn, password)

            return self.get_or_create_user(username=username_bytes,
                                           ldapo=ldapo,
                                           userdn=userdn)
        except ldap.INVALID_CREDENTIALS:
            logging.warning('Error authenticating user "%s" in LDAP: The '
                            'credentials provided were invalid',
                            username)
        except ldap.LDAPError as e:
            logging.warning('Error authenticating user "%s" in LDAP: %s',
                            username, e)
        except Exception as e:
            logging.exception('Unexpected error authenticating user "%s" '
                              'in LDAP: %s',
                              username, e)

        return None

    def get_or_create_user(self, username, request=None, ldapo=None,
                           userdn=None):
        """Return a user account, importing from LDAP if necessary.

        If the user already exists in the database, it will be returned
        directly. Otherwise, this will attempt to look up the user in LDAP
        and create a local user account representing that user.

        Args:
            username (unicode):
                The username to look up.

            request (django.http.HttpRequest, optional):
                The optional HTTP request for this operation.

            ldapo (ldap.LDAPObject, optional):
                The existing LDAP connection, if the caller has one. If not
                provided, a new connection will be created.

            userdn (unicode, optional):
                The DN for the user being looked up, if the caller knows it.
                If not provided, the DN will be looked up.

        Returns:
            django.contrib.auth.models.User:
            The resulting user, if it could be found either locally or in
            LDAP. If the user does not exist, ``None`` is returned.
        """
        username = re.sub(INVALID_USERNAME_CHAR_REGEX, '', username).lower()

        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            # The user wasn't in the database, so we'll look it up in
            # LDAP below.
            pass

        if ldap is None:
            logging.error('Attempted to look up user "%s" in LDAP, but the '
                          'python-ldap package is not installed!',
                          username)
            return None

        try:
            if ldapo is None:
                ldapo = self._connect(request=request)

                if ldapo is None:
                    return None

            if userdn is None:
                userdn = self._get_user_dn(ldapo=ldapo,
                                           username=username,
                                           request=request)

                if userdn is None:
                    return None

            # Perform a BASE search since we already know the DN of
            # the user
            search_result = ldapo.search_s(userdn, ldap.SCOPE_BASE)
            user_info = search_result[0][1]

            given_name_attr = getattr(settings, 'LDAP_GIVEN_NAME_ATTRIBUTE',
                                      'givenName')
            first_name = user_info.get(given_name_attr, [username])[0]

            surname_attr = getattr(settings, 'LDAP_SURNAME_ATTRIBUTE', 'sn')
            last_name = user_info.get(surname_attr, [''])[0]

            # If a single ldap attribute is used to hold the full name of
            # a user, split it into two parts.  Where to split was a coin
            # toss and I went with a left split for the first name and
            # dumped the remainder into the last name field.  The system
            # admin can handle the corner cases.
            try:
                if settings.LDAP_FULL_NAME_ATTRIBUTE:
                    full_name = \
                        user_info[settings.LDAP_FULL_NAME_ATTRIBUTE][0]
                    full_name = full_name.decode('utf-8')
                    first_name, last_name = full_name.split(' ', 1)
            except AttributeError:
                pass

            if settings.LDAP_EMAIL_DOMAIN:
                email = '%s@%s' % (username, settings.LDAP_EMAIL_DOMAIN)
            elif settings.LDAP_EMAIL_ATTRIBUTE:
                try:
                    email = user_info[settings.LDAP_EMAIL_ATTRIBUTE][0]
                except KeyError:
                    logging.error('LDAP: could not get e-mail address for '
                                  'user %s using attribute %s',
                                  username, settings.LDAP_EMAIL_ATTRIBUTE)
                    email = ''
            else:
                logging.warning(
                    'LDAP: e-mail for user %s is not specified',
                    username)
                email = ''

            user = User(username=username,
                        password='',
                        first_name=first_name,
                        last_name=last_name,
                        email=email)
            user.set_unusable_password()
            user.save()

            return user
        except ldap.NO_SUCH_OBJECT as e:
            logging.warning("LDAP error: %s settings.LDAP_BASE_DN: %s "
                            "User DN: %s",
                            e, settings.LDAP_BASE_DN, userdn,
                            exc_info=1)
        except ldap.LDAPError as e:
            logging.warning("LDAP error: %s", e, exc_info=1)

        return None

    def _connect(self, request=None):
        """Connect to LDAP.

        This will attempt to connect and authenticate (if needed) to the
        configured LDAP server.

        Args:
            request (django.http.HttpRequest, optional):
                The optional HTTP request used for logging context.

        Returns:
            ldap.LDAPObject:
            The resulting LDAP connection, if it could connect. If LDAP
            support isn't available, or there was an error, this will return
            ``None``.
        """
        if ldap is None:
            return None

        try:
            ldapo = ldap.initialize(settings.LDAP_URI)
            ldapo.set_option(ldap.OPT_REFERRALS, 0)
            ldapo.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

            if settings.LDAP_TLS:
                ldapo.start_tls_s()

            if settings.LDAP_ANON_BIND_UID:
                # Log in as the service account before searching.
                ldapo.simple_bind_s(settings.LDAP_ANON_BIND_UID,
                                    settings.LDAP_ANON_BIND_PASSWD)
            else:
                # Bind anonymously to the server.
                ldapo.simple_bind_s()

            return ldapo
        except ldap.INVALID_CREDENTIALS:
            if settings.LDAP_ANON_BIND_UID:
                logging.warning('Error authenticating with LDAP: The '
                                'credentials provided for "%s" were invalid.',
                                settings.LDAP_ANON_BIND_UID,
                                request=request)
            else:
                logging.warning('Error authenticating with LDAP: Anonymous '
                                'access to this server is not permitted.',
                                request=request)
        except ldap.LDAPError as e:
            logging.warning('Error authenticating with LDAP: %s',
                            e,
                            request=request)
        except Exception as e:
            logging.exception('Unexpected error occurred while authenticating '
                              'with LDAP: %s',
                              e,
                              request=request)

        return None

    def _get_user_dn(self, ldapo, username, request=None):
        """Return the DN for a given username.

        This will perform a lookup in LDAP to try to find a DN for a given
        username, which can be used in subsequent lookups and for
        authentication.

        Args:
            ldapo (ldap.LDAPObject):
                The LDAP connection.

            username (unicode):
                The username to look up in the directory.

            request (django.http.HttpRequest, optional):
                The optional HTTP request used for logging context.

        Returns:
            unicode:
            The DN for the username, if found. If not found, this will return
            ``None``.
        """
        assert ldapo is not None

        try:
            # If the UID mask has been explicitly set, use it instead of
            # computing a search filter.
            if settings.LDAP_UID_MASK:
                uidfilter = settings.LDAP_UID_MASK % username
            else:
                uidfilter = '(%(userattr)s=%(username)s)' % {
                    'userattr': settings.LDAP_UID,
                    'username': username,
                }

            # Search for the user with the given base DN and uid. If the user
            # is found, a fully qualified DN is returned.
            search = ldapo.search_s(settings.LDAP_BASE_DN,
                                    ldap.SCOPE_SUBTREE,
                                    uidfilter)

            if search:
                return search[0][0]

            logging.warning('LDAP error: The specified object does '
                            'not exist in the Directory: %s',
                            username,
                            request=request)
        except ldap.LDAPError as e:
            logging.warning('Error authenticating user "%s" in LDAP: %s',
                            username, e,
                            request=request)
        except Exception as e:
            logging.exception('Unexpected error authenticating user "%s" '
                              'in LDAP: %s',
                              username, e,
                              request=request)

        return None


class ActiveDirectoryBackend(AuthBackend):
    """Authenticate a user against an Active Directory server."""

    backend_id = 'ad'
    name = _('Active Directory')
    settings_form = ActiveDirectorySettingsForm
    login_instructions = \
        _('Use your standard Active Directory username and password.')

    def get_domain_name(self):
        """Return the current AD domain name."""
        return six.text_type(settings.AD_DOMAIN_NAME)

    def get_ldap_search_root(self, userdomain=None):
        """Return the search root(s) for users in the LDAP server."""
        if getattr(settings, "AD_SEARCH_ROOT", None):
            root = [settings.AD_SEARCH_ROOT]
        else:
            if userdomain is None:
                userdomain = self.get_domain_name()

            root = ['dc=%s' % x for x in userdomain.split('.')]

            if settings.AD_OU_NAME:
                root = ['ou=%s' % settings.AD_OU_NAME] + root

        return ','.join(root)

    def search_ad(self, con, filterstr, userdomain=None):
        """Run a search on the given LDAP server."""
        search_root = self.get_ldap_search_root(userdomain)
        logging.debug('Search root ' + search_root)
        return con.search_s(search_root, scope=ldap.SCOPE_SUBTREE,
                            filterstr=filterstr)

    def find_domain_controllers_from_dns(self, userdomain=None):
        """Find and return the active domain controllers using DNS."""
        import DNS
        DNS.Base.DiscoverNameServers()
        q = '_ldap._tcp.%s' % (userdomain or self.get_domain_name())
        req = DNS.Base.DnsRequest(q, qtype=DNS.Type.SRV).req()
        return [x['data'][-2:] for x in req.answers]

    def can_recurse(self, depth):
        """Return whether the given recursion depth is too big."""
        return (settings.AD_RECURSION_DEPTH == -1 or
                depth <= settings.AD_RECURSION_DEPTH)

    def get_member_of(self, con, search_results, seen=None, depth=0):
        """Get the LDAP groups for the given users.

        This iterates over the users specified in ``search_results`` and
        returns a set of groups of which those users are members.
        """
        depth += 1
        if seen is None:
            seen = set()

        for name, data in search_results:
            if name is None:
                continue

            member_of = data.get('memberOf', [])
            new_groups = [x.split(b',')[0].split(b'=')[1] for x in member_of]

            old_seen = seen.copy()
            seen.update(new_groups)

            # collect groups recursively
            if self.can_recurse(depth):
                for group in new_groups:
                    if group in old_seen:
                        continue

                    # Search for groups with the specified CN. Use the CN
                    # rather than The sAMAccountName so that behavior is
                    # correct when the values differ (e.g. if a
                    # "pre-Windows 2000" group name is set in AD)
                    group_data = self.search_ad(
                        con,
                        filter_format('(&(objectClass=group)(cn=%s))',
                                      (group,)))
                    seen.update(self.get_member_of(con, group_data,
                                                   seen=seen, depth=depth))
            else:
                logging.warning('ActiveDirectory recursive group check '
                                'reached maximum recursion depth.')

        return seen

    def get_ldap_connections(self, userdomain=None):
        """Get a set of connections to LDAP servers.

        This returns an iterable of connections to the LDAP servers specified
        in AD_DOMAIN_CONTROLLER.
        """
        if settings.AD_FIND_DC_FROM_DNS:
            dcs = self.find_domain_controllers_from_dns(userdomain)
        else:
            dcs = []

            for dc_entry in settings.AD_DOMAIN_CONTROLLER.split():
                if ':' in dc_entry:
                    host, port = dc_entry.split(':')
                else:
                    host = dc_entry
                    port = '389'

                dcs.append([port, host])

        for dc in dcs:
            port, host = dc
            ldap_uri = 'ldap://%s:%s' % (host, port)
            con = ldap.initialize(ldap_uri)

            if settings.AD_USE_TLS:
                try:
                    con.start_tls_s()
                except ldap.UNAVAILABLE:
                    logging.warning('Active Directory: Domain controller '
                                    '%s:%d for domain %s unavailable',
                                    host, int(port), userdomain)
                    continue
                except ldap.CONNECT_ERROR:
                    logging.warning("Active Directory: Could not connect "
                                    "to domain controller %s:%d for domain "
                                    "%s, possibly the certificate wasn't "
                                    "verifiable",
                                    host, int(port), userdomain)
                    continue

            con.set_option(ldap.OPT_REFERRALS, 0)
            yield con

    def authenticate(self, username, password):
        """Authenticate the user.

        This will authenticate the username and return the appropriate User
        object, or None.
        """
        username = username.strip()

        user_subdomain = ''

        if '@' in username:
            username, user_subdomain = username.split('@', 1)
        elif '\\' in username:
            user_subdomain, username = username.split('\\', 1)

        userdomain = self.get_domain_name()

        if user_subdomain:
            userdomain = "%s.%s" % (user_subdomain, userdomain)

        connections = self.get_ldap_connections(userdomain)

        required_group = settings.AD_GROUP_NAME
        if isinstance(required_group, six.text_type):
            required_group = required_group.encode('utf-8')

        if isinstance(username, six.text_type):
            username_bytes = username.encode('utf-8')
        else:
            username_bytes = username

        if isinstance(user_subdomain, six.text_type):
            user_subdomain = user_subdomain.encode('utf-8')

        if isinstance(password, six.text_type):
            password = password.encode('utf-8')

        for con in connections:
            try:
                bind_username = b'%s@%s' % (username_bytes, userdomain)
                logging.debug("User %s is trying to log in via AD",
                              bind_username.decode('utf-8'))
                con.simple_bind_s(bind_username, password)
                user_data = self.search_ad(
                    con,
                    filter_format('(&(objectClass=user)(sAMAccountName=%s))',
                                  (username_bytes,)),
                    userdomain)

                if not user_data:
                    return None

                if required_group:
                    try:
                        group_names = self.get_member_of(con, user_data)
                    except Exception as e:
                        logging.error("Active Directory error: failed getting"
                                      "groups for user '%s': %s",
                                      username, e, exc_info=1)
                        return None

                    if required_group not in group_names:
                        logging.warning("Active Directory: User %s is not in "
                                        "required group %s",
                                        username, required_group)
                        return None

                return self.get_or_create_user(username, None, user_data)
            except ldap.SERVER_DOWN:
                logging.warning('Active Directory: Domain controller is down')
                continue
            except ldap.INVALID_CREDENTIALS:
                logging.warning('Active Directory: Failed login for user %s',
                                username)
                return None

        logging.error('Active Directory error: Could not contact any domain '
                      'controller servers')
        return None

    def get_or_create_user(self, username, request, ad_user_data):
        """Get an existing user, or create one if it does not exist."""
        username = re.sub(INVALID_USERNAME_CHAR_REGEX, '', username).lower()

        try:
            user = User.objects.get(username=username)
            return user
        except User.DoesNotExist:
            try:
                user_info = ad_user_data[0][1]

                first_name = user_info.get('givenName', [username])[0]
                last_name = user_info.get('sn', [""])[0]
                email = user_info.get(
                    'mail',
                    ['%s@%s' % (username, settings.AD_DOMAIN_NAME)])[0]

                user = User(username=username,
                            password='',
                            first_name=first_name,
                            last_name=last_name,
                            email=email)
                user.is_staff = False
                user.is_superuser = False
                user.set_unusable_password()
                user.save()
                return user
            except:
                return None


class X509Backend(AuthBackend):
    """Authenticate a user from a X.509 client certificate.

    The certificate is passed in by the browser. This backend relies on the
    X509AuthMiddleware to extract a username field from the client certificate.
    """

    backend_id = 'x509'
    name = _('X.509 Public Key')
    settings_form = X509SettingsForm
    supports_change_password = True

    def authenticate(self, x509_field=""):
        """Authenticate the user.

        This will extract the username from the provided certificate and return
        the appropriate User object.
        """
        username = self.clean_username(x509_field)
        return self.get_or_create_user(username, None)

    def clean_username(self, username):
        """Validate the 'username' field.

        This checks to make sure that the contents of the username field are
        valid for X509 authentication.
        """
        username = username.strip()

        if settings.X509_USERNAME_REGEX:
            try:
                m = re.match(settings.X509_USERNAME_REGEX, username)
                if m:
                    username = m.group(1)
                else:
                    logging.warning("X509Backend: username '%s' didn't match "
                                    "regex.", username)
            except sre_constants.error as e:
                logging.error("X509Backend: Invalid regex specified: %s",
                              e, exc_info=1)

        return username

    def get_or_create_user(self, username, request):
        """Get an existing user, or create one if it does not exist."""
        user = None
        username = username.strip()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # TODO Add the ability to get the first and last names in a
            #      configurable manner; not all X.509 certificates will have
            #      the same format.
            if getattr(settings, 'X509_AUTOCREATE_USERS', False):
                user = User(username=username, password='')
                user.is_staff = False
                user.is_superuser = False
                user.set_unusable_password()
                user.save()

        return user


def _populate_defaults():
    """Populate the default list of authentication backends."""
    global _populated

    if not _populated:
        _populated = True

        # Always ensure that the standard built-in auth backend is included.
        register_auth_backend(StandardAuthBackend)

        entrypoints = \
            pkg_resources.iter_entry_points('reviewboard.auth_backends')

        for entry in entrypoints:
            try:
                cls = entry.load()

                # All backends should include an ID, but we need to handle
                # legacy modules.
                if not cls.backend_id:
                    logging.warning('The authentication backend %r did '
                                    'not provide a backend_id attribute. '
                                    'Setting it to the entrypoint name "%s".',
                                    cls, entry.name)
                    cls.backend_id = entry.name

                register_auth_backend(cls)
            except Exception as e:
                logging.error('Error loading authentication backend %s: %s',
                              entry.name, e, exc_info=1)


def get_registered_auth_backends():
    """Return all registered Review Board authentication backends.

    This will return all backends provided both by Review Board and by
    third parties that have properly registered with the
    "reviewboard.auth_backends" entry point.
    """
    _populate_defaults()

    return six.itervalues(_registered_auth_backends)


def get_registered_auth_backend(backend_id):
    """Return the authentication backends with the specified ID.

    If the authentication backend could not be found, this will return None.
    """
    _populate_defaults()

    try:
        return _registered_auth_backends[backend_id]
    except KeyError:
        return None


def register_auth_backend(backend_cls):
    """Register an authentication backend.

    This backend will appear in the list of available backends.

    The backend class must have a backend_id attribute set, and can only
    be registerd once. A KeyError will be thrown if attempting to register
    a second time.
    """
    _populate_defaults()

    backend_id = backend_cls.backend_id

    if not backend_id:
        raise KeyError('The backend_id attribute must be set on %r'
                       % backend_cls)

    if backend_id in _registered_auth_backends:
        raise KeyError('"%s" is already a registered auth backend'
                       % backend_id)

    _registered_auth_backends[backend_id] = backend_cls


def unregister_auth_backend(backend_cls):
    """Unregister a previously registered authentication backend."""
    _populate_defaults()

    backend_id = backend_cls.backend_id

    if backend_id not in _registered_auth_backends:
        logging.error('Failed to unregister unknown authentication '
                      'backend "%s".',
                      backend_id)
        raise KeyError('"%s" is not a registered authentication backend'
                       % backend_id)

    del _registered_auth_backends[backend_id]


def get_enabled_auth_backends():
    """Get all authentication backends being used by Review Board.

    The returned list contains every authentication backend that Review Board
    will try, in order.
    """
    global _enabled_auth_backends
    global _auth_backend_setting

    if (not _enabled_auth_backends or
        _auth_backend_setting != settings.AUTHENTICATION_BACKENDS):
        _enabled_auth_backends = []

        for backend in get_backends():
            if not isinstance(backend, AuthBackend):
                warn('Authentication backends should inherit from '
                     'reviewboard.accounts.backends.AuthBackend. Please '
                     'update %s.' % backend.__class__)

                for field, default in (('name', None),
                                       ('supports_registration', False),
                                       ('supports_change_name', False),
                                       ('supports_change_email', False),
                                       ('supports_change_password', False)):
                    if not hasattr(backend, field):
                        warn("Authentication backends should define a '%s' "
                             "attribute. Please define it in %s or inherit "
                             "from AuthBackend." % (field, backend.__class__))
                        setattr(backend, field, False)

            _enabled_auth_backends.append(backend)

        _auth_backend_setting = settings.AUTHENTICATION_BACKENDS

    return _enabled_auth_backends


def set_enabled_auth_backend(backend_id):
    """Set the authentication backend to be used."""
    siteconfig = SiteConfiguration.objects.get_current()
    siteconfig.set('auth_backend', backend_id)
