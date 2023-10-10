"""Actions for the reviews app."""

from __future__ import annotations

from typing import Iterable, List, Optional, TYPE_CHECKING, Union

from django.http import HttpRequest
from django.template import Context
from django.utils.translation import gettext_lazy as _

from reviewboard.actions import (AttachmentPoint,
                                 BaseAction,
                                 BaseMenuAction,
                                 actions_registry)
from reviewboard.admin.read_only import is_site_read_only_for
from reviewboard.deprecation import RemovedInReviewBoard70Warning
from reviewboard.reviews.features import (general_comments_feature,
                                          unified_banner_feature)
from reviewboard.reviews.models import ReviewRequest
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.urls import reviewable_url_names, review_request_url_names

if TYPE_CHECKING:
    # This is available only in django-stubs.
    from django.utils.functional import _StrOrPromise


all_review_request_url_names = reviewable_url_names + review_request_url_names


class CloseMenuAction(BaseMenuAction):
    """A menu for closing the review request.

    Version Added:
        6.0
    """

    action_id = 'close-menu'
    label = _('Close')
    apply_to = all_review_request_url_names

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This differs from :py:attr:`hidden` in that hidden actions still render
        but are hidden by CSS, whereas if this returns ``False`` the action
        will not be included in the DOM at all.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']
        review_request = context.get('review_request')
        perms = context.get('perms')
        user = request.user

        return (super().should_render(context=context) and
                review_request is not None and
                review_request.status == ReviewRequest.PENDING_REVIEW and
                not is_site_read_only_for(user) and
                (request.user.pk == review_request.submitter_id or
                (bool(perms) and
                 perms['reviews']['can_change_status'] and
                 review_request.public)))


class CloseCompletedAction(BaseAction):
    """The action to close a review request as completed.

    Version Added:
        6.0
    """

    action_id = 'close-completed'
    parent_id = CloseMenuAction.action_id
    label = _('Completed')
    apply_to = all_review_request_url_names
    js_view_class = 'RB.CloseCompletedActionView'

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This differs from :py:attr:`hidden` in that hidden actions still render
        but are hidden by CSS, whereas if this returns ``False`` the action
        will not be included in the DOM at all.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        review_request = context.get('review_request')

        return (super().should_render(context=context) and
                review_request is not None and
                review_request.public and
                not is_site_read_only_for(context['request'].user))


class CloseDiscardedAction(BaseAction):
    """The action to close a review request as discarded.

    Version Added:
        6.0
    """

    action_id = 'close-discarded'
    parent_id = CloseMenuAction.action_id
    label = _('Discarded')
    apply_to = all_review_request_url_names
    js_view_class = 'RB.CloseDiscardedActionView'


class DeleteAction(BaseAction):
    """The action to permanently delete a review request.

    Version Added:
        6.0
    """

    action_id = 'delete-review-request'
    parent_id = CloseMenuAction.action_id
    label = _('Delete Permanently')
    apply_to = all_review_request_url_names
    js_view_class = 'RB.DeleteActionView'

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This differs from :py:attr:`hidden` in that hidden actions still render
        but are hidden by CSS, whereas if this returns ``False`` the action
        will not be included in the DOM at all.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        perms = context.get('perms')

        return (super().should_render(context=context) and
                bool(perms) and
                perms['reviews']['delete_reviewrequest'] and
                not is_site_read_only_for(context['request'].user))


