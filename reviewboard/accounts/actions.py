"""Built-in actions for the accounts app.

Version Added:
    6.0
"""

from typing import TYPE_CHECKING

from django.conf import settings
from django.template import Context
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from reviewboard import get_manual_url
from reviewboard.actions import (ActionPlacement,
                                 AttachmentPoint,
                                 BaseAction,
                                 BaseMenuAction)
from reviewboard.actions.renderers import MenuActionGroupRenderer


if TYPE_CHECKING:
    MixinParent = BaseAction
else:
    MixinParent = object


class LoggedInUserMixin(MixinParent):
    """Mixin for actions that only render for logged-in users.

    Version Added:
        6.0
    """

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']
        return (super().should_render(context=context) and
                request.user.is_authenticated)


class AccountMenuActionRenderer(MenuActionGroupRenderer):
    """Action renderer for the My Account menu.

    This provides a custom template used to render the menu for display
    in the page header, using the username and avatar.

    Version Added:
        7.1
    """

    template_name = 'accounts/account_menu_action.html'


class AccountMenuAction(LoggedInUserMixin, BaseMenuAction):
    """A menu for account-related actions.

    Version Added:
        6.0
    """

    action_id = 'account-menu'
    default_renderer_cls = AccountMenuActionRenderer
    label = ''

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER),
    ]


class LoginAction(BaseAction):
    """Action for logging in.

    Version Added:
        6.0
    """

    action_id = 'login'
    label = _('Log in')

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER),
    ]

    def get_url(
        self,
        *,
        context: Context,
    ) -> str:
        """Return the URL for the action.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            str:
            The URL to use for the action.
        """
        request = context['request']
        return '%s?next=%s' % (reverse('login'), request.path)

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']
        return (super().should_render(context=context) and
                not request.user.is_authenticated)


class LogoutAction(LoggedInUserMixin, BaseAction):
    """Action for logging out.

    Version Added:
        6.0
    """

    action_id = 'logout'
    label = _('Log out')
    url_name = 'logout'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=AccountMenuAction.action_id),
    ]


class AdminAction(BaseAction):
    """Action for the "Admin" page.

    Version Added:
        6.0
    """

    action_id = 'admin'
    label = _('Admin')
    url_name = 'admin-dashboard'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=AccountMenuAction.action_id),
    ]

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        request = context['request']
        return (super().should_render(context=context) and
                request.user.is_staff)


class MyAccountAction(LoggedInUserMixin, BaseAction):
    """Action for the "My Account" page.

    Version Added:
        6.0
    """

    action_id = 'my-account'
    label = _('My account')
    url_name = 'user-preferences'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=AccountMenuAction.action_id),
    ]


class SupportMenuAction(BaseMenuAction):
    """A menu for support options.

    Version Added:
        6.0
    """

    action_id = 'support-menu'
    label = _('Support')

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER),
    ]


class DocumentationAction(BaseAction):
    """Action for accessing Review Board documentation.

    Version Added:
        6.0
    """

    action_id = 'documentation'
    label = _('Documentation')

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=SupportMenuAction.action_id),
    ]

    def get_url(
        self,
        *,
        context: Context,
    ) -> str:
        """Return the URL for the action.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            str:
            The URL to use for the action.
        """
        return get_manual_url()


class SupportAction(BaseAction):
    """Action for linking to support.

    Version Added:
        6.0
    """

    action_id = 'support'
    label = _('Get Support')
    url_name = 'support'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=SupportMenuAction.action_id),
    ]


class FollowMenuAction(BaseMenuAction):
    """A menu for follow options.

    Version Added:
        6.0
    """

    action_id = 'follow-menu'
    label = _('Follow')

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER),
    ]

    def should_render(
        self,
        *,
        context: Context,
    ) -> bool:
        """Return whether this action should render.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            bool:
            ``True`` if the action should render.
        """
        return (super().should_render(context=context) and
                not getattr(settings, 'DISABLE_FOLLOW_MENU', False))


class FollowNewsAction(BaseAction):
    """Action for following via News.

    Version Added:
        6.0
    """

    action_id = 'follow-rss'
    label = _('Review Board News')
    icon_class = 'rb-icon-rss'
    url = 'https://www.reviewboard.org/news/'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=FollowMenuAction.action_id),
    ]


class FollowBlueSkyAction(BaseAction):
    """Action for following via BlueSky.

    Version Added:
        7.0
    """

    action_id = 'follow-bluesky'
    label = _('BlueSky')
    icon_class = 'rb-icon-brand-bluesky'
    url = 'https://bsky.app/profile/reviewboard.bsky.social'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=FollowMenuAction.action_id),
    ]


class FollowLinkedInAction(BaseAction):
    """Action for following via LinkedIn.

    Version Added:
        7.0
    """

    action_id = 'follow-linkedin'
    label = _('LinkedIn')
    icon_class = 'rb-icon-brand-linkedin'
    url = 'https://www.linkedin.com/company/reviewboard/'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=FollowMenuAction.action_id),
    ]


class FollowMastodonAction(BaseAction):
    """Action for following via Mastodon.

    Version Added:
        7.0
    """

    action_id = 'follow-mastodon'
    label = _('Mastodon')
    icon_class = 'rb-icon-brand-mastodon'
    url = 'https://mastodon.online/@reviewboard'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=FollowMenuAction.action_id),
    ]


class FollowTwitterAction(BaseAction):
    """Action for following via Twitter.

    Version Added:
        6.0
    """

    action_id = 'follow-twitter'
    label = _('Twitter')
    icon_class = 'rb-icon-brand-twitter'
    url = 'https://twitter.com/reviewboard/'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=FollowMenuAction.action_id),
    ]


class FollowFacebookAction(BaseAction):
    """Action for following via Facebook.

    Version Added:
        6.0
    """

    action_id = 'follow-facebook'
    label = _('Facebook')
    icon_class = 'rb-icon-brand-facebook'
    url = 'https://facebook.com/reviewboard.org'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=FollowMenuAction.action_id),
    ]


class FollowRedditAction(BaseAction):
    """Action for following via Reddit.

    Version Added:
        6.0
    """

    action_id = 'follow-reddit'
    label = _('Reddit')
    icon_class = 'rb-icon-brand-reddit'
    url = 'https://reddit.com/r/reviewboard'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=FollowMenuAction.action_id),
    ]


class FollowYouTubeAction(BaseAction):
    """Action for following via YouTube.

    Version Added:
        6.0
    """

    action_id = 'follow-youtube'
    label = _('YouTube')
    icon_class = 'rb-icon-brand-youtube'
    url = 'https://www.youtube.com/channel/UCTnwzlRTtx8wQOmyXiA_iCg'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=FollowMenuAction.action_id),
    ]
