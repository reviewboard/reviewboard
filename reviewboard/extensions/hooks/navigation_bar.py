"""A hook for adding entries to the main navigation bar."""

from __future__ import annotations

from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint


class NavigationBarHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for adding entries to the main navigation bar.

    This takes a list of entries. Each entry represents something
    on the navigation bar, and is a dictionary with the following keys:

    ``label``:
        The label to display

    ``url``:
        The URL to point to.

    ``url_name``:
        The name of the URL to point to.

    Only one of ``url`` or ``url_name`` is required. ``url_name`` will
    take precedence.

    Optionally, a callable can be passed in for ``is_enabled_for``, which takes
    a single argument (the user) and returns True or False, indicating whether
    the entries should be shown. If this is not passed in, the entries are
    always shown (including for anonymous users).

    If your hook needs to access the template context, it can override
    :py:meth:`get_entries` and return results from there.
    """

    def initialize(self, entries=[], is_enabled_for=None, *args, **kwargs):
        """Initialize the hook.

        This will register each of the entries in the navigation bar.

        Args:
            entries (list of dict):
                The list of dictionary entries representing navigation
                bar items, as documented above.

            is_enabled_for (callable, optional):
                The optional function used to determine if these entries
                should appear for a given page. This is in the format of:

                .. code-block:: python

                   def is_enabled_for(user, request, local_site_name,
                                      **kwargs):
                       return True

                If not provided, the entries will be visible on every page.

            *args (tuple):
                Additional positional arguments. Subclasses should always
                pass these to this class.

            **kwargs (dict):
                Additional keyword arguments. Subclasses should always pass
                these to this class.
        """
        self.entries = entries
        self.is_enabled_for = is_enabled_for

    def get_entries(self, context):
        """Return the navigation bar entries defined in this hook.

        This can be overridden by subclasses if they need more control over
        the entries or need to access the template context.

        Args:
            context (django.template.RequestContext):
                The template context for the page.

        Returns:
            list of dict:
            The list of navigation bar entries. This will be empty if the
            entries are not enabled for this page.
        """
        request = context['request']

        if (not callable(self.is_enabled_for) or
            self.is_enabled_for(user=request.user,
                                request=request,
                                local_site_name=context['local_site_name'])):
            return self.entries
        else:
            return []
