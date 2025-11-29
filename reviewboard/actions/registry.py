"""Registry for actions.

Version Added:
    6.0
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Iterator, List

from django.utils.translation import gettext_lazy as _
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         NOT_REGISTERED)
from housekeeping import func_deprecated

from reviewboard.actions.base import (ActionAttachmentPoint,
                                      ActionPlacement,
                                      AttachmentPoint,
                                      BaseAction,
                                      BaseGroupAction)
from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.registries.registry import OrderedRegistry, Registry


logger = logging.getLogger(__name__)


class ActionAttachmentPointsRegistry(Registry[ActionAttachmentPoint]):
    """A registry for action attachment points.

    Version Added:
        7.1
    """

    lookup_attrs = ['attachment_point_id']

    errors = {
        ALREADY_REGISTERED: _(
            '"%(item)s" is already a registered attachment point.'
        ),
        NOT_REGISTERED: _(
            '"%(attr_value)s" is not a registered attachment point.'
        ),
    }

    def get_defaults(self) -> Iterator[ActionAttachmentPoint]:
        """Yield the built-in attachment points.

        Yields:
            reviewboard.actions.base.BaseAction:
            The built-in attachment points.
        """
        yield from [
            ActionAttachmentPoint(AttachmentPoint.NON_UI),
            ActionAttachmentPoint(AttachmentPoint.HEADER),
            ActionAttachmentPoint(AttachmentPoint.REVIEW_REQUEST_LEFT),
            ActionAttachmentPoint(AttachmentPoint.REVIEW_REQUEST),
            ActionAttachmentPoint(AttachmentPoint.UNIFIED_BANNER),
            ActionAttachmentPoint(AttachmentPoint.QUICK_ACCESS),
        ]

    def get_attachment_point(
        self,
        attachment_point_id: str,
    ) -> ActionAttachmentPoint | None:
        """Return the attachment point with the given ID.

        Args:
            attachment_point_id (str):
                The attachment point ID to look up.

        Returns:
            reviewboard.actions.base.ActionAttachmentPoint:
            The resulting attachment point instance, or ``None`` if not found.
        """
        return self.get('attachment_point_id', attachment_point_id)


class ActionsRegistry(OrderedRegistry[BaseAction]):
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
    _by_attachment_point: defaultdict[
        str,
        dict[
            str,
            tuple[BaseAction, ActionPlacement]
        ]
    ]

    #: Actions deferring registration until a dependency is registered.
    _deferred_registrations: dict[str, list[BaseAction]]

    def __init__(self) -> None:
        """Initialize the registry."""
        super().__init__()

        self._by_attachment_point = defaultdict(dict)
        self._deferred_registrations = {}

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

        # Sanity-check each placement to make sure it has a valid parent
        # reference (if needed) and doesn't exceed the depth limit. Any that
        # does will be excluded from the page, but any that do will remain.
        #
        # In any case, the action will still be registered. Note that this is
        # a change from Review Board 6/7, since actions can now be registered
        # and referenced from multiple locations. It's no longer fatal for
        # one of these checks to fail.
        deferred_registrations = self._deferred_registrations
        parents: dict[str, tuple[BaseAction, ActionPlacement]] = {}
        placements = action.placements or []
        valid_placements: list[ActionPlacement] = []

        for placement in placements:
            attachment = placement.attachment
            parent_id = placement.parent_id
            parent: BaseAction | None

            if parent_id:
                parent = self.get_action(parent_id)

                if parent is None:
                    logger.warning('Deferring registration of action "%s" '
                                   'because parent action "%s" is not yet '
                                   'registered.',
                                   action_id, parent_id)
                    deferred_registrations.setdefault(
                        parent_id, []
                    ).append(action)
                    return

                parent_placement = parent.get_placement(attachment)

                if parent_placement is None:
                    logger.error(
                        'Action "%s" refers to a parent action "%s" in '
                        'attachment point "%s", but the parent is not '
                        'placed in that attachment point. Skipping.',
                        action_id, parent.action_id, attachment)
                    continue
                elif parent_placement.depth + 1 > self.MAX_DEPTH:
                    logger.error(
                        'Action "%s" exceeds the maximum depth limit of %s '
                        'for attachment point(s) "%s".',
                        action_id, self.MAX_DEPTH, attachment)
                    continue

                parents[attachment] = (parent, parent_placement)

            valid_placements.append(placement)

        super().register(action)

        action.parent_registry = self

        by_attachment_point = self._by_attachment_point

        for placement in valid_placements:
            attachment = placement.attachment

            # Store by attachment points, for quick lookup.
            by_attachment_point[attachment][action_id] = (action, placement)

            # Establish the parent/child relationship between actions.
            parent_info = parents.get(attachment)

            if parent_info:
                parent, parent_placement = parent_info

                assert isinstance(parent, BaseGroupAction)

                placement.parent_action = parent
                parent_placement.child_actions.append(action)
            else:
                placement.parent_action = None

        # Old versions of the extension hooks for actions encouraged people to
        # register their child actions before the parent. These get deferred
        # above, but there can be any number of deferred actions here all
        # referring to the same parent, so we have to iterate through this
        # entire list.
        for deferred in deferred_registrations.pop(action_id, []):
            self.register(deferred)

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
        action_id = action.action_id
        by_attachment_point = self._by_attachment_point

        for placement in (action.placements or []):
            attachment = placement.attachment
            attachment_actions = by_attachment_point[attachment]

            if (parent_action := placement.parent_action):
                parent_placement = parent_action.get_placement(attachment)

                if parent_placement is not None:
                    parent_placement.child_actions.remove(action)

                placement.parent_action = None

            # Remove the per-attachment lookups.
            try:
                attachment_actions.pop(action_id)

                if not attachment_actions:
                    del by_attachment_point[attachment]
            except KeyError:
                logger.warning('Action "%s" unexpectedly not found in '
                               'attachment point "%s" when unregistering.',
                               action_id, attachment)

        super().unregister(action)

        action.parent_registry = None

    def get_action(
        self,
        action_id: str,
    ) -> BaseAction | None:
        """Return the action with the given ID.

        Version Added:
            7.1

        Args:
            action_id (str):
                The action ID to look up.

        Returns:
            reviewboard.actions.base.BaseAction:
            The resulting action instance, or ``None`` if not found.
        """
        return self.get('action_id', action_id)

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
            for action, placement in attachment_actions.values():
                if placement.parent_id is None or include_children:
                    yield action

    @func_deprecated(RemovedInReviewBoard90Warning, message=(
        '%(func_name)s is deprecated and support will be removed in '
        '%(product)s %(version)s. Please use '
        'action.get_placement(...).child_actions instead.'
    ))
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
        parent = self.get_action(parent_id)

        assert parent is not None, (
            f'Action {parent_id!r} was not registered when calling '
            f'get_children().'
        )

        yield from parent.child_actions
