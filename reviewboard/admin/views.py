from __future__ import annotations

import json
import logging
from itertools import groupby
from operator import attrgetter
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.http import (Http404,
                         HttpResponse,
                         HttpResponseRedirect,
                         JsonResponse)
from django.shortcuts import render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.html import format_html_join
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.generic.base import View
from djblets.cache.forwarding_backend import DEFAULT_FORWARD_CACHE_ALIAS
from djblets.siteconfig.views import site_settings as djblets_site_settings

from reviewboard.admin.cache_stats import get_cache_stats
from reviewboard.admin.decorators import superuser_required
from reviewboard.admin.forms.ssh_settings import SSHSettingsForm
from reviewboard.admin.security_checks import SecurityCheckRunner
from reviewboard.admin.support import get_support_url, serialize_support_data
from reviewboard.admin.widgets import (admin_widgets_registry,
                                       dynamic_activity_data)
from reviewboard.certs.errors import CertificateVerificationError
from reviewboard.hostingsvcs.base import hosting_service_registry
from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            TwoFactorAuthCodeRequiredError)
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.scmtools.errors import \
    UnverifiedCertificateError as LegacyUnverifiedCertificateError
from reviewboard.site.models import LocalSite
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.utils import humanize_key

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.utils.safestring import SafeString

    from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService


logger = logging.getLogger(__name__)


#: Hosting service IDs to highlight in the "Popular" section of the connect UI.
#:
#: Version Added:
#:     9.0
_POPULAR_SERVICE_IDS = {
    'forgejo',
    'github',
    'gitlab',
}


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
                             widget_cls, e, extra={'request': request})
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
def cache_stats(request, template_name='admin/cache_stats.html'):
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
def security(request, template_name='admin/security.html'):
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
                    logger.error('Deleting SSH key failed: %s', e,
                                 extra={'request': request})
            else:
                try:
                    form.create(request.FILES)
                    return HttpResponseRedirect('.')
                except Exception as e:
                    # Fall through. It will be reported inline and in the log.
                    logger.error('Uploading SSH key failed: %s', e,
                                 extra={'request': request})
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
                        content_type='application/json')


def support_redirect(request, **kwargs):
    """Return an HttpResponseRedirect to the Beanbag support page."""
    return HttpResponseRedirect(get_support_url(request))


