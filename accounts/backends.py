from django.conf import settings
from django.contrib.auth.models import User
from djblets.util.misc import get_object_or_none
import crypt
import logging
import nis


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
        try:
            import ldap
            ldapo = ldap.initialize(settings.LDAP_URI)
            ldapo.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            if settings.LDAP_TLS:
                ldapo.start_tls_s()
            search = ldapo.search_s(settings.LDAP_BASE_DN, ldap.SCOPE_ONELEVEL,
                                    settings.LDAP_UID_MASK % username)
            ldapo.bind_s(search[0][0], password)

            return self.get_or_create_user(username)
        except ImportError:
            pass
        except ldap.INVALID_CREDENTIALS:
            logging.warning("LDAP error: The specified object does not "
                            "exist in the Directory: %s" %
                            settings.LDAP_UID_MASK % username)
        except ldap.LDAPError, e:
            logging.warning("LDAP error: %s" % e)

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
                                        ldap.SCOPE_ONELEVEL,
                                        settings.LDAP_UID_MASK % username)

                first_name = passwd[0][1]['givenName'][0]
                last_name = passwd[0][1]['sn'][0]
                email = u'%s@%s' % (username, settings.LDAP_EMAIL_DOMAIN)

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
