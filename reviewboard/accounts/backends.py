import logging
import pkg_resources
import re
import sre_constants
import sys
from warnings import warn

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.contrib.auth import get_backends
from django.contrib.auth import hashers
from django.utils.translation import ugettext as _
from djblets.util.misc import get_object_or_none

from reviewboard.accounts.forms import ActiveDirectorySettingsForm, \
                                       LDAPSettingsForm, \
                                       NISSettingsForm, \
                                       StandardAuthSettingsForm, \
                                       X509SettingsForm


_auth_backends = []
_auth_backend_setting = None


class AuthBackend(object):
    """The base class for Review Board authentication backends."""
    name = None
    settings_form = None
    supports_anonymous_user = True
    supports_object_permissions = True
    supports_registration = False
    supports_change_name = False
    supports_change_email = False
    supports_change_password = False

    def authenticate(self, username, password):
        raise NotImplementedError

    def get_or_create_user(self, username, request):
        raise NotImplementedError

    def get_user(self, user_id):
        return get_object_or_none(User, pk=user_id)

    def update_password(self, user, password):
        """Updates the user's password on the backend.

        Authentication backends can override this to update the password
        on the backend. This will only be called if
        :py:attr:`supports_change_password` is ``True``.

        By default, this will raise NotImplementedError.
        """
        raise NotImplementedError

    def update_name(self, user):
        """Updates the user's name on the backend.

        The first name and last name will already be stored in the provided
        ``user`` object.

        Authentication backends can override this to update the name
        on the backend based on the values in ``user``. This will only be
        called if :py:attr:`supports_change_name` is ``True``.

        By default, this will do nothing.
        """
        pass

    def update_email(self, user):
        """Updates the user's e-mail address on the backend.

        The e-mail address will already be stored in the provided
        ``user`` object.

        Authentication backends can override this to update the e-mail
        address on the backend based on the values in ``user``. This will only
        be called if :py:attr:`supports_change_email` is ``True``.

        By default, this will do nothing.
        """
        pass


class StandardAuthBackend(AuthBackend, ModelBackend):
    name = _('Standard Registration')
    settings_form = StandardAuthSettingsForm
    supports_registration = True
    supports_change_name = True
    supports_change_email = True
    supports_change_password = True

    def authenticate(self, username, password):
        return ModelBackend.authenticate(self, username, password)

    def get_or_create_user(self, username, request):
        return ModelBackend.get_or_create_user(self, username, request)

    def update_password(self, user, password):
        user.password = hashers.make_password(password)

