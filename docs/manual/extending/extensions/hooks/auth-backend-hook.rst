.. _auth-backend-hook:

===============
AuthBackendHook
===============

:py:class:`reviewboard.extensions.hooks.AuthBackendHook` allows extensions to
register new authentication backends, which can be used to integrate with
databases or servers to handle authentication, user lookup, and profile
manipulation.

Extensions must provide a subclass of
:py:class:`reviewboard.accounts.backends.AuthBackend`, and pass it as a
parameter to :py:class:`AuthBackendHook`. Each class must provide
:py:attr:`backend_id` and :py:attr:`name` attributes, and must implement
:py:meth:`authenticate` and :py:meth:`get_or_create_user` methods.


Example
=======

.. code-block:: python

    from typing import TYPE_CHECKING

    from django.contrib.auth.models import User
    from reviewboard.accounts.backends import AuthBackend
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import AuthBackendHook

    if TYPE_CHECKING:
        from django.http import HttpRequest


    class SampleAuthBackend(AuthBackend):
        backend_id = 'myvendor_sample_auth'
        name = 'Sample Authentication'

        def authenticate(
            self,
            username: str,
            password: str,
        ) -> User | None:
            if username == 'superuser' and password == 's3cr3t':
                return self.get_or_create_user(username, password=password)

            return None

        def get_or_create_user(
            self,
            username: str,
            request: (HttpRequest | None) = None,
            password: (str | None) = None,
        ) -> User:
            user, is_new = User.objects.get_or_create(username=username)

            if is_new:
                user.set_unusable_password()
                user.save()

            return user


    class SampleExtension(Extension):
        def initialize(self) -> None:
            AuthBackendHook(self, SampleAuthBackend)
