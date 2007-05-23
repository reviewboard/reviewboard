from django.conf import settings
from django.contrib.auth.models import User, check_password
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
                # FIXME: We're doing 2 NIS fetches here if the user does
                # not already exit.  It'd be nice to avoid that, but it's
                # not critical.
                return self.get_or_create_user(username)
        except nis.error:
            pass

    def get_or_create_user(self, username):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                passwd = nis.match(username, 'passwd').split(':')
                first_name, last_name = passwd[4].split(' ', 1)
                email = '%s@%s' % (username, settings.NIS_EMAIL_DOMAIN)

                user = User(username=username,
                            password='',
                            first_name=first_name,
                            last_name=last_name,
                            email=email)
                user.is_staff = False
                user.is_superuser = False
                user.save()
            except nis.error:
                pass
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class LDAPBackend:
    """
    Authenticate against a user on an LDAP server.
    """

    def authenticate(self, username, password):
        try:
            import ldap
            ldapo = ldap.initialize(settings.LDAP_URI)
            ldapo.set_option(ldap.OPT_PROTOCOL_VERSION, '3')
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
                ldapo.set_option(ldap.OPT_PROTOCOL_VERSION, '3')
                ldapo.simple_bind_s(settings.LDAP_ANON_BIND_UID, settings.LDAP_ANON_BIND_PASSWD)

                passwd = ldapo.search_s(settings.LDAP_UID_MASK % username,
                                        ldap.SCOPE_SUBTREE, "objectclass=*")

                first_name, last_name = passwd[0][1]['cn'][0].split(' ', 1)
                email = '%s@%s' % (username, settings.LDAP_EMAIL_DOMAIN)

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
                # I'd really like to warn the user that their ANON_BIND_UID
                # and ANON_BIND_PASSWD are wrong, but I don't know how
                pass
            except ldap.LDAPError:
                pass
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