class NISBackend(AuthBackend):
    """Authenticate against a user on an NIS server."""
    name = _('NIS')
    settings_form = NISSettingsForm

    def authenticate(self, username, password):
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
            # FIXME I'm not sure under what situations this would fail (maybe if
            # their NIS server is down), but it'd be nice to inform the user.
            pass

        return None

    def get_or_create_user(self, username, request, passwd=None):
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

                email = u'%s@%s' % (username, settings.NIS_EMAIL_DOMAIN)

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
    """Authenticate against a user on an LDAP server."""
    name = _('LDAP')
    settings_form = LDAPSettingsForm

    def authenticate(self, username, password):
        username = username.strip()
        uid = settings.LDAP_UID_MASK % username

        if len(password) == 0:
            # Don't try to bind using an empty password; the server will
            # return success, which doesn't mean we have authenticated.
            # http://tools.ietf.org/html/rfc4513#section-5.1.2
            # http://tools.ietf.org/html/rfc4513#section-6.3.1
            logging.warning("Empty password for: %s" % uid)
            return None

        try:
            import ldap
            ldapo = ldap.initialize(settings.LDAP_URI)
            ldapo.set_option(ldap.OPT_REFERRALS, 0)
            ldapo.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            if settings.LDAP_TLS:
                ldapo.start_tls_s()

            if settings.LDAP_ANON_BIND_UID:
                # Log in as the anonymous user before searching.
                ldapo.simple_bind_s(settings.LDAP_ANON_BIND_UID,
                                    settings.LDAP_ANON_BIND_PASSWD)
                search = ldapo.search_s(settings.LDAP_BASE_DN, ldap.SCOPE_SUBTREE,
                                        uid)
                if not search:
                    # No such a user, return early, no need for bind attempts
                    logging.warning("LDAP error: The specified object does not "
                                    "exist in the Directory: %s" %
                                    uid)
                    return None
                else:
                    # Having found the user anonymously, attempt bind with the password
                    ldapo.bind_s(search[0][0], password)

            else :
                # Bind anonymously to the server, then search for the user with
                # the given base DN and uid. If the user is found, a fully
                # qualified DN is returned. Authentication is then done with
                # bind using this fully qualified DN.
                ldapo.simple_bind_s()
                search = ldapo.search_s(settings.LDAP_BASE_DN,
                                        ldap.SCOPE_SUBTREE,
                                        uid)
                userbinding = search[0][0]
                ldapo.bind_s(userbinding, password)

            return self.get_or_create_user(username, None, ldapo)

        except ImportError:
            pass
        except ldap.INVALID_CREDENTIALS:
            logging.warning("LDAP error: The specified object does not "
                            "exist in the Directory or provided invalid credentials: %s" %
                            uid)
        except ldap.LDAPError, e:
            logging.warning("LDAP error: %s" % e)
        except:
            # Fallback exception catch because
            # django.contrib.auth.authenticate() (our caller) catches only
            # TypeErrors
            logging.warning("An error while LDAP-authenticating: %r" %
                            sys.exc_info()[1])

        return None

    def get_or_create_user(self, username, request, ldapo):
        username = username.strip()

        try:
            user = User.objects.get(username=username)
            return user
        except User.DoesNotExist:
            try:
                import ldap
                search_result = ldapo.search_s(settings.LDAP_BASE_DN,
                                               ldap.SCOPE_SUBTREE,
                                               "(%s)" % settings.LDAP_UID_MASK % username)
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
                        full_name = user_info[settings.LDAP_FULL_NAME_ATTRIBUTE][0]
                        first_name, last_name = full_name.split(' ', 1)
                except AttributeError:
                    pass

                if settings.LDAP_EMAIL_DOMAIN:
                    email = u'%s@%s' % (username, settings.LDAP_EMAIL_DOMAIN)
                elif settings.LDAP_EMAIL_ATTRIBUTE:
                    email = user_info[settings.LDAP_EMAIL_ATTRIBUTE][0]
                else:
                    logging.warning("LDAP: email for user %s is not specified",
                                    username)
                    email = ''

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
            except ImportError:
                pass
            except ldap.INVALID_CREDENTIALS:
                # FIXME I'd really like to warn the user that their
                # ANON_BIND_UID and ANON_BIND_PASSWD are wrong, but I don't
                # know how
                pass
            except ldap.NO_SUCH_OBJECT, e:
                logging.warning("LDAP error: %s settings.LDAP_BASE_DN: %s "
                                "settings.LDAP_UID_MASK: %s" %
                                (e, settings.LDAP_BASE_DN,
                                 settings.LDAP_UID_MASK % username))
            except ldap.LDAPError, e:
                logging.warning("LDAP error: %s" % e)

        return None