class DownloadDiffAction(BaseAction):
    """The action to download a diff.

    Version Added:
        6.0
    """

    action_id = 'download-diff'
    label = _('Download Diff')
    apply_to = all_review_request_url_names

    def get_url(
        self,
        *,
        context: Context,
    ) -> str:
        """Return this action's URL.

        Args:
            context (django.template.Context):
                The collection of key-value pairs from the template.

        Returns:
            str:
            The URL to invoke if this action is clicked.
        """
        # We want to use a relative URL in the diff viewer as we will not be
        # re-rendering the page when switching between revisions.
        from reviewboard.urls import diffviewer_url_names

        request: HttpRequest = context['request']
        match = request.resolver_match

        if match and match.url_name in diffviewer_url_names:
            return 'raw/'

        return local_site_reverse(
            'raw-diff',
            request,
            kwargs={
                'review_request_id': context['review_request'].display_id,
            })

    def get_visible(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether the action should start visible or not.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should start visible. ``False``, otherwise.
        """
        from reviewboard.urls import diffviewer_url_names

        request: HttpRequest = context['request']
        match = request.resolver_match

        if match and match.url_name in diffviewer_url_names:
            return match.url_name != 'view-interdiff'

        return super().get_visible(context=context)

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This differs from :py:attr:`hidden` in that hidden actions still render
        but are hidden by CSS, whereas if this returns ``False`` the action
        will not be included in the DOM at all.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        from reviewboard.urls import diffviewer_url_names

        request: HttpRequest = context['request']
        match = request.resolver_match

        # If we're on a diff viewer page, then this should be initially
        # rendered, but might be hidden.
        if match and match.url_name in diffviewer_url_names:
            return True

        review_request = context.get('review_request')

        return (super().should_render(context=context) and
                review_request is not None and
                review_request.has_diffsets)


class ReviewMenuAction(BaseMenuAction):
    """The "Review" menu on the unified banner.

    Version Added:
        6.0
    """

    action_id = 'review-menu'
    apply_to = all_review_request_url_names
    attachment = AttachmentPoint.UNIFIED_BANNER
    label = _('Review')
    icon_class = 'rb-icon rb-icon-compose-review'
    js_view_class = 'RB.ReviewMenuActionView'

    def should_render(
        self,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This menu only renders when the user is logged in and the unified
        banner feature is enabled.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']
        user = request.user

        return (super().should_render(context=context) and
                user.is_authenticated and
                not is_site_read_only_for(user) and
                unified_banner_feature.is_enabled(request=request))


class CreateReviewAction(BaseAction):
    """Action to create a new, blank review.

    Version Added:
        6.0
    """

    action_id = 'create-review'
    parent_id = 'review-menu'
    apply_to = all_review_request_url_names
    attachment = AttachmentPoint.UNIFIED_BANNER
    label = _('Create a new review')
    description = [
        _('Your review will start off blank, but you can add text and '
          'general comments to it.'),
        _('Adding comments to code or file attachments will automatically '
          'create a new review for you.'),
    ]
    icon_class = 'rb-icon rb-icon-create-review'
    js_view_class = 'RB.CreateReviewActionView'
    template_name = 'actions/detailed_menuitem_action.html'


class EditReviewAction(BaseAction):
    """Action to edit an existing review.

    Version Added:
        6.0
    """

    action_id = 'edit-review'
    parent_id = 'review-menu'
    apply_to = all_review_request_url_names
    attachment = AttachmentPoint.UNIFIED_BANNER
    label = _('Edit your review')
    description = [
        _('Edit your comments and publish your review.'),
    ]
    icon_class = 'rb-icon rb-icon-compose-review'
    js_view_class = 'RB.EditReviewActionView'
    template_name = 'actions/detailed_menuitem_action.html'


class AddGeneralCommentAction(BaseAction):
    """Action to add a general comment.

    Version Added:
        6.0
    """

    action_id = 'add-general-comment'
    parent_id = 'review-menu'
    apply_to = all_review_request_url_names
    attachment = AttachmentPoint.UNIFIED_BANNER
    label = _('Add a general comment')
    description = [
        _('Add a new general comment about the change, not attached to '
          'any code or file attachments.'),
    ]
    icon_class = 'rb-icon rb-icon-edit'
    js_view_class = 'RB.AddGeneralCommentActionView'
    template_name = 'actions/detailed_menuitem_action.html'


class ShipItAction(BaseAction):
    """Action to mark a review request as "Ship It".

    Version Added:
        6.0
    """

    action_id = 'ship-it'
    parent_id = 'review-menu'
    apply_to = all_review_request_url_names
    attachment = AttachmentPoint.UNIFIED_BANNER
    label = _('Ship it!')
    description = [
        _("You're happy with what you're seeing, and would like to "
          'approve it.'),
        _('If you want to leave a comment with this, choose "Create '
          'a new review" above.'),
    ]
    icon_class = 'rb-icon rb-icon-shipit'
    js_view_class = 'RB.ShipItActionView'
    template_name = 'actions/detailed_menuitem_action.html'


class LegacyAddGeneralCommentAction(BaseAction):
    """The action for adding a general comment.

    Version Added:
        6.0
    """

    action_id = 'legacy-add-general-comment'
    label = _('Add General Comment')
    apply_to = all_review_request_url_names

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This differs from :py:attr:`hidden` in that hidden actions still render
        but are hidden by CSS, whereas if this returns ``False`` the action
        will not be included in the DOM at all.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']
        user = request.user

        return (super().should_render(context=context) and
                user.is_authenticated and
                not is_site_read_only_for(user) and
                general_comments_feature.is_enabled(request=request) and
                not unified_banner_feature.is_enabled(request=request))


class LegacyEditReviewAction(BaseAction):
    """The old-style "Edit Review" action.

    This exists within the review request actions area, and will be supplanted
    by the new action in the Review menu in the unified banner.

    Version Added:
        6.0
    """

    action_id = 'legacy-edit-review'
    label = _('Review')
    apply_to = all_review_request_url_names

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This differs from :py:attr:`hidden` in that hidden actions still render
        but are hidden by CSS, whereas if this returns ``False`` the action
        will not be included in the DOM at all.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']
        user = request.user

        return (super().should_render(context=context) and
                user.is_authenticated and
                not is_site_read_only_for(user) and
                not unified_banner_feature.is_enabled(request=request))


class LegacyShipItAction(BaseAction):
    """The old-style "Ship It" action.

    This exists within the review request actions area, and will be supplanted
    by the new action in the Review menu in the unified banner.

    Version Added:
        6.0
    """

    action_id = 'legacy-ship-it'
    label = _('Ship It!')
    apply_to = all_review_request_url_names

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This differs from :py:attr:`hidden` in that hidden actions still render
        but are hidden by CSS, whereas if this returns ``False`` the action
        will not be included in the DOM at all.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']
        user = request.user

        return (super().should_render(context=context) and
                user.is_authenticated and
                not is_site_read_only_for(user) and
                not unified_banner_feature.is_enabled(request=request))


class UpdateMenuAction(BaseMenuAction):
    """A menu for updating the review request.

    Version Added:
        6.0
    """

    action_id = 'update-menu'
    label = _('Update')
    apply_to = all_review_request_url_names

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This differs from :py:attr:`hidden` in that hidden actions still render
        but are hidden by CSS, whereas if this returns ``False`` the action
        will not be included in the DOM at all.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']
        review_request = context.get('review_request')
        perms = context.get('perms')
        user = request.user

        return (super().should_render(context=context) and
                review_request is not None and
                review_request.status == ReviewRequest.PENDING_REVIEW and
                not is_site_read_only_for(user) and
                (user.pk == review_request.submitter_id or
                (bool(perms) and perms['reviews']['can_edit_reviewrequest'])))


class UploadDiffAction(BaseAction):
    """The action to update or upload a diff.

    Version Added:
        6.0
    """

    action_id = 'upload-diff'
    parent_id = UpdateMenuAction.action_id
    apply_to = all_review_request_url_names
    js_view_class = 'RB.UpdateDiffActionView'

    def get_label(
        self,
        *,
        context: Context,
    ) -> _StrOrPromise:
        """Return the label for the action.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            str:
            The label to use for the action.
        """
        review_request = context['review_request']
        draft = review_request.get_draft(context['request'].user)

        if (draft and draft.diffset) or review_request.has_diffsets:
            return _('Update Diff')
        else:
            return _('Upload Diff')

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This differs from :py:attr:`hidden` in that hidden actions still render
        but are hidden by CSS, whereas if this returns ``False`` the action
        will not be included in the DOM at all.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']
        review_request = context.get('review_request')
        perms = context.get('perms')
        user = request.user

        return (super().should_render(context=context) and
                review_request is not None and
                review_request.repository_id is not None and
                not is_site_read_only_for(user) and
                (user.pk == review_request.submitter_id or
                 (bool(perms) and
                  perms['reviews']['can_edit_reviewrequest'])))


class UploadFileAction(BaseAction):
    """The action to upload a new file attachment.

    Version Added:
        6.0
    """

    action_id = 'upload-file'
    parent_id = UpdateMenuAction.action_id
    label = _('Add File')
    apply_to = all_review_request_url_names
    js_view_class = 'RB.AddFileActionView'

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This differs from :py:attr:`hidden` in that hidden actions still render
        but are hidden by CSS, whereas if this returns ``False`` the action
        will not be included in the DOM at all.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']
        review_request = context.get('review_request')
        perms = context.get('perms')
        user = request.user

        return (super().should_render(context=context) and
                review_request is not None and
                review_request.status == ReviewRequest.PENDING_REVIEW and
                not is_site_read_only_for(user) and
                (user.pk == review_request.submitter_id or
                 (bool(perms) and
                  perms['reviews']['can_edit_reviewrequest'])))


class StarAction(BaseAction):
    """The action to star a review request.

    Version Added:
        6.0
    """

    action_id = 'star-review-request'
    attachment = AttachmentPoint.REVIEW_REQUEST_LEFT
    label = ''
    template_name = 'reviews/star_action.html'
    apply_to = all_review_request_url_names

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This differs from :py:attr:`hidden` in that hidden actions still render
        but are hidden by CSS, whereas if this returns ``False`` the action
        will not be included in the DOM at all.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']
        review_request = context.get('review_request')
        user = request.user

        return (user.is_authenticated and
                review_request is not None and
                review_request.public and
                not is_site_read_only_for(user) and
                super().should_render(context=context))


class ArchiveMenuAction(BaseMenuAction):
    """A menu for managing the visibility state of the review request.

    Version Added:
        6.0
    """

    action_id = 'archive-menu'
    attachment = AttachmentPoint.REVIEW_REQUEST_LEFT
    label = ''
    template_name = 'reviews/archive_menu_action.html'
    js_view_class = 'RB.ArchiveMenuActionView'
    apply_to = all_review_request_url_names

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        This differs from :py:attr:`hidden` in that hidden actions still render
        but are hidden by CSS, whereas if this returns ``False`` the action
        will not be included in the DOM at all.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']
        review_request = context.get('review_request')
        user = request.user

        return (user.is_authenticated and
                review_request is not None and
                review_request.public and
                not is_site_read_only_for(user) and
                super().should_render(context=context))


class ArchiveAction(BaseAction):
    """An action for archiving the review request.

    Version Added:
        6.0
    """

    action_id = 'archive'
    parent_id = ArchiveMenuAction.action_id
    attachment = AttachmentPoint.REVIEW_REQUEST_LEFT
    apply_to = all_review_request_url_names
    label = ''
    template_name = 'reviews/archive_action.html'
    js_view_class = 'RB.ArchiveActionView'


class MuteAction(BaseAction):
    """An action for muting the review request.

    Version Added:
        6.0
    """

    action_id = 'mute'
    parent_id = ArchiveMenuAction.action_id
    attachment = AttachmentPoint.REVIEW_REQUEST_LEFT
    apply_to = all_review_request_url_names
    label = ''
    template_name = 'reviews/archive_action.html'
    js_view_class = 'RB.MuteActionView'


class BaseReviewRequestAction(BaseAction):
    """A base class for an action that can be applied to a review request.

    Creating an action requires subclassing :py:class:`BaseReviewRequestAction`
    and overriding any fields/methods as desired. Different instances of the
    same subclass can also override the class fields with their own instance
    fields.

    Example:
        .. code-block:: python

           class UsedOnceAction(BaseReviewRequestAction):
               action_id = 'once'
               label = 'This is used once.'

           class UsedMultipleAction(BaseReviewRequestAction):
               def __init__(self, action_id, label):
                   super().__init__()

                   self.action_id = 'repeat-' + action_id
                   self.label = 'This is used multiple times,'

    Note:
        Since the same action will be rendered for multiple different users in
        a multithreaded environment, the action state should not be modified
        after initialization. If we want different action attributes at
        runtime, then we can override one of the getter methods (such as
        :py:meth:`get_label`), which by default will simply return the original
        attribute from initialization.

    Deprecated:
        6.0:
        New code should be written using
        :py:class:`reviewboard.actions.base.BaseAction`. This class will be
        removed in 7.0.
    """

    apply_to = all_review_request_url_names

    def __init__(self) -> None:
        """Initialize this action.

        By default, actions are top-level and have no children.
        """
        RemovedInReviewBoard70Warning.warn(
            'BaseReviewRequestAction is deprecated and will be removed in '
            'Review Board 7.0. Please update your code to use '
            'reviewboard.actions.base.BaseAction')

        super().__init__()
        self._parent = None

    @property
    def max_depth(self) -> int:
        """Lazily compute the max depth of any action contained by this action.

        Top-level actions have a depth of zero, and child actions have a depth
        that is one more than their parent action's depth.

        Algorithmically, the notion of max depth is equivalent to the notion of
        height in the context of trees (from graph theory). We decided to use
        this term instead so as not to confuse it with the dimensional height
        of a UI element.

        Returns:
            int:
            The max depth of any action contained by this action.
        """
        return 0

    def reset_max_depth(self) -> None:
        """Reset the max_depth of this action and all its ancestors to zero."""
        # The max depth is now calculated on the fly, so this is a no-op.
        pass

    def get_extra_context(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> dict:
        """Return extra template context for the action.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            Extra context to use when rendering the action's template.
        """
        data = super().get_extra_context(request=request, context=context)

        if self.template_name != 'actions/action.html':
            data['action'] = self.copy_to_dict(context)

        return data

    def copy_to_dict(
        self,
        context: Context,
    ) -> dict:
        """Copy this action instance to a dictionary.

        This is a legacy implementation left to maintain compatibility with
        custom templates.
        """
        return {
            'action_id': self.action_id,
            'hidden': not self.get_visible(context=context),
            'label': self.get_label(context=context),
            'url': self.get_url(context=context),
        }

    def register(
        self,
        parent: Optional[BaseReviewRequestMenuAction] = None,
    ) -> None:
        """Register this review request action instance.

        Note:
           Newly registered top-level actions are appended to the left of the
           other previously registered top-level actions. So if we intend to
           register a collection of top-level actions in a certain order, then
           we likely want to iterate through the actions in reverse.

        Args:
            parent (BaseReviewRequestMenuAction, optional):
                The parent action instance of this action instance.

        Raises:
            KeyError:
                A second registration is attempted (action IDs must be unique
                across all types of actions and menu actions, at any depth).

            DepthLimitExceededError:
                The maximum depth limit is exceeded.
        """
        if parent:
            self.parent_id = parent.action_id

        actions_registry.register(self)

    def unregister(self) -> None:
        """Unregister this review request action instance.

        Note:
           This method can mutate its parent's child actions. So if we are
           iteratively unregistering a parent's child actions, then we should
           consider first making a clone of the list of children.

        Raises:
            KeyError:
                An unregistration is attempted before it's registered.
        """
        actions_registry.unregister(self)


class BaseReviewRequestMenuAction(BaseMenuAction):
    """A base class for an action with a dropdown menu.

    Deprecated:
        6.0:
        New code should be written using
        :py:class:`reviewboard.actions.base.BaseMenuAction`. This class will be
        removed in 7.0.
    """

    apply_to = all_review_request_url_names

    def __init__(
        self,
        child_actions: Optional[List[BaseReviewRequestAction]] = None,
    ) -> None:
        """Initialize this menu action.

        Args:
            child_actions (list of BaseReviewRequestAction, optional):
                The list of child actions to be contained by this menu action.

        Raises:
            KeyError:
                A second registration is attempted (action IDs must be unique
                across all types of actions and menu actions, at any depth).

            DepthLimitExceededError:
                The maximum depth limit is exceeded.
        """
        super().__init__()

        self._children = child_actions or []

    def copy_to_dict(
        self,
        context: Context,
    ) -> dict:
        """Copy this menu action instance to a dictionary.

        This is a legacy implementation left to maintain compatibility with
        custom templates.

        Args:
            context (django.template.Context):
                The collection of key-value pairs from the template.

        Returns:
            dict:
            The corresponding dictionary.
        """
        return {
            'action_id': self.action_id,
            'child_actions': self.child_actions,
            'hidden': not self.get_visible(context=context),
            'label': self.get_label(context=context),
            'url': self.get_url(context=context),
        }

    def get_extra_context(
        self,
        *,
        request: HttpRequest,
        context: Context,
    ) -> dict:
        """Return extra template context for the action.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            Extra context to use when rendering the action's template.
        """
        data = super().get_extra_context(request=request, context=context)

        if self.template_name != 'actions/menu_action.html':
            data['menu_action'] = self.copy_to_dict(context)

        return data

    @property
    def max_depth(self) -> int:
        """Lazily compute the max depth of any action contained by this action.

        Returns:
            int: The max depth of any action contained by this action.
        """
        if self.child_actions:
            return max(child_action.max_depth
                       for child_action in self.child_actions)
        else:
            return self.depth

    def register(
        self,
        parent: Optional[BaseReviewRequestMenuAction] = None,
    ) -> None:
        """Register this review request action instance.

        Note:
           Newly registered top-level actions are appended to the left of the
           other previously registered top-level actions. So if we intend to
           register a collection of top-level actions in a certain order, then
           we likely want to iterate through the actions in reverse.

        Args:
            parent (BaseReviewRequestMenuAction, optional):
                The parent action instance of this action instance.

        Raises:
            KeyError:
                A second registration is attempted (action IDs must be unique
                across all types of actions and menu actions, at any depth).

            DepthLimitExceededError:
                The maximum depth limit is exceeded.
        """
        if parent:
            self.parent_id = parent.action_id

        actions_registry.register(self)

        for child in self._children:
            child.parent_id = self.action_id
            child.register()

    def unregister(self) -> None:
        """Unregister this review request action instance.

        This menu action recursively unregisters its child action instances.

        Raises:
            KeyError: An unregistration is attempted before it's registered.
        """
        for child in self._children:
            child.unregister()

        actions_registry.unregister(self)


def register_actions(
    actions: List[Union[BaseReviewRequestAction, BaseReviewRequestMenuAction]],
    parent_id: Optional[str] = None,
) -> None:
    """Register the given actions as children of the corresponding parent.

    If no parent_id is given, then the actions are assumed to be top-level.

    Deprecated:
        6.0:
        Users should switch to
        :py:const:`reviewboard.actions.actions_registry`. This method will be
        removed in Review Board 7.

    Args:
        actions (iterable of BaseReviewRequestAction):
            The collection of action instances to be registered.

        parent_id (unicode, optional):
            The action ID of the parent of each action instance to be
            registered.

    Raises:
        KeyError:
            The parent action cannot be found or a second registration is
            attempted (action IDs must be unique across all types of actions
            and menu actions, at any depth).

        DepthLimitExceededError:
            The maximum depth limit is exceeded.
    """
    RemovedInReviewBoard70Warning.warn(
        'register_actions has been deprecated and will be removed in '
        'Review Board 7.0. Please update your code to use '
        'reviewboard.actions.actions_registry.')

    if parent_id:
        parent = actions_registry.get('action_id', parent_id)
    else:
        parent = None

    for action in actions:
        action.register(parent)


def unregister_actions(
    action_ids: Iterable[str],
) -> None:
    """Unregister each of the actions corresponding to the given IDs.

    Deprecated:
        6.0:
        Users should switch to
        :py:const:`reviewboard.actions.actions_registry`. This method will be
        removed in Review Board 7.

    Args:
        action_ids (iterable of unicode):
            The collection of action IDs corresponding to the actions to be
            removed.

    Raises:
        KeyError:
            An unregistration is attempted before it's registered.
    """
    RemovedInReviewBoard70Warning.warn(
        'unregister_actions has been deprecated and will be removed in '
        'Review Board 7.0. Please update your code to use '
        'reviewboard.actions.actions_registry.')

    for action_id in action_ids:
        action = actions_registry.get('action_id', action_id)
        action.unregister()


def clear_all_actions() -> None:
    """Clear all registered actions.

    This method is really only intended to be used by unit tests. We might be
    able to remove this hack once we convert to djblets.registries.

    Deprecated:
        6.0:
        Users should switch to
        :py:const:`reviewboard.actions.actions_registry`. This method will be
        removed in Review Board 7.

    Warning:
        This will clear **all** actions, even if they were registered in
        separate extensions.
    """
    RemovedInReviewBoard70Warning.warn(
        'clear_all_actions has been deprecated and will be removed in '
        'Review Board 7.0. Please update your code to use '
        'reviewboard.actions.actions_registry.')
    actions_registry.reset()
