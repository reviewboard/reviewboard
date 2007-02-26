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
            original_crypted = nis.match(username, 'passwd').split(":")[1]
            new_crypted = crypt.crypt(password, original_crypted[:2])

            if original_crypted == new_crypted:
                user = User.objects.get(username=username)

        except nis.error:
            pass

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
