from __future__ import unicode_literals

import json
import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_protect
from djblets.cache.forwarding_backend import DEFAULT_FORWARD_CACHE_ALIAS
from djblets.siteconfig.models import SiteConfiguration
from djblets.siteconfig.views import site_settings as djblets_site_settings
from djblets.util.compat.django.shortcuts import render
from djblets.util.compat.django.template.loader import render_to_string

from reviewboard.accounts.models import Profile
from reviewboard.admin.cache_stats import get_cache_stats
from reviewboard.admin.decorators import superuser_required
from reviewboard.admin.forms import SSHSettingsForm
from reviewboard.admin.security_checks import SecurityCheckRunner
from reviewboard.admin.support import get_support_url, serialize_support_data
from reviewboard.admin.widgets import (dynamic_activity_data,
                                       primary_widgets,
                                       secondary_widgets)
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.utils import humanize_key


@staff_member_required
def dashboard(request, template_name="admin/dashboard.html"):
    """Display the administration dashboard.

    This is the entry point to the admin site, containing news updates and
    useful administration tasks.
    """
    return render(
        request=request,
        template_name=template_name,
        context={
            'widgets': primary_widgets + secondary_widgets,
            'root_path': reverse('admin:index'),
            'title': _('Admin Dashboard'),
            'page_model_attrs': {
                'supportData': serialize_support_data(request,
                                                      force_is_admin=True),
            },
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
                    logging.error('Deleting SSH key failed: %s' % e)
            else:
                try:
                    form.create(request.FILES)
                    return HttpResponseRedirect('.')
                except Exception as e:
                    # Fall through. It will be reported inline and in the log.
                    logging.error('Uploading SSH key failed: %s' % e)
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
            'key': key,
            'fingerprint': fingerprint,
            'public_key': client.get_public_key(key),
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
