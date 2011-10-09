from django import template
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.template.context import RequestContext
from djblets.siteconfig.models import SiteConfiguration

from reviewboard import get_version_string
from reviewboard.admin import widgets
from reviewboard.admin.cache_stats import get_has_cache_stats
from reviewboard.reviews.models import DefaultReviewer, Group
from reviewboard.scmtools.models import Repository


register = template.Library()


@register.inclusion_tag('admin/subnav_item.html', takes_context=True)
def admin_subnav(context, url_name, name, icon=""):
    """
    Returns a <li> containing a link to the desired setting tab.
    """
    request = context.get('request')
    url = reverse(url_name)

    return RequestContext(request, {
        'url': url,
        'name': name,
        'current': url == request.path,
        'icon': icon,
     })


@register.inclusion_tag('admin/admin_widget.html', takes_context=True)
def admin_widget(context, widget_name, widget_title, widget_icon=""):
    """Renders a widget with the given information.

    The widget will be created and returned as HTML. Any states in the
    database will be loaded into the rendered widget.
    """
    request = context.get('request')

    widget_list = {
        'user-activity': widgets.get_user_activity_widget,
        'request-statuses': widgets.get_request_statuses,
        'repositories': widgets.get_repositories,
        'review-groups': widgets.get_groups,
        'server-cache': widgets.get_server_cache,
        'news': widgets.get_news,
        'stats': widgets.get_stats,
        'stats-large': widgets.get_large_stats,
        'recent-actions': widgets.get_recent_actions,
    }

    widget_data = widget_list.get(widget_name)(request)
    siteconfig = SiteConfiguration.objects.get(site=Site.objects.get_current())
    widget_states = siteconfig.get("widget_settings")

    if widget_states:
        widget_state = widget_states.get(widget_name, '0')
    else:
        widget_state = ''

    return RequestContext(context['request'], {
       'widget_title': widget_title,
       'widget_state': widget_state,
       'widget_name': widget_name,
       'widget_icon': widget_icon,
       'widget_size': widget_data['size'],
       'widget_data': widget_data['data'],
       'widget_content': widget_data['template'],
       'widget_actions': widget_data['actions'],
     })


@register.inclusion_tag('admin/widgets/w-actions.html', takes_context=True)
def admin_actions(context):
    """Admin Sidebar with configuration links and setting indicators."""
    request = context.get('request')

    if '_popup' not in request.REQUEST or 'pop' not in request.REQUEST:
        request_context = {
            'show_sidebar': True,
            'count_users': User.objects.count(),
            'count_review_groups': Group.objects.count(),
            'count_default_reviewers': DefaultReviewer.objects.count(),
            'count_repository':
                Repository.objects.accessible(request.user).count(),
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
    if pattern in request.path:
        return 'nav-active'

    return ''
