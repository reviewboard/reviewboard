from django.conf import settings
from django.contrib.auth.models import User
from djblets.util.misc import get_object_or_none
import crypt
import logging
import nis
import sys


class NISBackend:
    """
    Authenticate against a user on an NIS server.
    """

    def authenticate(self, username, password):
        try:
            passwd = nis.match(username, 'passwd').split(':')
            original_crypted = passwd[1]
            new_crypted = crypt.crypt(password, original_crypted)

            if original_crypted == new_crypted:
                return self.get_or_create_user(username, passwd)
        except nis.error:
            # FIXME I'm not sure under what situations this would fail (maybe if
            # their NIS server is down), but it'd be nice to inform the user.
            pass

    def get_or_create_user(self, username, passwd=None):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                if not passwd:
                    passwd = nis.match(username, 'passwd').split(':')

                names = passwd[4].split(' ', 1)
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

    def get_user(self, user_id):
        return get_object_or_none(User, pk=user_id)


class LDAPBackend:
    """
    Authenticate against a user on an LDAP server.
    """

    def authenticate(self, username, password):
        username = username.strip()
        uid = settings.LDAP_UID_MASK % username

        try:
            import ldap
            ldapo = ldap.initialize(settings.LDAP_URI)
            ldapo.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            if settings.LDAP_TLS:
                ldapo.start_tls_s()

            # May need to log in as the anonymous user before searching.
            if settings.LDAP_ANON_BIND_UID:
                ldapo.simple_bind_s(settings.LDAP_ANON_BIND_UID,
                                    settings.LDAP_ANON_BIND_PASSWD)

            search = ldapo.search_s(settings.LDAP_BASE_DN, ldap.SCOPE_SUBTREE,
                                    uid)
            if not search:
                # no such a user, return early, no need for bind attempts
                logging.warning("LDAP error: The specified object does not "
                                "exist in the Directory: %s" %
                                uid)
                return None

            ldapo.bind_s(search[0][0], password)

            return self.get_or_create_user(username)
        except ImportError:
            pass
        except ldap.INVALID_CREDENTIALS:
            logging.warning("LDAP error: The specified object does not "
                            "exist in the Directory or provided invalid credentials: %s" %
                            uid)
        except ldap.LDAPError, e:
            logging.warning("LDAP error: %s" % e)
        except:
            # fallback exception catch because
            # django.contrib.auth.authenticate() (our caller) catches only
            # TypeErrors
            logging.warning("An error while LDAP-authenticating: %r" %
                            sys.exc_info()[1])

        return None

    def get_or_create_user(self, username):
        try:
            user = User.objects.get(username=username)
            return user
        except User.DoesNotExist:
            try:
                import ldap
                ldapo = ldap.initialize(settings.LDAP_URI)
                ldapo.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
                if settings.LDAP_TLS:
                    ldapo.start_tls_s()
                if settings.LDAP_ANON_BIND_UID:
                    ldapo.simple_bind_s(settings.LDAP_ANON_BIND_UID,
                                        settings.LDAP_ANON_BIND_PASSWD)

                passwd = ldapo.search_s(settings.LDAP_BASE_DN,
                                        ldap.SCOPE_SUBTREE,
                                        settings.LDAP_UID_MASK % username)

                first_name = passwd[0][1]['givenName'][0]
                last_name = passwd[0][1]['sn'][0]

                if settings.LDAP_EMAIL_DOMAIN:
                    email = u'%s@%s' % (username, settings.LDAP_EMAIL_DOMAIN)
                elif settings.LDAP_EMAIL_ATTRIBUTE:
                    email = passwd[0][1][settings.LDAP_EMAIL_ATTRIBUTE][0]

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

    def get_user(self, user_id):
        return get_object_or_none(User, pk=user_id)


class ActiveDirectoryBackend:
    def get_domain_name(self):
        return str(settings.AD_DOMAIN_NAME)

    def get_ldap_search_root(self):
        root = ['dc=%s' % x for x in self.get_domain_name().split('.')]
        if settings.AD_OU_NAME:
            root = ['ou=%s' % settings.AD_OU_NAME] + root
        return ','.join(root)

    def search_ad(self, con, filterstr):
        import ldap
        search_root = self.get_ldap_search_root()
        logging.debug('Search root ' + search_root)
        return con.search_s(search_root, scope=ldap.SCOPE_SUBTREE, filterstr=filterstr)

    def find_domain_controllers_from_dns(self):
        import DNS
        DNS.Base.DiscoverNameServers()
        q = '_ldap._tcp.%s' % self.get_domain_name()
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
                    group_data = self.search_ad(con, '(&(objectClass=group)(saMAccountName=%s))' % group)
                    seen.update(self.get_member_of(con, group_data, seen=seen, depth=depth))
            else:
                logging.warning('ActiveDirectory recursive group check reached maximum recursion depth.')

        return seen

    def get_ldap_connections(self):
        import ldap
        if settings.AD_FIND_DC_FROM_DNS:
            dcs = self.find_domain_controllers_from_dns()
        else:
            dcs = [('389', settings.AD_DOMAIN_CONTROLLER)]

        for dc in dcs:
            port, host = dc
            con = ldap.open(host, port=int(port))
            if settings.AD_USE_TLS:
                con.start_tls_s()
            con.set_option(ldap.OPT_REFERRALS, 0)
            yield con

    def authenticate(self, username, password):
        import ldap
        connections = self.get_ldap_connections()

        username = username.strip()

        for con in connections:
            try:
                bind_username ='%s@%s' % (username, self.get_domain_name())
                con.simple_bind_s(bind_username, password)
                user_data = self.search_ad(con, '(&(objectClass=user)(sAMAccountName=%s))' % username)
                try:
                    group_names = self.get_member_of(con, user_data)
                except Exception, e:
                    logging.error("Active Directory error: failed getting groups for user %s" % username)
                    return None
                required_group = settings.AD_GROUP_NAME
                if required_group and not required_group in group_names:
                    logging.warning("Active Directory: User %s is not in required group %s" % (username, required_group))
                    return None

                return self.get_or_create_user(username, user_data)
            except ldap.SERVER_DOWN:
                logging.warning('Active Directory: Domain controller is down')
                continue
            except ldap.INVALID_CREDENTIALS:
                logging.warning('Active Directory: Failed login for user %s' % username)
                return None

        logging.error('Active Directory error: Could not contact any domain controller servers')
        return None

    def get_or_create_user(self, username, ad_user_data):
        try:
            user = User.objects.get(username=username)
            return user
        except User.DoesNotExist:
            try:
                first_name = ad_user_data[0][1]['givenName'][0]
                last_name = ad_user_data[0][1]['sn'][0]
                email = u'%s@%s' % (username, settings.AD_DOMAIN_NAME)

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

    def get_user(self, user_id):
        return get_object_or_none(User, pk=user_id)
