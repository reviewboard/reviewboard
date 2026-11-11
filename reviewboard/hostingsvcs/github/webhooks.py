"""Support for GitHub App webhook handling.

Version Added:
    9.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from django.utils.translation import gettext_lazy as _
from djblets.registries.errors import RegistrationError
from djblets.registries.registry import ALREADY_REGISTERED, NOT_REGISTERED

from reviewboard.registries.registry import OrderedRegistry

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from typing import ClassVar, TypeAlias

    from typelets.django.strings import StrOrPromise
    from typelets.json import JSONDict

    from reviewboard.hostingsvcs.models import HostingServiceAccount
    from reviewboard.scmtools.models import Repository


logger = logging.getLogger(__name__)


#: The error name for an invalid webhook handler.
#:
#: Version Added:
#:     9.0
INVALID_HANDLER = 'invalid_handler'


#: An access level for a GitHub App permission.
#:
#: Version Added:
#:     9.0
GitHubAppPermissionLevel: TypeAlias = Literal['read', 'write', 'admin']


#: The ranking of GitHub App permission access levels.
#:
#: Higher values grant more access.
#:
#: Version Added:
#:     9.0
_PERMISSION_LEVEL_RANKS: Mapping[GitHubAppPermissionLevel, int] = {
    'read': 1,
    'write': 2,
    'admin': 3,
}


def merge_github_app_permissions(
    permissions_list: Iterable[Mapping[str, GitHubAppPermissionLevel]],
) -> dict[str, GitHubAppPermissionLevel]:
    """Merge GitHub App permissions.

    When more than one mapping requests the same permission, the highest
    access level (``read``, then ``write``, then ``admin``) is kept.

    Version Added:
        9.0

    Args:
        permissions_list (list of dict):
            The permission mappings to merge. Each maps a GitHub App
            permission name to an access level.

    Returns:
        dict:
        The merged mapping of permission names to access levels.
    """
    result: dict[str, GitHubAppPermissionLevel] = {}

    for permissions in permissions_list:
        for name, level in permissions.items():
            rank = _PERMISSION_LEVEL_RANKS.get(level)

            if rank is None:
                logger.warning(
                    'Unknown access level %r for GitHub App permission %r.',
                    level, name)
                continue

            existing_level = result.get(name)

            if (existing_level is None or
                rank > _PERMISSION_LEVEL_RANKS[existing_level]):
                result[name] = level

    return result


def merge_github_app_permission_labels(
    labels_list: Iterable[Mapping[str, StrOrPromise]],
) -> dict[str, StrOrPromise]:
    """Merge GitHub App permission label mappings.

    This keeps the first label found for each key.

    Version Added:
        9.0

    Args:
        labels_list (list of dict):
            The label mappings to merge.

    Returns:
        dict:
        The merged mapping of keys to labels.
    """
    result: dict[str, StrOrPromise] = {}

    for labels in labels_list:
        for key, label in labels.items():
            result.setdefault(key, label)

    return result


@dataclass(frozen=True, kw_only=True)
class GitHubAppWebhookEvent:
    """A GitHub App webhook event.

    Version Added:
        9.0
    """

    ######################
    # Instance variables #
    ######################

    #: The event name.
    #:
    #: This is the value of the :mailheader:`X-GitHub-Event` header.
    event_name: str

    #: The ID of the delivery.
    #:
    #: This is the value of the :mailheader:`X-GitHub-Delivery` header.
    delivery_id: str

    #: The decoded payload of the event.
    payload: JSONDict

    #: The app-record account for the GitHub App the event was sent from.
    app_account: HostingServiceAccount

    #: The installation account the event applies to, if any.
    installation_account: HostingServiceAccount | None

    #: The repository the event applies to, if any.
    repository: Repository | None


class BaseGitHubAppWebhookHandler:
    """Base class for a handler of GitHub App webhook events.

    Subclasses will list the events they handle and the GitHub App
    permissions they require, and implement :py:meth:`handle_event`.

    Version Added:
        9.0
    """

    #: The unique ID of the handler.
    handler_id: ClassVar[str]

    #: The names of the GitHub events the handler receives.
    #:
    #: These will be requested when connecting a GitHub App.
    events: ClassVar[set[str]]

    #: The GitHub App permissions required for the handler's events.
    #:
    #: This maps a permission name to the access level needed. These will be
    #: requested when connecting a GitHub App.
    required_permissions: ClassVar[
        Mapping[str, GitHubAppPermissionLevel]] = {}

    #: Localized labels for the handler's events.
    #:
    #: This maps an event name to a label shown to admins when connecting
    #: a GitHub App.
    event_labels: ClassVar[Mapping[str, StrOrPromise]] = {}

    #: Localized labels for the handler's required permissions.
    #:
    #: This maps a permission name to a label shown to admins when
    #: connecting a GitHub App.
    permission_labels: ClassVar[Mapping[str, StrOrPromise]] = {}

    def handle_event(
        self,
        event: GitHubAppWebhookEvent,
    ) -> None:
        """Handle an event delivered to the GitHub App webhook.

        Args:
            event (GitHubAppWebhookEvent):
                The event that was delivered.

        Raises:
            Exception:
                An error occurred while handling the event. This will be
                logged.
        """
        raise NotImplementedError


class GitHubAppWebhookHandlerRegistry(
    OrderedRegistry[BaseGitHubAppWebhookHandler],
):
    """A registry for GitHub App webhook handlers.

    Version Added:
        9.0
    """

    lookup_attrs = ['handler_id']

    errors = {
        ALREADY_REGISTERED: _(
            '"%(item)s" is already a registered GitHub App webhook handler.'
        ),
        NOT_REGISTERED: _(
            '"%(attr_value)s" is not a registered GitHub App webhook '
            'handler.'
        ),
        INVALID_HANDLER: _(
            'Could not register GitHub App webhook handler %(item)s: '
            '%(errors)s.'
        ),
    }

    ######################
    # Instance variables #
    ######################

    #: The cached names of all events handled by registered handlers.
    #:
    #: This is ``None`` until it's computed, and is cleared whenever a
    #: handler is registered or unregistered.
    _events: frozenset[str] | None

    def __init__(self) -> None:
        """Initialize the registry."""
        self._events = None

        super().__init__()

    def on_item_registering(
        self,
        handler: BaseGitHubAppWebhookHandler,
        /,
    ) -> None:
        """Handle pre-registration of a handler.

        This will validate that the handler has an ID, at least one event,
        and only valid permission access levels. Invalid handlers are not
        registered.

        Args:
            handler (BaseGitHubAppWebhookHandler):
                The handler being registered.

        Raises:
            djblets.registries.errors.RegistrationError:
                The handler is not valid.
        """
        super().on_item_registering(handler)

        errors: list[str] = []

        handler_id = getattr(handler, 'handler_id', None)

        if not handler_id or not isinstance(handler_id, str):
            errors.append('handler_id must be a non-empty string')

        events = getattr(handler, 'events', None)

        if not events or not isinstance(events, set):
            errors.append('events must be a non-empty set')

        for name, level in handler.required_permissions.items():
            if level not in _PERMISSION_LEVEL_RANKS:
                errors.append(
                    f'required_permissions has invalid access level '
                    f'{level!r} for permission {name!r}')

        if errors:
            raise RegistrationError(self.format_error(
                INVALID_HANDLER,
                item=handler,
                errors=', '.join(errors)))

    def on_item_registered(
        self,
        handler: BaseGitHubAppWebhookHandler,
        /,
    ) -> None:
        """Handle post-registration of a handler.

        This will reset the cached event names.

        Args:
            handler (BaseGitHubAppWebhookHandler):
                The handler that was registered.
        """
        super().on_item_registered(handler)

        self._events = None

    def on_item_unregistered(
        self,
        handler: BaseGitHubAppWebhookHandler,
        /,
    ) -> None:
        """Handle post-unregistration of a handler.

        This will reset the cached event names.

        Args:
            handler (BaseGitHubAppWebhookHandler):
                The handler that was unregistered.
        """
        super().on_item_unregistered(handler)

        self._events = None

    def get_handlers_for_event(
        self,
        event: str,
    ) -> Sequence[BaseGitHubAppWebhookHandler]:
        """Return the handlers registered for an event.

        Args:
            event (str):
                The name of the GitHub event.

        Returns:
            list of BaseGitHubAppWebhookHandler:
            The handlers for the event, in the order they were registered.
        """
        return [
            handler
            for handler in self
            if event in handler.events
        ]

    def get_events(self) -> frozenset[str]:
        """Return the names of all events handled by registered handlers.

        Returns:
            frozenset of str:
            The names of the events.
        """
        events = self._events

        if events is None:
            events = frozenset(
                event
                for handler in self
                for event in handler.events
            )
            self._events = events

        return events

    def get_required_permissions(
        self,
    ) -> Mapping[str, GitHubAppPermissionLevel]:
        """Return all the permissions required by registered handlers.

        When more than one handler requires the same permission, the highest
        access level is returned.

        Returns:
            dict:
            A mapping of GitHub App permission names to access levels.
        """
        return merge_github_app_permissions(
            handler.required_permissions
            for handler in self
        )

    def get_event_labels(self) -> Mapping[str, StrOrPromise]:
        """Return the event labels provided by registered handlers.

        When more than one handler provides a label for the same event, the
        label from the first registered handler is returned.

        Returns:
            dict:
            A mapping of GitHub event names to human-readable labels.
        """
        return merge_github_app_permission_labels(
            handler.event_labels
            for handler in self
        )

    def get_permission_labels(self) -> Mapping[str, StrOrPromise]:
        """Return the permission labels provided by registered handlers.

        When more than one handler provides a label for the same permission,
        the label from the first registered handler is returned.

        Returns:
            dict:
            A mapping of GitHub App permission names to human-readable
            labels.
        """
        return merge_github_app_permission_labels(
            handler.permission_labels
            for handler in self
        )


#: The registry of GitHub App webhook handlers.
#:
#: Version Added:
#:     9.0
github_app_webhook_handler_registry = GitHubAppWebhookHandlerRegistry()
