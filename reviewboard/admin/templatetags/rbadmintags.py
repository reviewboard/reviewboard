from __future__ import unicode_literals

from django import template
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.template.context import RequestContext
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import basictag

from reviewboard import get_version_string
from reviewboard.admin.cache_stats import get_has_cache_stats
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.notifications.models import WebHookTarget
from reviewboard.reviews.models import DefaultReviewer, Group
from reviewboard.scmtools.models import Repository
from reviewboard.site.urlresolvers import local_site_reverse


register = template.Library()


@register.inclusion_tag('admin/subnav_item.html', takes_context=True)
def admin_subnav(context, url_name, name, icon=""):
    """Return an <li> containing a link to the desired setting tab."""
    request = context.get('request')
    url = local_site_reverse(url_name, request=request)

    return RequestContext(
        request, {
            'url': url,
            'name': name,
            'current': url == request.path,
            'icon': icon,
        })


@register.tag
@basictag(takes_context=True)
def admin_widget(context, widget):
    """Render a widget with the given information.

    The widget will be created and returned as HTML. Any states in the
    database will be loaded into the rendered widget.
    """
    request = context.get('request')

    siteconfig = SiteConfiguration.objects.get(site=Site.objects.get_current())
    widget_states = siteconfig.get("widget_settings")

    if widget_states:
        widget.collapsed = widget_states.get(widget.name, "0") != '0'
    else:
        widget.collapsed = False

    return widget.render(request)


@register.inclusion_tag('admin/widgets/w-actions.html', takes_context=True)
def admin_actions(context):
    """Render the admin sidebar.

    This includes the configuration links and setting indicators.
    """
    request = context.get('request')

    if '_popup' not in request.REQUEST or 'pop' not in request.REQUEST:
        request_context = {
            'show_sidebar': True,
            'count_users': User.objects.count(),
            'count_review_groups': Group.objects.count(),
            'count_default_reviewers': DefaultReviewer.objects.count(),
            'count_repository': Repository.objects.accessible(
                request.user, visible_only=False).count(),
            'count_webhooks': WebHookTarget.objects.count(),
            'count_hosting_accounts': HostingServiceAccount.objects.count(),
            'has_cache_stats': get_has_cache_stats(),
            'version': get_version_string(),
        }
    else:
        request_context = {
            'show_sidebar': False,
        }

    return RequestContext(request, request_context)


@register.simple_tag
def nav_active(request, pattern):
    """Helper to render a class name for active navigation items.

    This will check to see if the given pattern is part of the current page's
    URL, and if so, return a class name to add to the navigation element.
    """
    if pattern in request.path:
        return 'nav-active'

    return ''
