from admin.cache_stats import get_has_cache_stats

from django import template
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.template.context import RequestContext
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.reviews.models import DefaultReviewer, Group

from reviewboard.admin import widgets
from reviewboard import get_version_string

from scmtools.models import Repository


register = template.Library()


@register.inclusion_tag('admin/subnav_item.html', takes_context=True)
def admin_subnav(context, url_name, name, icon=""):
    """
    Returns a <li> containing a link to the desired setting tab.
    """
    request = context.get('request')
    url = reverse(url_name)

    return RequestContext(context['request'], {
        'url': url,
        'name': name,
        'current': url == request.path,
        'icon': icon
     })

@register.inclusion_tag('admin/admin_widget.html', takes_context=True)
def admin_widget(context, widget_name, widget_title, widget_icon=""):
    """
    Chooses a widget based on the custom tag. Loads the widget states.
    Returns a widget with available data and other information
    """
    request = context.get('request')
    widget_list = {
        'user-activity': widgets.getUserActivityWidget,
        'request-statuses': widgets.getRequestStatuses,
        'repositories': widgets.getRepositories,
        'review-groups': widgets.getGroups,
        'server-cache': widgets.getServerCache,
        'news': widgets.getNews,
        'stats': widgets.getStats,
        'stats-large': widgets.getLargeStats,
        'recent-actions': widgets.getRecentActions
    }

    widget_data = widget_list.get(widget_name)(request)
    siteconfig = SiteConfiguration.objects.get(site=Site.objects.get_current())
    widget_states = siteconfig.get("widget_settings")
    widget_state = ""
    if widget_states:
        if widget_name in widget_states:
            widget_state = widget_states[widget_name]
        else:
            widget_state = "0"

    return RequestContext(context['request'], {
       'widget_title': widget_title,
       'widget_state': widget_state,
       'widget_name': widget_name,
       'widget_icon': widget_icon,
       'widget_size': widget_data['size'],
       'widget_data': widget_data['data'],
       'widget_content': widget_data['template'],
       'widget_actions': widget_data['actions']
     })


@register.inclusion_tag('admin/widgets/w-actions.html', takes_context=True)
def admin_actions(context):
    """ Admin Sidebar with configuration links and setting indicators """
    current_site_config = SiteConfiguration.objects.get_current()
    request = context.get('request')

    if not request.REQUEST.has_key('_popup') \
        or not request.REQUEST.has_key('pop'):
        site_configs = {
        'read_only': \
            current_site_config.get('auth_anonymous_access'),
        'syntax_highlighting': \
            current_site_config.get('diffviewer_syntax_highlighting'),
        'logging_enabled': \
            current_site_config.get('logging_enabled'),
        'logging_directory': \
            current_site_config.get('logging_directory'),
        'logging_allow_profiling': \
            current_site_config.get('logging_allow_profiling'),
        'mail_use_tls': \
            current_site_config.get('mail_use_tls'),
        'mail_send_review_mail': \
            current_site_config.get('mail_send_review_mail'),
        'search_enable': current_site_config.get('search_enable')
        }
        return RequestContext(context['request'], {
            'request': request,
            'show_sidebar': True,
            'count_users': User.objects.count(),
            'count_review_groups': Group.objects.count(),
            'count_default_reviewers': DefaultReviewer.objects.count(),
            'count_repository': Repository.objects.accessible(request.user)\
                .count(),
            'has_cache_stats': get_has_cache_stats(),
            'site_configs': site_configs,
            'version': get_version_string()
        })
    else:
        return RequestContext(context['request'], {
            'show_sidebar': False
        })

@register.simple_tag
def nav_active(request, pattern):
    if pattern in request.path:
        return 'nav-active'

    return ''