@method_decorator(
    (staff_member_required, csrf_protect),
    name='dispatch',
)
class ConnectedServicesListView(View):
    """Management view for connected services.

    Version Added:
        9.0
    """

    def get(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Unused positional arguments.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            django.http.HttpResponse:
            The rendered response.
        """
        # Build the list of available services.
        available_services = [
            {
                'id': service.hosting_service_id,
                'name': str(service.name),
                'logo': (static(service.logo_image)
                         if service.logo_image
                         else None),
                'sections': self._get_service_sections(service),
            }
            for service in hosting_service_registry
            if service.visible and service.needs_authorization
        ]

        # Build the list of entries for the page.
        entries: list[tuple[str, SafeString]] = [
            *self._build_hosting_service_entries(request),
            # TODO: integrations and repositories w/o hosting services.
        ]
        entries.sort(key=lambda entry: entry[0])

        # A connect flow that needs to finish in the wizard (such as returning
        # from a GitHub App installation) stashes the step URL in the session.
        # Pop it so the wizard opens on that step once, without reopening on a
        # later refresh. The value is server-built, so it is safe to fetch and
        # inject into the dialog.
        auto_connect_url = request.session.pop('connect_wizard_url', None)

        return render(
            request=request,
            template_name='admin/connected_services/list.html',
            context={
                'auto_connect_url': auto_connect_url,
                'available_services': available_services,
                'service_entries': [entry[1] for entry in entries],
                'title': _('Connected Services'),
            },
        )

    def _build_hosting_service_entries(
        self,
        request: HttpRequest,
    ) -> list[tuple[str, SafeString]]:
        """Build a list of entries for hosting services.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            list of tuple:
            A list of 2-tuples, each of:

            Tuple:
                0 (str):
                    The sort key to use.

                1 (django.utils.safestring.SafeString):
                    The rendered entry.
        """
        accounts = (
            HostingServiceAccount.objects
            .accessible(visible_only=False, local_site=LocalSite.ALL)
            .annotate(repository_count=Count('repositories'))
            .order_by('service_name')
        )

        # Group accounts by the associated hosting service. If there are any
        # accounts whose service cannot be loaded from the registry, they will
        # be grouped under None.
        service_groups: list[tuple[
            type[BaseHostingService] | None,
            list[HostingServiceAccount]]
        ] = []

        for name, group in groupby(accounts, key=attrgetter('service_name')):
            service = hosting_service_registry.get_hosting_service(name)
            service_groups.append((service, list(group)))

        return [
            (
                (service.name or '').lower(),
                service.connect_ui.render_connected_services_list_entry(
                    request,
                    accounts=accounts),
            )
            for service, accounts in service_groups
            if service
        ]

    def _get_service_sections(
        self,
        service: type[BaseHostingService],
    ) -> list[str]:
        """Return the section IDs a service belongs to in the connect UI.

        A service can appear in more than one section.

        Args:
            service (type):
                The hosting service class.

        Returns:
            list of str:
            The section IDs for the service.
        """
        sections: list[str] = []

        if service.hosting_service_id in _POPULAR_SERVICE_IDS:
            sections.append('popular')

        # A service that supports repositories is listed under "Source
        # hosting", even if it also supports bug trackers. Only services that
        # are bug trackers alone are listed under "Issue tracking". This
        # matches the service type shown for connected accounts (see
        # BaseHostingService.make_admin_services_list_entry_context).
        if service.supports_repositories:
            sections.append('source_hosting')
        elif service.supports_bug_trackers:
            sections.append('issue_tracking')

        return sections


@method_decorator(
    (staff_member_required, csrf_protect),
    name='dispatch',
)
class ConnectServiceView(View):
    """View for connecting a hosting service account.

    This handles the per-service step of the "Connect a service" flow. A
    ``GET`` request returns the service-specific connect UI as an HTML
    fragment, and a ``POST`` request processes the authentication form and
    creates the :py:class:`~reviewboard.hostingsvcs.models.
    HostingServiceAccount`.

    Version Added:
        9.0
    """

    def get(
        self,
        request: HttpRequest,
        service_id: str,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            service_id (str):
                The ID of the hosting service to connect.

            *args (tuple):
                Unused positional arguments.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            django.http.HttpResponse:
            The rendered connect UI fragment.
        """
        service = self._get_service(service_id)

        return HttpResponse(service.connect_ui.render_connect_ui(request))

    def post(
        self,
        request: HttpRequest,
        service_id: str,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP POST requests.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            service_id (str):
                The ID of the hosting service to connect.

            *args (tuple):
                Unused positional arguments.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            django.http.JsonResponse:
            A JSON response indicating success (with a redirect URL) or
            failure (with the re-rendered connect UI fragment).
        """
        service = self._get_service(service_id)

        form = service.connect_ui.get_auth_form_class()(
            data=request.POST,
            hosting_service_cls=service)

        if form.is_valid():
            try:
                form.save()
            except ValueError as e:
                form.add_error(None, str(e))
            except TwoFactorAuthCodeRequiredError as e:
                form.add_error(None, str(e))
            except AuthorizationError as e:
                form.add_error(
                    None,
                    _('Unable to link the account: %s') % e)
            except (CertificateVerificationError,
                    LegacyUnverifiedCertificateError) as e:
                form.add_error(None, str(e))
            except Exception as e:
                logger.exception('Unexpected error connecting hosting '
                                 'service "%s": %s',
                                 service_id, e)
                form.add_error(
                    None,
                    _('Unexpected error when linking the account: %s. '
                      'Additional details may be found in the Review Board '
                      'log file.') % e)
            else:
                return JsonResponse({
                    'success': True,
                    'redirect': reverse('connected-services-list'),
                })

        return JsonResponse({
            'success': False,
            'html': service.connect_ui.render_connect_ui(request, form=form),
        })

    def _get_service(
        self,
        service_id: str,
    ) -> type[BaseHostingService]:
        """Return the hosting service for the given ID.

        Args:
            service_id (str):
                The ID of the hosting service.

        Returns:
            type:
            The hosting service class.

        Raises:
            django.http.Http404:
                The service does not exist, is not visible, or does not
                require authorization.
        """
        service = hosting_service_registry.get_hosting_service(service_id)

        if (service is None or
            not service.visible or
            not service.needs_authorization):
            raise Http404

        return service