class ActiveDirectoryBackend(AuthBackend):
    """Authenticate a user against an Active Directory server."""
    name = _('Active Directory')
    settings_form = ActiveDirectorySettingsForm

    def get_domain_name(self):
        return str(settings.AD_DOMAIN_NAME)

    def get_ldap_search_root(self, userdomain=None):
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
        import ldap
        search_root = self.get_ldap_search_root(userdomain)
        logging.debug('Search root ' + search_root)
        return con.search_s(search_root, scope=ldap.SCOPE_SUBTREE, filterstr=filterstr)

    def find_domain_controllers_from_dns(self, userdomain=None):
        import DNS
        DNS.Base.DiscoverNameServers()
        q = '_ldap._tcp.%s' % (userdomain or self.get_domain_name())
        req = DNS.Base.DnsRequest(q, qtype = 'SRV').req()
        return [x['data'][-2:] for x in req.answers]

    def can_recurse(self, depth):
        return (settings.AD_RECURSION_DEPTH == -1 or
                        depth <= settings.AD_RECURSION_DEPTH)

    def get_member_of(self, con, search_results, seen=None, depth=0):
        depth += 1
        if seen is None:
            seen = set()

        for name, data in search_results:
            if name is None:
                continue
            member_of = data.get('memberOf', [])
            new_groups = [x.split(',')[0].split('=')[1] for x in member_of]
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
                        con, '(&(objectClass=group)(cn=%s))' % group)
                    seen.update(self.get_member_of(con, group_data,
                                                   seen=seen, depth=depth))
            else:
                logging.warning('ActiveDirectory recursive group check '
                                'reached maximum recursion depth.')

        return seen

    def get_ldap_connections(self, userdomain=None):
        import ldap
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
            con = ldap.open(host, port=int(port))
            if settings.AD_USE_TLS:
                con.start_tls_s()
            con.set_option(ldap.OPT_REFERRALS, 0)
            yield con

    def authenticate(self, username, password):
        import ldap

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

        for con in connections:
            try:
                bind_username = '%s@%s' % (username, userdomain)
                logging.debug("User %s is trying to log in "
                              "via AD" % bind_username)
                con.simple_bind_s(bind_username, password)
                user_data = self.search_ad(
                    con,
                    '(&(objectClass=user)(sAMAccountName=%s))' % username,
                    userdomain)

                if not user_data:
                    return None

                if required_group:
                    try:
                        group_names = self.get_member_of(con, user_data)
                    except Exception, e:
                        logging.error("Active Directory error: failed getting"
                                      "groups for user '%s': %s" % (username, e))
                        return None

                    if required_group not in group_names:
                        logging.warning("Active Directory: User %s is not in required group %s" % (username, required_group))
                        return None

                return self.get_or_create_user(username, None, user_data)
            except ldap.SERVER_DOWN:
                logging.warning('Active Directory: Domain controller is down')
                continue
            except ldap.INVALID_CREDENTIALS:
                logging.warning('Active Directory: Failed login for user %s' % username)
                return None

        logging.error('Active Directory error: Could not contact any domain controller servers')
        return None

    def get_or_create_user(self, username, request, ad_user_data):
        username = username.strip()

        try:
            user = User.objects.get(username=username)
            return user
        except User.DoesNotExist:
            try:
                user_info = ad_user_data[0][1]

                first_name = user_info.get('givenName', [username])[0]
                last_name = user_info.get('sn', [""])[0]
                email = user_info.get('mail',
                    [u'%s@%s' % (username, settings.AD_DOMAIN_NAME)])[0]

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
    """
    Authenticate a user from a X.509 client certificate passed in by the
    browser. This backend relies on the X509AuthMiddleware to extract a
    username field from the client certificate.
    """
    name = _('X.509 Public Key')
    settings_form = X509SettingsForm
    supports_change_password = True

    def authenticate(self, x509_field=""):
        username = self.clean_username(x509_field)
        return self.get_or_create_user(username, None)

    def clean_username(self, username):
        username = username.strip()

        if settings.X509_USERNAME_REGEX:
            try:
                m = re.match(settings.X509_USERNAME_REGEX, username)
                if m:
                    username = m.group(1)
                else:
                    logging.warning("X509Backend: username '%s' didn't match "
                                    "regex." % username)
            except sre_constants.error, e:
                logging.error("X509Backend: Invalid regex specified: %s" % e)

        return username

    def get_or_create_user(self, username, request):
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


def get_registered_auth_backends():
    """Returns all registered Review Board authentication backends.

    This will return all backends provided both by Review Board and by
    third parties that have properly registered with the
    "reviewboard.auth_backends" entry point.
    """
    # Always ensure that the standard built-in auth backend is included.
    yield "builtin", StandardAuthBackend

    for entry in pkg_resources.iter_entry_points('reviewboard.auth_backends'):
        try:
            yield entry.name, entry.load()
        except Exception, e:
            logging.error('Error loading authentication backend %s: %s'
                          % (entry.name, e),
                          exc_info=1)


def get_auth_backends():
    """Returns all authentication backends being used by Review Board.

    The returned list contains every authentication backend that Review Board
    will try, in order.
    """
    global _auth_backends
    global _auth_backend_setting

    if (not _auth_backends or
        _auth_backend_setting != settings.AUTHENTICATION_BACKENDS):
        _auth_backends = []
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

            _auth_backends.append(backend)

        _auth_backend_setting = settings.AUTHENTICATION_BACKENDS

    return _auth_backends
