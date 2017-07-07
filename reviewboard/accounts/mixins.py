"""Mixins for account-related views."""

from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from reviewboard.accounts.decorators import (check_login_required,
                                             valid_prefs_required)


class CheckLoginRequiredViewMixin(object):
    """View mixin to check if a user needs to be logged in.

    This is a convenience around using the :py:func:`@check_login_required
    <reviewboard.accounts.decorators.check_login_required>` decorator for
    class-based views.
    """

    @method_decorator(check_login_required)
    def dispatch(self, *args, **kwargs):
        """Dispatch a HTTP request to the right handler.

        Args:
            *args (tuple):
                Positional arguments to pass to the handler.

            **kwargs (tuple):
                Keyword arguments to pass to the handler.

                These will be arguments provided by the URL pattern.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response to send to the client.
        """
        return super(CheckLoginRequiredViewMixin, self).dispatch(
            *args, **kwargs)


class LoginRequiredViewMixin(object):
    """View mixin to ensure a user is logged in.

    This is a convenience around using the :py:func:`@login_required
    <django.contrib.auth.decorators.login_required>` decorator for
    class-based views.
    """

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Dispatch a HTTP request to the right handler.

        Args:
            *args (tuple):
                Positional arguments to pass to the handler.

            **kwargs (tuple):
                Keyword arguments to pass to the handler.

                These will be arguments provided by the URL pattern.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response to send to the client.
        """
        return super(LoginRequiredViewMixin, self).dispatch(*args, **kwargs)


class UserProfileRequiredViewMixin(object):
    """View mixin to ensure a user has a profile set up.

    This is a convenience around using the :py:func:`@valid_prefs_required
    <reviewboard.accounts.decorators.valid_prefs_required>` decorator for
    class-based views.
    """

    @method_decorator(valid_prefs_required)
    def dispatch(self, *args, **kwargs):
        """Dispatch a HTTP request to the right handler.

        Args:
            *args (tuple):
                Positional arguments to pass to the handler.

            **kwargs (tuple):
                Keyword arguments to pass to the handler.

                These will be arguments provided by the URL pattern.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response to send to the client.
        """
        return super(UserProfileRequiredViewMixin, self).dispatch(
            *args, **kwargs)
