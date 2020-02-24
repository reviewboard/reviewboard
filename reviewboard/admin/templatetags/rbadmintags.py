from __future__ import unicode_literals

import re

from django import template
from django.contrib.auth.models import User
from django.template.context import RequestContext
from django.utils.safestring import mark_safe
from djblets.util.templatetags.djblets_js import json_dumps

from reviewboard import get_version_string
from reviewboard.admin.forms.change_form import ChangeFormFieldset
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.notifications.models import WebHookTarget
from reviewboard.oauth.models import Application
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
            'current': request is not None and url == request.path,
            'icon': icon,
        })


@register.inclusion_tag('admin/sidebar.html', takes_context=True)
def admin_sidebar(context):
    """Render the admin sidebar.

    This includes the configuration links and setting indicators.
    """
    request = context.get('request')

    request_context = {
        'count_users': User.objects.count(),
        'count_review_groups': Group.objects.count(),
        'count_default_reviewers': DefaultReviewer.objects.count(),
        'count_oauth_applications': Application.objects.count(),
        'count_repository': Repository.objects.accessible(
            request.user, visible_only=False).count(),
        'count_webhooks': WebHookTarget.objects.count(),
        'count_hosting_accounts': HostingServiceAccount.objects.count(),
        'version': get_version_string(),
    }

    return RequestContext(request, request_context)


@register.simple_tag()
def process_result_headers(result_headers):
    """Process a Django ChangeList's result headers to aid in rendering.

    This will provide better information for our template so that we can
    more effectively render a datagrid.

    Args:
        result_headers (list of dict):
            The result headers to modify.
    """
    class_attrib_re = re.compile(r'\s*class="([^"]+)"')

    for header in result_headers:
        m = class_attrib_re.match(header['class_attrib'])

        if m:
            class_value = m.groups(1)[0]
        else:
            class_value = ''

        if class_value != 'action-checkbox-column':
            class_value = 'has-label %s' % class_value

        header['class_attrib'] = \
            mark_safe(' class="datagrid-header %s"' % class_value)

        if header['sortable'] and header['sort_priority'] > 0:
            if header['ascending']:
                sort_order = 'asc'
            else:
                sort_order = 'desc'

            if header['sort_priority'] == 1:
                sort_priority = 'primary'
            else:
                sort_priority = 'secondary'

            header['sort_icon'] = 'datagrid-icon-sort-%s-%s' % (
                sort_order, sort_priority)

    return ''


@register.simple_tag(takes_context=True)
def changelist_js_model_attrs(context):
    """Return serialized JSON attributes for the RB.Admin.ChangeListPage model.

    These will all be passed to the :js:class:`RB.Admin.ChangeListPage`
    constructor.

    Args:
        context (django.template.Context):
            The context for the page.

    Returns:
        django.utils.safestring.SafeText:
        A string containing the JSON attributes for the page model.
    """
    action_form = context.get('action_form')
    cl = context['cl']

    model_data = {
        'modelName': cl.opts.verbose_name,
        'modelNamePlural': cl.opts.verbose_name_plural,
    }

    if action_form is not None:
        action_choices = action_form.fields['action'].choices

        model_data['actions'] = [
            {
                'id': action_id,
                'label': action_label,
            }
            for action_id, action_label in action_choices
            if action_id
        ]

    return json_dumps(model_data)


@register.filter
def change_form_fieldsets(admin_form):
    """Iterate through all fieldsets in an administration change form.

    This will provide each field as a
    :py:class:`~reviewboard.admin.forms.change_form.ChangeFormFieldset`.

    Args:
        admin_form (django.contrib.admin.helpers.AdminForm):
            The administration form.

    Yields:
        reviewboard.admin.forms.change_form.ChangeFormFieldset:
        Each fieldset in the form.
    """
    form = admin_form.form
    readonly_fields = admin_form.readonly_fields
    model_admin = admin_form.model_admin

    for name, options in admin_form.fieldsets:
        yield ChangeFormFieldset(form=form,
                                 name=name,
                                 readonly_fields=readonly_fields,
                                 model_admin=model_admin,
                                 **options)


@register.simple_tag(takes_context=True)
def render_change_form_fieldset(context, fieldset):
    """Render a Change Form fieldset.

    This will render a
    :py:class:`~reviewboard.admin.forms.change_form.ChangeFormFieldset` to
    HTML.

    Args:
        context (django.template.Context):
            The current template context.

        fieldset (reviewboard.admin.forms.change_form.ChangeFormFieldset):
            The fieldset to render.

    Returns:
        django.utils.safestring.SafeText:
        The resulting HTML for the fieldset.
    """
    return fieldset.render(context)
