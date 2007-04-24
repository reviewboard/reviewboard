from django.conf import settings
from django.contrib.auth.models import User, check_password
import crypt
import nis

class NISBackend:
    """
    Authenticate against a user on an NIS server.
    """

    def authenticate(self, username, password):
        user = None

        try:
            passwd = nis.match(username, 'passwd').split(':')
            original_crypted = passwd[1]
            new_crypted = crypt.crypt(password, original_crypted[:2])

            if original_crypted == new_crypted:
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    # Create a new user.
                    first_name, last_name = passwd[4].split(' ', 2)
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

    def get_or_create_user(self, user_id):
        # FIXME: remove duplication with authenticate()
        user = self.get_user(user_id)
        if not user:
            try:
                passwd = nis.match(username, 'passwd').split(':')
                first_name, last_name = passwd[4].split(' ', 2)
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
