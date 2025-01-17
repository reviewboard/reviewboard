"""Extra user detail introspection and representation.

Version Added:
    7.1
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar, Iterator, Optional, TYPE_CHECKING

from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from reviewboard.registries.registry import OrderedRegistry

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.http import HttpRequest
    from django.utils.safestring import SafeString

    from reviewboard.site.models import LocalSite


logger = logging.getLogger(__name__)


@dataclass
class UserBadge:
    """A badge shown alongside a user's name.

    Badges can represent some detail about a user. All badges are provided
    by extensions.

    Version Added:
        7.1
    """

    ######################
    # Instance variables #
    ######################

    #: The visual label shown on the badge.
    label: str

    #: The user this badge belongs to.
    user: User

    #: An optional CSS class (or classes) used for the badge.
    #:
    #: This allows an extension to provide custom styling for a badge, such
    #: as custom colors.
    #:
    #: Multiple CSS classes can be provided by separating them with spaces.
    css_class: Optional[str] = None

    def render_to_string(self) -> SafeString:
        """Render the badge to an HTML string.

        All badges use a ``rb-c-user-badge`` CSS class, along with any
        CSS classes provided in :py:attr:`css_class`.

        The label for the badge will reflect :py:attr:`label`.

        Returns:
            django.utils.safestring.SafeString:
            The HTML for the badge.
        """
        try:
            css_classes: list[str] = [
                'rb-c-user-badge',
            ]

            css_class = self.css_class

            if css_class:
                css_classes.append(css_class)

            attrs: list[tuple[str, str]] = [
                ('class', ' '.join(css_classes)),
            ]

            return format_html(
                '<span {attrs}>{label}</span>',
                attrs=format_html_join(' ', '{}="{}"', attrs),
                label=self.label)
        except Exception as e:
            logger.exception(
                'Unexpected error when rendering user badge %r: %s',
                self, e)

            return mark_safe('')


class BaseUserDetailsProvider:
    """Base class for a provider for additional user details.

    This enables extensions to provide additional information about users,
    for specialized rendering and logic.

    Version Added:
        7.1
    """

    #: The unique ID of the user details provider.
    user_details_provider_id: ClassVar[str]

    def get_user_badges(
        self,
        user: User,
        *,
        local_site: Optional[LocalSite],
        request: Optional[HttpRequest] = None,
    ) -> Iterator[UserBadge]:
        """Return a list of badges to display for a user.

        Badges provide a visual indicator about some aspect of a user, for
        display purposes.

        Args:
            user (django.contrib.auth.models.User):
                The user the badges must correspond to.

            local_site (reviewboard.site.models.LocalSite):
                The Local Site the badges must correspond to.

            request (django.http.HttpRequest, optional):
                The optional HTTP request from the client.

        Yields:
            UserBadge:
            Each badge to display.
        """
        yield from []


class UserDetailsProviderRegistry(OrderedRegistry[BaseUserDetailsProvider]):
    """A registry of user detail providers.

    Each provider in the registry will be queried when requesting additional
    information on users.

    Version Added:
        7.1
    """

    lookup_attrs = ('user_details_provider_id',)

    def get_user_details_provider(
        self,
        provider_id: str,
    ) -> Optional[BaseUserDetailsProvider]:
        """Return the user details provider for a given ID.

        Args:
            provider_id (str):
                The ID of the user details provider to return.

        Returns:
            UserDetailsProvider:
            The user details provider matching the ID, or ``None`` if not
            found.
        """
        return self.get('user_details_provider_id', provider_id)


#: The registry managing user details providers.
#:
#: Version Added:
#:     7.1
user_details_provider_registry = UserDetailsProviderRegistry()
