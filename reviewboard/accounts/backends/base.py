"""Base class for authentication backends."""

from __future__ import unicode_literals

import re

from django.contrib.auth.models import User
from djblets.db.query import get_object_or_none


class BaseAuthBackend(object):
    """The base class for Review Board authentication backends."""

    backend_id = None
    name = None
    settings_form = None
    supports_anonymous_user = True
    supports_object_permissions = True
    supports_registration = False
    supports_change_name = False
    supports_change_email = False
    supports_change_password = False
    login_instructions = None

    INVALID_USERNAME_CHAR_REGEX = re.compile(r'[^\w.@+-]')

    def authenticate(self, **credentials):
        """Authenticate the user.

        This will authenticate the username and return the appropriate User
        object, or None.
        """
        raise NotImplementedError

    def get_or_create_user(self, username, request):
        """Get an existing user, or create one if it does not exist."""
        raise NotImplementedError

    def get_user(self, user_id):
        """Get an existing user, or None if it does not exist."""
        return get_object_or_none(User, pk=user_id)

    def update_password(self, user, password):
        """Update the user's password on the backend.

        Authentication backends can override this to update the password
        on the backend. This will only be called if
        :py:attr:`supports_change_password` is ``True``.

        By default, this will raise NotImplementedError.
        """
        raise NotImplementedError

    def update_name(self, user):
        """Update the user's name on the backend.

        The first name and last name will already be stored in the provided
        ``user`` object.

        Authentication backends can override this to update the name
        on the backend based on the values in ``user``. This will only be
        called if :py:attr:`supports_change_name` is ``True``.

        By default, this will do nothing.
        """
        pass

    def update_email(self, user):
        """Update the user's e-mail address on the backend.

        The e-mail address will already be stored in the provided
        ``user`` object.

        Authentication backends can override this to update the e-mail
        address on the backend based on the values in ``user``. This will only
        be called if :py:attr:`supports_change_email` is ``True``.

        By default, this will do nothing.
        """
        pass

    def query_users(self, query, request):
        """Search for users on the back end.

        This call is executed when the User List web API resource is called,
        before the database is queried.

        Authentication backends can override this to perform an external
        query. Results should be written to the database as standard
        Review Board users, which will be matched and returned by the web API
        call.

        The ``query`` parameter contains the value of the ``q`` search
        parameter of the web API call (e.g. /users/?q=foo), if any.

        Errors can be passed up to the web API layer by raising a
        reviewboard.accounts.errors.UserQueryError exception.

        By default, this will do nothing.
        """
        pass

    def search_users(self, query, request):
        """Custom user-database search.

        This call is executed when the User List web API resource is called
        and the ``q`` search parameter is provided, indicating a search
        query.

        It must return either a django.db.models.Q object or None.  All
        enabled backends are called until a Q object is returned.  If one
        isn't returned, a default search is executed.
        """
        return None
