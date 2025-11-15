"""Registry for actions.

Version Added:
    6.0
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Iterator, List, Optional

from django.utils.translation import gettext_lazy as _
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         NOT_REGISTERED)

from reviewboard.actions.base import BaseAction
from reviewboard.actions.errors import DepthLimitExceededError
from reviewboard.registries.registry import OrderedRegistry


logger = logging.getLogger(__name__)


class ActionsRegistry(OrderedRegistry):
    """A registry for actions.

    Version Added:
        6.0
    """

    lookup_attrs = ['action_id']

    errors = {
        ALREADY_REGISTERED: _('"%(item)s" is already a registered action.'),
        NOT_REGISTERED: _('"%(attr_value)s" is not a registered action.'),
    }

    MAX_DEPTH = 2

    ######################
    # Instance variables #
    ######################

    #: Action lookup by attachment point.
    #:
    #: Version Added:
    #:     7.1
    _by_attachment_point: defaultdict[str, dict[str, BaseAction]]

    #: Actions deferring registration until a dependency is registered.
    _deferred_registrations: list[BaseAction]

    def __init__(self) -> None:
        """Initialize the registry."""
        super().__init__()

        self._by_attachment_point = defaultdict(dict)
        self._deferred_registrations = []

    def get_defaults(self) -> Iterator[BaseAction]:
        """Yield the built-in actions.

        Yields:
            reviewboard.actions.base.BaseAction:
            The built-in actions.
        """
        from reviewboard.accounts.actions import (
            AccountMenuAction,
            AdminAction,
            DocumentationAction,
            FollowFacebookAction,
            FollowBlueSkyAction,
            FollowLinkedInAction,
            FollowMastodonAction,
            FollowMenuAction,
            FollowRedditAction,
            FollowNewsAction,
            FollowTwitterAction,
            FollowYouTubeAction,
            LoginAction,
            LogoutAction,
            MyAccountAction,
            SupportAction,
            SupportMenuAction,
        )
        from reviewboard.reviews.actions import (
            AddGeneralCommentAction,
            ArchiveAction,
            ArchiveMenuAction,
            CloseMenuAction,
            CloseCompletedAction,
            CloseDiscardedAction,
            CreateReviewAction,
            DeleteAction,
            DownloadDiffAction,
            EditReviewAction,
            LegacyAddGeneralCommentAction,
            LegacyEditReviewAction,
            LegacyShipItAction,
            MuteAction,
            QuickAccessAddGeneralCommentAction,
            QuickAccessCreateReviewAction,
            QuickAccessEditReviewAction,
            QuickAccessShipItAction,
            ReviewMenuAction,
            ShipItAction,
            StarAction,
            UpdateMenuAction,
            UploadDiffAction,
            UploadFileAction,
        )

        # The order here is important, and will reflect the order that items
        # appear in the UI.
        builtin_actions: List[BaseAction] = [
            # Header bar
            AccountMenuAction(),
            LoginAction(),
            MyAccountAction(),
            AdminAction(),
            LogoutAction(),
            SupportMenuAction(),
            DocumentationAction(),
            SupportAction(),
            FollowMenuAction(),
            FollowNewsAction(),
            FollowBlueSkyAction(),
            FollowFacebookAction(),
            FollowLinkedInAction(),
            FollowMastodonAction(),
            FollowRedditAction(),
            FollowTwitterAction(),
            FollowYouTubeAction(),

            # Review request actions (left side)
            StarAction(),
            ArchiveMenuAction(),
            ArchiveAction(),
            MuteAction(),

            # Review request actions (right side)
            CloseMenuAction(),
            CloseCompletedAction(),
            CloseDiscardedAction(),
            DeleteAction(),
            UpdateMenuAction(),
            UploadDiffAction(),
            UploadFileAction(),
            DownloadDiffAction(),
            LegacyEditReviewAction(),
            LegacyShipItAction(),
            LegacyAddGeneralCommentAction(),

            # Unified banner actions
            ReviewMenuAction(),
            CreateReviewAction(),
            EditReviewAction(),
            AddGeneralCommentAction(),
            ShipItAction(),
            QuickAccessCreateReviewAction(),
            QuickAccessEditReviewAction(),
            QuickAccessAddGeneralCommentAction(),
            QuickAccessShipItAction(),
        ]

        for action in builtin_actions:
            yield action

    def register(
        self,
        action: BaseAction,
    ) -> None:
        """Register an item.

        Args:
            action (reviewboard.actions.base.BaseAction):
                The action to register.

        Raises:
            djblets.registries.errors.AlreadyRegisteredError:
                The item is already registered or if the item shares an
                attribute name, attribute value pair with another item in
                the registry.

            djblets.registries.errors.RegistrationError:
                The item is missing one of the required attributes.

            reviewboard.actions.errors.DepthLimitExceededError:
                The action was nested too deeply.
        """
        action_id = action.action_id
        assert action_id is not None

        parent: Optional[BaseAction]

        if action.parent_id:
            parent = self.get('action_id', action.parent_id)

            if parent is None:
                logger.warning('Deferring registration of action %s because '
                               'parent action %s is not yet registered.',
                               action_id, action.parent_id)
                self._deferred_registrations.append(action)
                return

            if parent.depth + 1 > self.MAX_DEPTH:
                raise DepthLimitExceededError(action_id,
                                              depth_limit=self.MAX_DEPTH)
        else:
            parent = None

        super().register(action)

        # Store this by attachment point, for quick lookup.
        if (attachment := action.attachment):
            self._by_attachment_point[attachment][action_id] = action

        # Establish the parent/child relationship between actions.
        if parent:
            action.parent_action = parent
            parent.child_actions.append(action)
        else:
            action.parent_action = None

        # Old versions of the extension hooks for actions encouraged people to
        # register their child actions before the parent. These get deferred
        # above, but there can be any number of deferred actions here all
        # referring to the same parent, so we have to iterate through this
        # entire list.
        for deferred in self._deferred_registrations:
            if deferred.parent_id == action_id:
                self.register(deferred)
                self._deferred_registrations.remove(deferred)

    def unregister(
        self,
        action: BaseAction,
    ) -> None:
        """Unregister an item.

        Args:
            action (reviewboard.actions.base.BaseAction):
                The action to unregister.

        Raises:
            djblets.registries.errors.ItemLookupError:
                Raised if the item is not found in the registry.
        """
        if (parent_action := action.parent_action):
            parent_action.child_actions.remove(action)
            action.parent_action = None

        # Remove the per-attachment lookups.
        if (attachment := action.attachment):
            assert action.action_id

            by_attachment_point = self._by_attachment_point
            attachment_actions = by_attachment_point[attachment]

            try:
                attachment_actions.pop(action.action_id)

                if not attachment_actions:
                    del by_attachment_point[attachment]
            except KeyError:
                logger.warning('Action "%s" unexpectedly not found in '
                               'attachment point "%s" when unregistering.',
                               action.action_id, attachment)

        super().unregister(action)

    def get_for_attachment(
        self,
        attachment: str,
        *,
        include_children: bool = False,
    ) -> Iterator[BaseAction]:
        """Yield actions for the given attachment point.

        Args:
            attachment (reviewboard.actions.base.AttachmentPoint):
                The attachment point.

            include_children (bool, optional):
                Whether to also include children of menus. If ``False``, this
                will only yield the top-level items.

        Yields:
            reviewboard.actions.base.BaseAction:
            The actions for the given attachment point.
        """
        self.populate()

        attachment_actions = self._by_attachment_point.get(attachment)

        if attachment_actions:
            for action in attachment_actions.values():
                if action.parent_id is None or include_children:
                    yield action

    def get_children(
        self,
        parent_id: str,
    ) -> Iterator[BaseAction]:
        """Return the children for a menu action.

        Args:
            parent_id (str):
                The ID of the parent.

        Yields:
            reviewboard.actions.base.BaseAction:
            The actions that are contained within the menu.
        """
        parent = self.get('action_id', parent_id)
        assert parent is not None

        yield from parent.child_actions
