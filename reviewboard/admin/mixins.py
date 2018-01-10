"""View mixins provided by the admin app."""

from __future__ import unicode_literals

from django.utils.decorators import method_decorator

from reviewboard.admin.decorators import check_read_only


class CheckReadOnlyViewMixin(object):
    """View mixin to check if the site is read-only.

    This is a convenience around using the :py:func:`@check_reead_only
    <reviewboard.admin.decorators.check_read_only>` decorator for class-based
    views.
    """

    @method_decorator(check_read_only)
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
        return super(CheckReadOnlyViewMixin, self).dispatch(*args, **kwargs)
