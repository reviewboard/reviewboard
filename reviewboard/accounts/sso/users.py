"""Utilities for managing users with SSO.

Version Added:
    5.0
"""

import re

from django.contrib.auth.models import User
from django.db.models import Q

from reviewboard.accounts.sso.errors import InvalidUsernameError


# This matches what's used in Review Board URLs.
INVALID_USERNAME_CHARS_RE = re.compile(r'[^\w.@+-]+')


def find_suggested_username(email):
    """Return the suggested username for a given e-mail address.

    Version Added:
        5.0

    Args:
        email (str):
            The user's e-mail address.

    Returns:
        str:
        The suggested username.

    Raises:
        reviewboard.accounts.sso.errors.InvalidUsernameError:
            The suggested username does not work with Review Board's rules.
    """
    # Normalize the username, factoring in everything before the '@' (if any)
    # and converting any non-alphanumeric characters to dashes. Then we'll
    # sanity-check that it meets our username criteria.
    norm_user_id = INVALID_USERNAME_CHARS_RE.sub('-', email.split('@')[0])

    if (norm_user_id.startswith('-') or
        norm_user_id.endswith('-') or
        '--' in norm_user_id):
        # This is an invalid username.
        raise InvalidUsernameError('Invalid SSO username "%s"' % norm_user_id)

    return norm_user_id


def find_user_for_sso_user_id(username, email, alternate_username):
    """Find a matching user for SSO login.

    Version Added:
        5.0

    Args:
        username (str):
            The username, if available. May be ``None``.

        email (str):
            The user's e-mail address.

        alternate_username (str):
            An alternate username to try, if ``username`` is ``None``. This
            probably comes from :py:func:`find_suggested_username`.

    Returns:
        django.contrib.auth.models.User:
        The user object, if one exists.
    """
    q = Q()

    if username:
        q |= Q(username=username)

    q |= Q(email=email) | Q(username=alternate_username)

    # Fetch all candidates first to save on DB queries.
    candidate_users = list(User.objects.filter(q))

    # First try by username. This will be present if the username has been
    # specified in the SSO provider.
    if username:
        for user in candidate_users:
            if user.username == username:
                return user

    # Next see if we have a user with a matching e-mail address.
    for user in candidate_users:
        if user.email == email:
            return user

    # Finally, try a computed username from the e-mail address.
    for user in candidate_users:
        if user.username == alternate_username:
            return user

    return None
