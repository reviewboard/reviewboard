"""Registry for actions.

Version Added:
    6.0
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Iterator

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         NOT_REGISTERED,
                                         RegistryState)
from housekeeping import func_deprecated

from reviewboard.actions.base import (ActionAttachmentPoint,
                                      ActionPlacement,
                                      AttachmentPoint,
                                      BaseAction,
                                      BaseGroupAction)
from reviewboard.actions.renderers import ButtonActionRenderer
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
        from reviewboard.admin.actions import (
            get_default_admin_attachment_points,
        )

        yield from get_default_admin_attachment_points()
        yield from (
            ActionAttachmentPoint(AttachmentPoint.NON_UI),
            ActionAttachmentPoint(AttachmentPoint.HEADER),
            ActionAttachmentPoint(AttachmentPoint.REVIEW_REQUEST_LEFT),
            ActionAttachmentPoint(AttachmentPoint.REVIEW_REQUEST),
            ActionAttachmentPoint(AttachmentPoint.UNIFIED_BANNER),
            ActionAttachmentPoint(
                AttachmentPoint.QUICK_ACCESS,
                default_action_renderer_cls=ButtonActionRenderer,
            ),
        )

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

    #: Placements deferring registration until a dependency is registered.
    #:
    #: Keys are tuples in the form of ``(parent_id, attachment)``.
    #
    #: Values are dictionaries are in the form of ``{action_id: action}``.
    #:
    #: Version Added:
    #:     7.1
    _deferred_placements: defaultdict[
        tuple[str, str],
        dict[str, BaseAction]
    ]

    def __init__(self) -> None:
        """Initialize the registry."""
        super().__init__()

        self._by_attachment_point = defaultdict(dict)
        self._deferred_placements = defaultdict(dict)

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
        from reviewboard.admin.actions import get_default_admin_actions
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
            ReviewMenuAction,
            ShipItAction,
            StarAction,
            UpdateMenuAction,
            UploadDiffAction,
            UploadFileAction,
        )

        # The order here is important, and will reflect the order that items
        # appear in the UI.
        yield from (
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
        )

        yield from get_default_admin_actions()

    def on_reset(self) -> None:
        """Handle cleanup after resetting the registry.

        This clears cached state used for looking up actions by attachment
        point and deferred placements.
        """
        super().on_reset()

        # If everything went as expected, these lists should be empty. But
        # on the off-chance that there's a bug, we want to assert in debug
        # mode so we can catch this without affecting production.
        if settings.DEBUG or settings.RUNNING_TEST:
            assert self._by_attachment_point == {}, self._by_attachment_point
            assert self._deferred_placements == {}, self._deferred_placements

        self._by_attachment_point.clear()
        self._deferred_placements.clear()

    def on_item_registered(
        self,
        action: BaseAction,
        /,
    ) -> None:
        """Handle post-registration placement of an action.

        This will process any placements for the action, putting them in
        the right place within an attachment point's action hierarchy.

        It will also handle deferring any placements for parent actions not
        yet registered, and processing of deferred placements for actions
        now registered.

        Args:
            action (reviewboard.actions.base.BaseAction):
                The action that was registered.
        """
        super().on_item_registered(action)

        action.parent_registry = self

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
        deferred_placements = self._deferred_placements
        seen_attachments: set[str] = set()

        for placement in (action.placements or []):
            attachment = placement.attachment

            if attachment in seen_attachments:
                logger.warning(
                    'Action "%s" has been placed in attachment "%s" more '
                    'than once. Only the first instance will be placed.',
                    action_id, attachment)
                continue

            seen_attachments.add(attachment)

            parent_id = placement.parent_id
            parent_placement: (ActionPlacement | None) = None
            parent: (BaseAction | None) = None

            if parent_id:
                parent = self.get_action(parent_id)

                if parent is None:
                    # Old versions of the extension hooks for actions
                    # encouraged people to register their child actions before
                    # the parent. Furthermore, since actions can be placed in
                    # multiple parents, not all parents may be registered.
                    # Defer these placements until they've been set up.
                    logger.debug(
                        'Deferring placement of action "%s" in attachment '
                        'point "%s" because parent action "%s" is not yet '
                        'registered.',
                        action_id, attachment, parent_id)

                    defer_key = (parent_id, attachment)
                    deferred_placements[defer_key][action_id] = action
                    continue

                try:
                    parent_placement = parent.get_placement(attachment)
                except KeyError as e:
                    logger.error(
                        'Invalid placement %r found while registering action '
                        '%r in parent %r: %s',
                        attachment, action_id, parent_id, e)
                    continue

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

            self._setup_placement(
                action=action,
                placement=placement,
                parent=parent,
                parent_placement=parent_placement,
            )

    def on_item_unregistering(
        self,
        action: BaseAction,
        /,
    ) -> None:
        """Handle pre-unregistration tasks for an action.

        Args:
            action (reviewboard.actions.base.BaseAction):
                The action to unregister.
        """
        for placement in (action.placements or []):
            self._remove_placement(action, placement,
                                   unregistered=True)

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

    def _setup_placement(
        self,
        *,
        action: BaseAction,
        placement: ActionPlacement,
        parent: BaseAction | None,
        parent_placement: ActionPlacement | None,
    ) -> None:
        """Set up a placement for an action.

        This will place the action within the attachment, parented to another
        action if specified.

        If the action being placed was a blocker for any deferred placements,
        those placements will be processed.

        Args:
            action (reviewboard.actions.base.BaseAction):
                The action being placed.

            placement (reviewboard.actions.base.ActionPlacement):
                The placement for this action.

            parent (reviewboard.actions.base.BaseAction):
                The parent action this will be placed under, if any.

            parent_placement (reviewboard.actions.base.ActionPlacement):
                The placement for the parent action, if a parent is specified.
        """
        attachment = placement.attachment
        action_id = action.action_id

        # Store by attachment points, for quick lookup.
        self._by_attachment_point[attachment][action_id] = (action, placement)

        # Establish the parent/child relationship between actions.
        if parent is not None:
            assert isinstance(parent, BaseGroupAction)
            assert parent_placement is not None

            placement.parent_action = parent
            parent_placement.child_actions.append(action)
        else:
            placement.parent_action = None

        # Go through any deferred placements parented here and add them,
        # recursively.
        deferred = self._deferred_placements.pop((action_id, attachment), {})

        for deferred_action in deferred.values():
            if self.state != RegistryState.POPULATING:
                # If we're not initially populating the registry with the
                # defaults shipped with Review Board, leave a debug message
                # that this will be deferred in case an extension author is
                # unsure why their action isn't showing up.
                logger.debug(
                    'Adding deferred placement of action "%s" in attachment '
                    'point "%s" for parent action "%s".',
                    deferred_action.action_id, attachment,
                    action_id)

            self._setup_placement(
                action=deferred_action,
                placement=deferred_action.get_placement(attachment),
                parent=action,
                parent_placement=placement,
            )

    def _remove_placement(
        self,
        action: BaseAction,
        placement: ActionPlacement,
        *,
        unregistered: bool = False,
    ) -> None:
        """Remove a placement for an action.

        This will remove a placement as part of either unregistering an
        action or from removing or re-deferring a parent placement.

        The placement will be removed from the parent placement and from
        lookup tables. All child actions in the placement will be removed.

        Removed actions are put back into a deferred state so they can be
        placed again later if the parent placement is re-added.

        Args:
            action (reviewboard.actions.base.BaseAction):
                The action for the placement.

            placement (reviewboard.actions.base.ActionPlacement):
                The placement being removed.

            unregistered (bool, optional):
                Whether the action is being explicitly unregistered.
        """
        action_id = action.action_id
        by_attachment_point = self._by_attachment_point

        attachment = placement.attachment
        attachment_actions = by_attachment_point[attachment]
        deferred_placements = self._deferred_placements

        # Remove placements for any children that depend on this placement
        # so they can be re-added if this action is registered again.
        if placement.child_actions:
            for child_action in list(placement.child_actions):
                child_placement = child_action.get_placement(attachment)

                if child_placement:
                    self._remove_placement(child_action, child_placement)
        else:
            # If nothing depends on this placement, we can remove it from
            # the deferment list if present.
            deferred_placements.pop((action_id, attachment), None)

        # If this placement is parented to another (whether it currently
        # exists in the registry or not), it may need to be deferred or
        # removed from a deferred list.
        if (parent_id := placement.parent_id):
            defer_key = (parent_id, attachment)

            if not unregistered:
                deferred_placements[defer_key][action_id] = action
            elif not placement.child_actions:
                # This action is being unregistered, and it has a parent but
                # no child actions. This means it can be safely removed from
                # any deferred list, since adding a parent action back to
                # the registry would not need to place this again.
                if defer_key in deferred_placements:
                    deferred_placements[defer_key].pop(action_id, None)

                    if not deferred_placements[defer_key]:
                        # There are no more deferred placements for this
                        # parent and attachment, so delete its entry.
                        del deferred_placements[defer_key]

        # If this placement is parented to another, remove it from that
        # placement's list of children.
        if (parent_action := placement.parent_action):
            parent_placement = parent_action.get_placement(attachment)

            if parent_placement is not None:
                parent_placement.child_actions.remove(action)

            placement.parent_action = None

        # Remove this from the per-attachment lookups.
        #
        # Note that it may not be in this list, because we remove this both
        # when processing children of an unregistered action and when
        # processing the unregistered action itself. We can end up here
        # multiple times when tearing down multiple actions, such as during
        # extension shutdown or registry reset.
        attachment_actions.pop(action_id, None)

        # Clear out this attachment point lookup if there are no longer
        # any actions left.
        if not attachment_actions:
            del by_attachment_point[attachment]
