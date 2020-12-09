"""Account-related template tags."""

from __future__ import unicode_literals

import logging
from datetime import datetime

import pytz
from django import template
from django.utils import dateformat, timezone
from django.utils.html import escape
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.templatetags.djblets_js import json_dumps

from reviewboard.admin.read_only import is_site_read_only_for
from reviewboard.avatars import avatar_services
from reviewboard.site.urlresolvers import local_site_reverse


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
    authenticated = user.is_authenticated()

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
                             user)
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
