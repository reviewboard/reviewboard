from __future__ import unicode_literals

import re

from django import template
from django.contrib import messages
from django.contrib.admin.templatetags.admin_urls import (
    add_preserved_filters,
    admin_urlname,
    admin_urlquote)
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.template.context import RequestContext
from django.utils import six
from django.utils.safestring import mark_safe
from djblets.util.templatetags.djblets_js import json_dumps_items

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

    # We're precomputing URLs in here, rather than computing them in the
    # template, because we need to always ensure that reverse() will be
    # searching all available URL patterns and not just the ones bound to
    # request.current_app.
    #
    # current_app gets set by AdminSite views, and if we're in an extension's
    # AdminSite view, we'll fail to resolve these URLs from within the
    # template. We don't have that problem if calling reverse() ourselves.
    request_context.update({
        'url_%s' % url_name: reverse('admin:%s' % url_name)
        for url_name in ('auth_user_add',
                         'auth_user_changelist',
                         'hostingsvcs_hostingserviceaccount_add',
                         'hostingsvcs_hostingserviceaccount_changelist',
                         'notifications_webhooktarget_add',
                         'notifications_webhooktarget_changelist',
                         'oauth_application_add',
                         'oauth_application_changelist',
                         'reviews_defaultreviewer_add',
                         'reviews_defaultreviewer_changelist',
                         'reviews_group_add',
                         'reviews_group_changelist',
                         'scmtools_repository_add',
                         'scmtools_repository_changelist')
    })

    return RequestContext(request, request_context)


@register.simple_tag
def alert_css_classes_for_message(message):
    """Render the CSS classes for a rb-c-alert from a Django Message.

    This helps to craft an alert that reflects the status of a
    :py:class:`~django.contrib.messages.storage.base.Message`.

    This will include a CSS modifier class reflecting the status of the
    message and any extra tags defined on the message.

    Args:
        message (django.contrib.messages.storage.base.Message):
            The message to render classes for.

    Returns:
        unicode:
        A space-separated list of classes.
    """
    status_class = {
        messages.DEBUG: '-is-info',
        messages.INFO: '-is-info',
        messages.SUCCESS: '-is-success',
        messages.WARNING: '-is-warning',
        messages.ERROR: '-is-error',
    }[message.level]

    if message.extra_tags:
        return '%s %s' % (status_class, message.extra_tags)

    return status_class


@register.filter
def split_error_title_text(error):
    """Split an exception's text into a title and body text.

    Args:
        error (Exception):
            The error containing text to split.

    Returns:
        tuple:
        A tuple containing:

        1. The title text.
        2. The rest of the error message (or ``None``).
    """
    return six.text_type(error).split('\n', 1)


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

    return json_dumps_items(model_data)


@register.inclusion_tag('admin/submit_line.html', takes_context=True)
def change_form_submit_buttons(context):
    """Return HTML for a change form's submit buttons.

    This will compute the correct set of Save/Delete buttons, based on whether
    this is rendering for a Django admin change form (taking into account
    the object's state and user's permissions) or for any other type of form.

    Args:
        context (django.template.Context):
            The context for the page.

    Returns:
        django.utils.safestring.SafeText:
        A string containing the submit buttons.
    """
    show_save = context.get('show_save', True)
    delete_url = None

    if 'change' in context:
        change = context['change']
        is_popup = context['is_popup']
        show_delete = context.get('show_delete', True)

        if is_popup:
            show_delete = False
            show_save_as_new = False
            show_save_and_add_another = False
            show_save_and_continue = False
        else:
            save_as = context['save_as']
            opts = context['opts']
            original = context['original']

            show_delete = (
                change and
                context.get('show_delete', True) and
                context['has_delete_permission'])
            show_save_as_new = (
                save_as and
                change)
            show_save_and_add_another = (
                (not save_as or context['add']) and
                context['has_add_permission'])
            show_save_and_continue = (
                context.get('show_save_and_continue', True) and
                context['has_change_permission'])

            if show_delete:
                assert original is not None

                delete_url = add_preserved_filters(
                    context,
                    reverse(admin_urlname(opts, 'delete'),
                            args=[admin_urlquote(original.pk)]))
    else:
        delete_url = context.get('delete_url', '#')
        show_delete = context.get('show_delete', False)
        show_save_as_new = context.get('show_save_as_new', False)
        show_save_and_add_another = context.get('show_save_and_add_another',
                                                False)
        show_save_and_continue = context.get('show_save_and_continue', False)

    return {
        'delete_url': delete_url,
        'show_delete_link': show_delete,
        'show_save': show_save,
        'show_save_and_add_another': show_save_and_add_another,
        'show_save_and_continue': show_save_and_continue,
        'show_save_as_new': show_save_as_new,
    }


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
