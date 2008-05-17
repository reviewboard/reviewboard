from django.conf import settings
from django.contrib.auth.models import User
from djblets.util.misc import get_object_or_none
import crypt
import nis

class NISBackend:
    """
    Authenticate against a user on an NIS server.
    """

    def authenticate(self, username, password):
        try:
            passwd = nis.match(username, 'passwd').split(':')
            original_crypted = passwd[1]
            new_crypted = crypt.crypt(password, original_crypted[:2])

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
            ldapo.simple_bind_s(settings.LDAP_UID_MASK % username, password)

            return self.get_or_create_user(username)

        except ImportError:
            pass
        except ldap.INVALID_CREDENTIALS:
            pass

    def get_or_create_user(self, username):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                import ldap
                ldapo = ldap.initialize(settings.LDAP_URI)
                ldapo.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
                ldapo.simple_bind_s(settings.LDAP_ANON_BIND_UID, settings.LDAP_ANON_BIND_PASSWD)

                passwd = ldapo.search_s(settings.LDAP_UID_MASK % username,
                                        ldap.SCOPE_SUBTREE, "objectclass=*")

                first_name, last_name = passwd[0][1]['cn'][0].split(' ', 1)
                email = u'%s@%s' % (username, settings.LDAP_EMAIL_DOMAIN)

                user = User(username=username,
                            password='',
                            first_name=first_name,
                            last_name=last_name,
                            email=email)
                user.is_staff = False
                user.is_superuser = False
                user.save()
            except ImportError:
                pass
            except ldap.INVALID_CREDENTIALS:
                # FIXME I'd really like to warn the user that their
                # ANON_BIND_UID and ANON_BIND_PASSWD are wrong, but I don't
                # know how
                pass
            except ldap.NO_SUCH_OBJECT:
                pass
            except ldap.LDAPError:
                pass
        return user

    def get_user(self, user_id):
        return get_object_or_none(User, pk=user_id)
