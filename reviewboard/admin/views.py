from __future__ import unicode_literals

import json
import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.html import format_html_join
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_protect
from djblets.cache.forwarding_backend import DEFAULT_FORWARD_CACHE_ALIAS
from djblets.siteconfig.views import site_settings as djblets_site_settings
from djblets.util.compat.django.shortcuts import render
from djblets.util.compat.django.template.loader import render_to_string

from reviewboard.admin.cache_stats import get_cache_stats
from reviewboard.admin.decorators import superuser_required
from reviewboard.admin.forms.ssh_settings import SSHSettingsForm
from reviewboard.admin.security_checks import SecurityCheckRunner
from reviewboard.admin.support import get_support_url, serialize_support_data
from reviewboard.admin.widgets import (admin_widgets_registry,
                                       dynamic_activity_data)
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.utils import humanize_key


logger = logging.getLogger(__name__)


@staff_member_required
def admin_dashboard_view(request):
    """Display the administration dashboard.

    This is the entry point to the admin site, containing news updates and
    useful administration tasks.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

    Returns:
        django.http.HttpResponse:
        The resulting HTTP response for the view.
    """
    widgets_info = []
    widgets_html = []

    for widget_cls in admin_widgets_registry:
        try:
            widget = widget_cls()

            if not widget.can_render(request):
                continue

            if widget.dom_id is None:
                widget.dom_id = 'admin-widget-%s' % widget.widget_id

            widget_info = {
                'id': widget.widget_id,
                'domID': widget.dom_id,
                'viewClass': widget.js_view_class,
                'modelClass': widget.js_model_class,
            }

            js_view_options = widget.get_js_view_options(request)
            js_model_attrs = widget.get_js_model_attrs(request)
            js_model_options = widget.get_js_model_options(request)

            if js_view_options:
                widget_info['viewOptions'] = js_view_options

            if js_model_attrs:
                widget_info['modelAttrs'] = js_model_attrs

            if js_model_options:
                widget_info['modelOptions'] = js_model_options

            widget_html = widget.render(request)
        except Exception as e:
            logger.exception('Error setting up administration widget %r: %s',
                             widget_cls, e)
            continue

        widgets_info.append(widget_info)
        widgets_html.append((widget_html,))

    return render(
        request=request,
        template_name='admin/dashboard.html',
        context={
            'page_model_attrs': {
                'supportData': serialize_support_data(request,
                                                      force_is_admin=True),
                'widgetsData': widgets_info,
            },
            'title': _('Admin Dashboard'),
            'widgets_html': format_html_join('', '{0}', widgets_html),
        })


@staff_member_required
def cache_stats(request, template_name="admin/cache_stats.html"):
    """Display statistics on the cache.

    This includes such pieces of information as memory used, cache misses, and
    uptime.
    """
    cache_stats = get_cache_stats()
    cache_info = settings.CACHES[DEFAULT_FORWARD_CACHE_ALIAS]

    return render(
        request=request,
        template_name=template_name,
        context={
            'cache_hosts': cache_stats,
            'cache_backend': cache_info['BACKEND'],
            'title': _('Server Cache'),
            'root_path': reverse('admin:index'),
        })


@staff_member_required
def security(request, template_name="admin/security.html"):
    """Run security checks and report the results."""
    runner = SecurityCheckRunner()
    results = runner.run()

    return render(
        request=request,
        template_name=template_name,
        context={
            'test_results': results,
            'title': _('Security Checklist'),
        })


@superuser_required
def site_settings(request, form_class, template_name='admin/settings.html'):
    """Render the general site settings page."""
    return djblets_site_settings(request, form_class, template_name, {
        'root_path': reverse('admin:index'),
    })


@csrf_protect
@superuser_required
def ssh_settings(request, template_name='admin/ssh_settings.html'):
    """Render the SSH settings page."""
    client = SSHClient()
    key = client.get_user_key()

    if request.method == 'POST':
        form = SSHSettingsForm(request.POST, request.FILES)

        if form.is_valid():
            if form.did_request_delete() and client.get_user_key() is not None:
                try:
                    form.delete()
                    return HttpResponseRedirect('.')
                except Exception as e:
                    logger.error('Deleting SSH key failed: %s' % e)
            else:
                try:
                    form.create(request.FILES)
                    return HttpResponseRedirect('.')
                except Exception as e:
                    # Fall through. It will be reported inline and in the log.
                    logger.error('Uploading SSH key failed: %s' % e)
    else:
        form = SSHSettingsForm()

    if key:
        fingerprint = humanize_key(key)
    else:
        fingerprint = None

    return render(
        request=request,
        template_name=template_name,
        context={
            'has_file_field': True,
            'key': key,
            'fingerprint': fingerprint,
            'public_key': client.get_public_key(key).replace('\n', ''),
            'form': form,
        })


def manual_updates_required(request, updates):
    """Render a page showing required updates that the admin must make.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        updates (list):
            The list of required updates to display on the page.

    Returns:
        django.http.HttpResponse:
        The response to send to the client.
    """
    return render(
        request=request,
        template_name='admin/manual_updates_required.html',
        context={
            'updates': [
                render_to_string(template_name=update_template_name,
                                 context=extra_context,
                                 request=request)
                for update_template_name, extra_context in updates
            ],
        })


def widget_activity(request):
    """Return JSON data for the admin activity widget."""
    activity_data = dynamic_activity_data(request)

    return HttpResponse(json.dumps(activity_data),
                        content_type="application/json")


def support_redirect(request, **kwargs):
    """Return an HttpResponseRedirect to the Beanbag support page."""
    return HttpResponseRedirect(get_support_url(request))
