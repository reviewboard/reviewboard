"""A hook for adding information to the user infobox."""

from __future__ import annotations

from django.template.loader import render_to_string
from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint


class UserInfoboxHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for adding information to the user infobox.

    Extensions can use this hook to add additional pieces of data to the box
    which pops up when hovering the mouse over a user.
    """

    def initialize(self, template_name=None):
        """Initialize the hook.

        Args:
            template_name (unicode):
                The template to render with the default :py:func:`render`
                method.
        """
        self.template_name = template_name

    def get_extra_context(self, user, request, local_site, **kwargs):
        """Return extra context to use when rendering the template.

        This may be overridden in order to make use of the default
        :py:func:`render` method.

        Args:
            user (django.contrib.auth.models.User):
                The user whose infobox is being shown.

            request (django.http.HttpRequest):
                The request for the infobox view.

            local_site (reviewboard.site.models.LocalSite):
                The local site, if any.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            Additional context to include when rendering the template.
        """
        return {}

    def get_etag_data(self, user, request, local_site, **kwargs):
        """Return data to be included in the user infobox ETag.

        The infobox view uses an ETag to enable browser caching of the content.
        If the extension returns data which can change, this method should
        return a string which is unique to that data.

        Args:
            user (django.contrib.auth.models.User):
                The user whose infobox is being shown.

            request (django.http.HttpRequest):
                The request for the infobox view.

            local_site (reviewboard.site.models.LocalSite):
                The local site, if any.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            unicode:
            A string to be included in the ETag for the view.
        """
        return ''

    def render(self, user, request, local_site, **kwargs):
        """Return content to include in the user infobox.

        This may be overridden in the case where providing a custom template
        and overriding :py:func:`get_extra_context` is insufficient.

        Args:
            user (django.contrib.auth.models.User):
                The user whose infobox is being shown.

            request (django.http.HttpRequest):
                The request for the infobox view.

            local_site (reviewboard.site.models.LocalSite):
                The local site, if any.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            django.utils.safestring.SafeText:
            Text to include in the infobox HTML.
        """
        assert self.template_name is not None

        context = {
            'extension': self.extension,
            'user': user,
        }
        context.update(self.get_extra_context(user=user,
                                              request=request,
                                              local_site=local_site))
        return render_to_string(
            template_name=self.template_name,
            context=context,
            request=request)
