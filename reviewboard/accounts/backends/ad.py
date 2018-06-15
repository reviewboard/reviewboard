"""Active Directory authentication backend."""

from __future__ import unicode_literals

import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import six
from django.utils.translation import ugettext_lazy as _

try:
    import ldap
    from ldap.filter import filter_format
except ImportError:
    ldap = None

from reviewboard.accounts.backends.base import BaseAuthBackend
from reviewboard.accounts.forms.auth import ActiveDirectorySettingsForm


class ActiveDirectoryBackend(BaseAuthBackend):
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

        Yields:
            tuple of (unicode, ldap.LDAP_OBJECT):
            The connections to the configured LDAP servers.
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
            connection = ldap.initialize(ldap_uri)

            if settings.AD_USE_TLS:
                try:
                    connection.start_tls_s()
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

            connection.set_option(ldap.OPT_REFERRALS, 0)
            yield ldap_uri, connection

    def authenticate(self, username, password, **kwargs):
        """Authenticate the user.

        Args:
            username (unicode):
                The entered username.

            password (unicode):
                The entered password.

            **kwargs (dict, unused):
                Additional keyword arguments passed by the caller.

        Returns:
            django.contrib.auth.models.User:
            The authenticated user. If authentication fails, returns None.
        """
        username = username.strip()

        if ldap is None:
            logging.error('Attempted to authenticate user "%s" in LDAP, but '
                          'the python-ldap package is not installed!',
                          username)
            return None

        user_subdomain = ''

        if '@' in username:
            username, user_subdomain = username.split('@', 1)
        elif '\\' in username:
            user_subdomain, username = username.split('\\', 1)

        userdomain = self.get_domain_name()

        if user_subdomain:
            userdomain = "%s.%s" % (user_subdomain, userdomain)

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

        for uri, connection in self.get_ldap_connections(userdomain):
            try:
                bind_username = b'%s@%s' % (username_bytes, userdomain)
                logging.debug("User %s is trying to log in via AD",
                              bind_username.decode('utf-8'))
                connection.simple_bind_s(bind_username, password)
                user_data = self.search_ad(
                    connection,
                    filter_format('(&(objectClass=user)(sAMAccountName=%s))',
                                  (username_bytes,)),
                    userdomain)

                if not user_data:
                    return None

                if required_group:
                    try:
                        group_names = self.get_member_of(connection, user_data)
                    except Exception as e:
                        logging.error('Active Directory error: failed getting '
                                      'groups for user "%s" from controller '
                                      '%s: %s',
                                      username, uri, e, exc_info=1)
                        return None

                    if required_group not in group_names:
                        logging.warning('Active Directory: User %s is not in '
                                        'required group %s on controller %s',
                                        username, required_group, uri)
                        return None

                return self.get_or_create_user(username, None, user_data)
            except ldap.SERVER_DOWN:
                logging.warning('Active Directory: Domain controller %s is '
                                'down',
                                uri)
                continue
            except ldap.INVALID_CREDENTIALS:
                logging.warning('Active Directory: Failed login for user %s '
                                'on controller %s',
                                username, uri)
                return None

        logging.error('Active Directory error: Could not contact any domain '
                      'controller servers')
        return None

    def get_or_create_user(self, username, request, ad_user_data=None):
        """Get an existing user, or create one if it does not exist."""
        username = self.INVALID_USERNAME_CHAR_REGEX.sub('', username).lower()

        try:
            user = User.objects.get(username=username)
            return user
        except User.DoesNotExist:
            if ad_user_data is None:
                return None

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
