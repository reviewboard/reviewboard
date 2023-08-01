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
from reviewboard.actions import (AttachmentPoint,
                                 BaseAction,
                                 BaseMenuAction)


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


class AccountMenuAction(LoggedInUserMixin, BaseMenuAction):
    """A menu for account-related actions.

    Version Added:
        6.0
    """

    action_id = 'account-menu'
    attachment = AttachmentPoint.HEADER
    label = ''
    template_name = 'accounts/account_menu_action.html'


class LoginAction(BaseAction):
    """Action for logging in.

    Version Added:
        6.0
    """

    action_id = 'login'
    label = _('Log in')
    attachment = AttachmentPoint.HEADER

    def get_url(
        self,
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
    parent_id = 'account-menu'
    label = _('Log out')
    attachment = AttachmentPoint.HEADER
    url_name = 'logout'


class AdminAction(BaseAction):
    """Action for the "Admin" page.

    Version Added:
        6.0
    """

    action_id = 'admin'
    parent_id = 'account-menu'
    label = _('Admin')
    attachment = AttachmentPoint.HEADER
    url_name = 'admin-dashboard'

    def should_render(
        self,
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
    parent_id = 'account-menu'
    label = _('My account')
    attachment = AttachmentPoint.HEADER
    url_name = 'user-preferences'


class SupportMenuAction(BaseMenuAction):
    """A menu for support options.

    Version Added:
        6.0
    """

    action_id = 'support-menu'
    label = _('Support')
    attachment = AttachmentPoint.HEADER


class DocumentationAction(BaseAction):
    """Action for accessing Review Board documentation.

    Version Added:
        6.0
    """

    action_id = 'documentation'
    parent_id = 'support-menu'
    label = _('Documentation')
    attachment = AttachmentPoint.HEADER

    def get_url(
        self,
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
    parent_id = 'support-menu'
    label = _('Get Support')
    attachment = AttachmentPoint.HEADER
    url_name = 'support'


class FollowMenuAction(BaseMenuAction):
    """A menu for follow options.

    Version Added:
        6.0
    """

    action_id = 'follow-menu'
    label = _('Follow')
    attachment = AttachmentPoint.HEADER

    def should_render(
        self,
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
    parent_id = 'follow-menu'
    label = _('Review Board News')
    icon_class = 'fa fa-rss'
    url = 'https://www.reviewboard.org/news/'
    attachment = AttachmentPoint.HEADER


class FollowTwitterAction(BaseAction):
    """Action for following via Twitter.

    Version Added:
        6.0
    """

    action_id = 'follow-twitter'
    parent_id = 'follow-menu'
    label = _('Twitter')
    icon_class = 'fa fa-twitter'
    url = 'https://twitter.com/reviewboard/'
    attachment = AttachmentPoint.HEADER


class FollowFacebookAction(BaseAction):
    """Action for following via Facebook.

    Version Added:
        6.0
    """

    action_id = 'follow-facebook'
    parent_id = 'follow-menu'
    label = _('Facebook')
    icon_class = 'fa fa-facebook'
    url = 'https://facebook.com/reviewboard.org'
    attachment = AttachmentPoint.HEADER


class FollowRedditAction(BaseAction):
    """Action for following via Reddit.

    Version Added:
        6.0
    """

    action_id = 'follow-reddit'
    parent_id = 'follow-menu'
    label = _('Reddit')
    icon_class = 'fa fa-reddit'
    url = 'https://reddit.com/r/reviewboard'
    attachment = AttachmentPoint.HEADER


class FollowYouTubeAction(BaseAction):
    """Action for following via YouTube.

    Version Added:
        6.0
    """

    action_id = 'follow-youtube'
    parent_id = 'follow-menu'
    label = _('YouTube')
    icon_class = 'fa fa-youtube'
    url = 'https://www.youtube.com/channel/UCTnwzlRTtx8wQOmyXiA_iCg'
    attachment = AttachmentPoint.HEADER
