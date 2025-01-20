"""Account-related template tags."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterator, TYPE_CHECKING

import pytz
from django import template
from django.contrib.auth.models import User
from django.utils import dateformat, timezone
from django.utils.html import escape, format_html, format_html_join
from django.utils.safestring import SafeString, mark_safe
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.templatetags.djblets_js import json_dumps

from reviewboard.accounts.user_details import user_details_provider_registry
from reviewboard.admin.read_only import is_site_read_only_for
from reviewboard.avatars import avatar_services
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from django.template.context import Context


logger = logging.getLogger(__name__)
register = template.Library()


@register.simple_tag(takes_context=True)
def user_profile_display_name(context, user):
    """Render the user's display name.

    Args:
        context (django.template.context.Context):
            The template rendering context.

        user (django.contrib.auth.models.User):
            The user whose display name is to be rendered.

    Returns:
        unicode:
        The user's display name.
    """
    request = context['request']

    if request is not None:
        request_user = request.user
    else:
        request_user = None

    return escape(user.get_profile().get_display_name(request_user))


@register.simple_tag(takes_context=True)
def js_user_session_info(context):
    """Return JSON-serialized data for a new RB.UserSession instance.

    This is used on all Review Board pages to construct the attributes
    passed to :js:class:`RB.UserSession`. This contains information on the user
    and their authentication state, important API URLs that need to be
    accessed, timezone information, avatar URLs, and various user preferences.

    Args:
        context (django.template.Context):
            The current template context.

    Returns:
        django.utils.safestring.SafeText:
        The JSON-serialized attribute data.
    """
    request = context['request']
    user = request.user
    authenticated = user.is_authenticated

    info = {
        'authenticated': authenticated,
    }

    if authenticated:
        # Authenticated users.
        siteconfig = SiteConfiguration.objects.get_current()
        profile = request.user.get_profile()
        username = user.username
        avatar_urls = {}
        avatar_html = {}

        info.update({
            'allowSelfShipIt': siteconfig.get('reviews_allow_self_shipit'),
            'fullName': user.get_full_name() or username,
            'readOnly': is_site_read_only_for(user),
            'username': username,
        })

        # Inject some URLs needed to manage some user state.
        info['sessionURL'] = local_site_reverse('session-resource',
                                                request=request)

        for key, url_name in (('archivedReviewRequestsURL',
                               'archived-review-requests-resource'),
                              ('mutedReviewRequestsURL',
                               'muted-review-requests-resource'),
                              ('userFileAttachmentsURL',
                               'user-file-attachments-resource'),
                              ('userPageURL',
                               'user'),
                              ('watchedReviewGroupsURL',
                               'watched-review-groups-resource'),
                              ('watchedReviewRequestsURL',
                               'watched-review-requests-resource')):
            info[key] = local_site_reverse(
                url_name,
                request=request,
                kwargs={
                    'username': username,
                })

        if profile is not None:
            cur_timezone = pytz.timezone(profile.timezone)
            use_rich_text = profile.should_use_rich_text
            info.update({
                'commentsOpenAnIssue': profile.open_an_issue,
                'enableDesktopNotifications':
                    profile.should_enable_desktop_notifications,
            })
        else:
            cur_timezone = timezone.get_current_timezone()
            use_rich_text = siteconfig.get('default_use_rich_text')

        if siteconfig.get('avatars_enabled'):
            avatar_service = avatar_services.for_user(user)

            if avatar_service is None:
                logger.error('Could not get a suitable avatar service for '
                             'user %s in js_session_info().',
                             user,
                             extra={'request': request})
            else:
                # Fetch a 32x32 avatar URL (and any variants for different
                # screen DPIs). We only fetch 32x32 for historical reasons,
                # but may want to extend this in the future for additional
                # sizes.
                for size in (32,):
                    avatar_urls[size] = avatar_service.get_avatar_urls(
                        request=request,
                        user=user,
                        size=size)
                    avatar_html[size] = avatar_service.render(
                        request=request,
                        user=user,
                        size=size)

        info.update({
            'avatarHTML': avatar_html,
            'avatarURLs': avatar_urls,
            'defaultUseRichText': use_rich_text,
            'timezoneOffset': dateformat.format(datetime.now(tz=cur_timezone),
                                                'O'),
        })
    else:
        # Anonymous users.
        info['loginURL'] = local_site_reverse('login',
                                              request=request)

    return json_dumps(info)


@register.simple_tag(takes_context=True)
def user_badges(
    context: Context,
    user: User,
) -> SafeString:
    """Return badges shown for a user.

    This will query for any badges provided for a user and return HTML
    rendering them. No order is guaranteed.

    Version Added:
        7.1

    Args:
        context (django.template.context.Context):
            The template rendering context.

        user (django.contrib.auth.models.User):
            The user to query for badges.

    Returns:
        django.utils.safestring.SafeString:
        The HTML containing badges for the user.
    """
    if not user:
        return mark_safe('')

    assert isinstance(user, User), f'{user!r} must be a User'

    def _iter_badges() -> Iterator[SafeString]:
        request = context['request']

        if request is not None:
            local_site = request.local_site
        else:
            local_site = None

        for provider in user_details_provider_registry:
            try:
                badges = provider.get_user_badges(user=user,
                                                  local_site=local_site,
                                                  request=request)

                for user_badge in badges:
                    yield user_badge.render_to_string()
            except Exception as e:
                logger.exception(
                    'Unexpected error when fetching user badges from provider '
                    '%r: %s',
                    provider, e)

    badges_html = format_html_join('', '{}', (
        (html,)
        for html in _iter_badges()
    ))

    if badges_html:
        return format_html('<div class="rb-c-user-badges">{}</div>',
                           badges_html)
    else:
        return mark_safe('')
