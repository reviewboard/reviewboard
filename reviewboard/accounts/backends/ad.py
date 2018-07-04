"""Active Directory authentication backend."""

from __future__ import absolute_import, unicode_literals

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


logger = logging.getLogger(__name__)


class ActiveDirectoryBackend(BaseAuthBackend):
    """Authenticate a user against an Active Directory server.

    This is controlled by the following Django settings:

    .. setting:: AD_DOMAIN_CONTROLLER

    ``AD_DOMAIN_CONTROLLER``:
        The domain controller (or controllers) to connect to. This must be
        a string, but multiple controllers can be specified by separating
        each with a space.

        This is ``auth_ad_domain_controller`` in the site configuration.


    .. setting:: AD_DOMAIN_NAME

    ``AD_DOMAIN_NAME``:
       The Active Directory domain name. This must be a string.

       This is ``auth_ad_domain_name`` in the site configuration.


    .. setting:: AD_FIND_DC_FROM_DNS

    ``AD_FIND_DC_FROM_DNS``:
        Whether domain controllers should be found by using DNS. This must be
        a boolean.

        This is ``auth_ad_find_dc_from_dns`` in the site configuration.


    .. setting:: AD_GROUP_NAME

    ``AD_GROUP_NAME``:
        The optional name of the group to restrict available users to. This
        must be a string.

        This is ``auth_ad_group_name`` in the site configuration.


    .. setting:: AD_OU_NAME

    ``AD_OU_NAME``:
       The optional name of the Organizational Unit to restrict available users
       to. This must be a string.

       This is ``auth_ad_ou_name`` in the site configuration.


    .. setting:: AD_RECURSION_DEPTH

    ``AD_RECURSION_DEPTH``:
        Maximum depth to recurse when checking group membership. A value of
        -1 means infinite depth is supported. A value of 0 turns off recursive
        checks.

        This is ``auth_ad_recursion_depth`` in the site configuration.


    .. setting:: AD_SEARCH_ROOT

    ``AD_SEARCH_ROOT``:
        A custom search root for entries in Active Directory. This must be a
        string.

        This is ``auth_ad_search_root`` in the site configuration.


    .. setting:: AD_USE_TLS

    ``AD_USE_TLS``:
        Whether to use TLS when communicating over LDAP. This must be a
        boolean.

        This is ``auth_ad_use_tls`` in the site configuration.
    """

    backend_id = 'ad'
    name = _('Active Directory')
    settings_form = ActiveDirectorySettingsForm
    login_instructions = \
        _('Use your standard Active Directory username and password.')

    def get_domain_name(self):
        """Return the current Active Directory domain name.

        This returns the domain name as set in :setting:`AD_DOMAIN_NAME`.

        Returns:
            unicode:
            The Active Directory domain name.
        """
        return six.text_type(settings.AD_DOMAIN_NAME)

    def get_ldap_search_root(self, userdomain=None):
        """Return the search root(s) for users in the LDAP server.

        If :setting:`AD_SEARCH_ROOT` is set, then it will be used. Otherwise,
        a suitable search root will be computed based on the domain name
        (either the provided ``user_domain`` or the result of
        :py:meth:`get_domain_name`) and any configured Organizational Unit
        name (:setting:`AD_OU_NAME`).

        Args:
            userdomain (unicode, optional):
                An explicit Active Directory domain to use for the search root.

        Returns:
            unicode:
            The search root used to locate users.
        """
        if getattr(settings, 'AD_SEARCH_ROOT', None):
            root = [settings.AD_SEARCH_ROOT]
        else:
            if userdomain is None:
                userdomain = self.get_domain_name()

            root = ['dc=%s' % x for x in userdomain.split('.')]

            if settings.AD_OU_NAME:
                root = ['ou=%s' % settings.AD_OU_NAME] + root

        return ','.join(root)

    def search_ad(self, con, filterstr, userdomain=None):
        """Search the given LDAP server based on the provided filter.

        Args:
            con (ldap.LDAPObject):
                The LDAP connection to search.

            filterstr (unicode):
                The filter string used to locate objects in Active Directory.

            userdomain (unicode, optional):
                An explicit domain used for the search. If not provided,
                :py:meth:`get_domain_name` will be used.

        Returns:
            list of tuple:
            The list of search results. Each tuple in the list is in the form
            of ``(dn, attrs)``, where ``dn`` is the Distinguished Name of the
            entry and ``attrs`` is a dictionary of attributes for that entry.
        """
        search_root = self.get_ldap_search_root(userdomain)
        logger.debug('Search root "%s" for filter "%s"',
                     search_root, filterstr)
        return con.search_s(search_root, scope=ldap.SCOPE_SUBTREE,
                            filterstr=filterstr)

    def find_domain_controllers_from_dns(self, userdomain=None):
        """Find and return the active domain controllers using DNS.

        Args:
            userdomain (unicode, optional):
                An explicit domain used for the search. If not provided,
                :py:meth:`get_domain_name` will be used.

        Returns:
            list of unicode:
            The list of domain controllers.
        """
        import DNS
        DNS.Base.DiscoverNameServers()

        req = DNS.Base.DnsRequest(
            '_ldap._tcp.%s' % (userdomain or self.get_domain_name()),
            qtype=DNS.Type.SRV).req()

        return [answer['data'][-2:] for answer in req.answers]

    def can_recurse(self, depth):
        """Return whether the given recursion depth is too deep.

        Args:
            depth (int):
                The current depth to check.

        Returns:
            bool:
            ``True`` if the provided depth can be recursed into. ``False``
            if it's too deep.
        """
        return (settings.AD_RECURSION_DEPTH == -1 or
                depth <= settings.AD_RECURSION_DEPTH)

    def get_member_of(self, con, search_results, seen=None, depth=0):
        """Return the LDAP groups for the given users.

        This iterates over the users specified in ``search_results`` and
        returns a set of groups of which those users are members.

        Args:
            con (ldap.LDAPObject):
                The LDAP connection used for checking groups memberships.

            search_results (list of tuple):
                The list of search results to check. This expects a result
                from :py:meth:`search_ad`.

            seen (set, optional):
                The set of groups that have already been seen when recursing.
                This is used internally by this method and should not be
                provided by the caller.

            depth (int, optional):
                The current recursion depth. This is used internally by this
                method and should not be provided by the caller.

        Returns:
            set:
            The group memberships found for the given users.
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

            # Collect groups recursively.
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
                logger.warning('Recursive group check reached maximum '
                               'recursion depth (%s)',
                               depth)

        return seen

    def get_ldap_connections(self, userdomain=None):
        """Return all LDAP connections used for Active Directory.

        This returns an iterable of connections to the LDAP servers specified
        in :setting:`AD_DOMAIN_CONTROLLER`.

        Yields:
            tuple of (unicode, ldap.LDAPObject):
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
                    logger.warning('Domain controller "%s:%d" for domain "%s" '
                                   'unavailable',
                                   host, int(port), userdomain)
                    continue
                except ldap.CONNECT_ERROR:
                    logger.warning('Could not connect to domain controller '
                                   '"%s:%d" for domain "%s". The certificate '
                                   'may not be verifiable.',
                                   host, int(port), userdomain)
                    continue

            connection.set_option(ldap.OPT_REFERRALS, 0)
            yield ldap_uri, connection

    def authenticate(self, username, password, **kwargs):
        """Authenticate a user against Active Directory.

        Args:
            username (unicode):
                The username to authenticate.

            password (unicode):
                The user's password.

            **kwargs (dict, unused):
                Additional keyword arguments passed by the caller.

        Returns:
            django.contrib.auth.models.User:
            The authenticated user. If authentication fails for any reason,
            this will return ``None``.
        """
        username = username.strip()

        if ldap is None:
            logger.error('Attempted to authenticate user "%s" in LDAP, but '
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
            userdomain = '%s.%s' % (user_subdomain, userdomain)

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
                        logger.error('Unable to retrieve groups for user '
                                     '"%s" from controller "%s": %s',
                                     username, uri, e, exc_info=1)
                        return None

                    if required_group not in group_names:
                        logger.warning('User %s is not in required group "%s" '
                                       'on controller "%s"',
                                       username, required_group, uri)
                        return None

                return self.get_or_create_user(username=username,
                                               request=None,
                                               ad_user_data=user_data)
            except ldap.SERVER_DOWN:
                logger.warning('domain controller "%s" is down', uri)
                continue
            except ldap.INVALID_CREDENTIALS:
                logger.warning('Failed login for user "%s" on controller "%s"',
                               username, uri)
                return None

        logger.error('Could not contact any domain controller servers')

        return None

    def get_or_create_user(self, username, request=None, ad_user_data=None):
        """Return an existing user or create one if it doesn't exist.

        This does not authenticate the user.

        If the user does not exist in the database, but does in Active
        Directory, its information will be stored in the database for later
        lookup. However, this will only happen if ``ad_user_data`` is provided.

        Args:
            username (unicode):
                The name of the user to look up or create.

            request (django.http.HttpRequest, unused):
                The HTTP request from the client. This is unused.

            ad_user_data (list of tuple, optional):
                Data about the user to create. This is generally provided by
                :py:meth:`authenticate`.

        Returns:
            django.contrib.auth.models.User:
            The resulting user, or ``None`` if one could not be found.
        """
        username = self.INVALID_USERNAME_CHAR_REGEX.sub('', username).lower()

        try:
            return User.objects.get(username=username)
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
            except Exception:
                return None
