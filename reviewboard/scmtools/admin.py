from __future__ import unicode_literals

from django.contrib import admin
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from reviewboard.accounts.admin import fix_review_counts
from reviewboard.admin.server import get_server_url
from reviewboard.scmtools.forms import RepositoryForm
from reviewboard.scmtools.models import Repository, Tool


class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'path', 'hosting', '_visible', 'inline_actions')
    list_select_related = ('hosting_account',)
    search_fields = ('name', 'path', 'mirror_path', 'tool__name')
    raw_id_fields = ('local_site',)
    ordering = ('name',)
    fieldsets = (
        (_('General Information'), {
            'fields': ('name', 'visible',),
            'classes': ('wide',),
        }),
        (RepositoryForm.REPOSITORY_HOSTING_FIELDSET, {
            'fields': (
                'hosting_type',
                'hosting_account',
            ),
            'classes': ('wide',),
        }),
        (RepositoryForm.REPOSITORY_INFO_FIELDSET, {
            'fields': (
                'tool',
                'repository_plan',
                'path',
                'mirror_path',
                'raw_file_url',
                'username',
                'password',
                'use_ticket_auth',
            ),
            'classes': ('wide',),
        }),
        (RepositoryForm.SSH_KEY_FIELDSET, {
            'fields': (
                'associate_ssh_key',
            ),
            'classes': ('wide',),
        }),
        (RepositoryForm.BUG_TRACKER_FIELDSET, {
            'fields': (
                'bug_tracker_use_hosting',
                'bug_tracker_type',
                'bug_tracker_hosting_url',
                'bug_tracker_plan',
                'bug_tracker_hosting_account_username',
                'bug_tracker',
            ),
            'classes': ('wide',),
        }),
        (_('Access Control'), {
            'fields': ('public', 'users', 'review_groups'),
            'classes': ('wide',),
        }),
        (_('Advanced Settings'), {
            'fields': ('encoding',),
            'classes': ('wide', 'collapse'),
        }),
        (_('Internal State'), {
            'description': _('<p>This is advanced state that should not be '
                             'modified unless something is wrong.</p>'),
            'fields': ('local_site', 'hooks_uuid', 'extra_data'),
            'classes': ['collapse'],
        }),
    )
    form = RepositoryForm

    def hosting(self, repository):
        if repository.hosting_account_id:
            account = repository.hosting_account

            if account.service:
                return '%s@%s' % (account.username, account.service.name)

        return ''
    hosting.short_description = _('Hosting Service Account')

    def inline_actions(self, repository):
        s = ['<div class="admin-inline-actions">']

        if repository.hosting_account:
            service = repository.hosting_account.service

            if service and service.has_repository_hook_instructions:
                s.append(format_html(
                    '<a class="action-hooks-setup"'
                    '   href="{0}/hooks-setup/">[{1}]</a>',
                    repository.pk, _('Hooks')))

        s.append(format_html(
            '<a class="action-rbtools-setup"'
            '   href="{0}/rbtools-setup/">[{1}]</a>',
            repository.pk, _('RBTools Setup')))

        s.append('</div>')

        return ''.join(s)
    inline_actions.allow_tags = True
    inline_actions.short_description = ''

    def _visible(self, repository):
        return repository.visible
    _visible.boolean = True
    _visible.short_description = _('Show')

    def get_urls(self):
        from django.conf.urls import patterns

        return patterns(
            '',

            (r'^(?P<repository_id>[0-9]+)/hooks-setup/$',
             self.admin_site.admin_view(self.hooks_setup)),

            (r'^(?P<repository_id>[0-9]+)/rbtools-setup/$',
             self.admin_site.admin_view(self.rbtools_setup)),
        ) + super(RepositoryAdmin, self).get_urls()

    def hooks_setup(self, request, repository_id):
        repository = get_object_or_404(Repository, pk=repository_id)

        if repository.hosting_account:
            service = repository.hosting_account.service

            if service and service.has_repository_hook_instructions:
                return HttpResponse(service.get_repository_hook_instructions(
                    request, repository))

        return HttpResponseNotFound()

    def rbtools_setup(self, request, repository_id):
        repository = get_object_or_404(Repository, pk=repository_id)

        return render_to_response(
            'admin/scmtools/repository/rbtools_setup.html',
            RequestContext(request, {
                'repository': repository,
                'reviewboard_url': get_server_url(
                    local_site=repository.local_site),
            }))


@receiver(pre_delete, sender=Repository,
          dispatch_uid='repository_delete_reset_review_counts')
def repository_delete_reset_review_counts(sender, instance, using, **kwargs):
    """Reset review counts in the dashboard when deleting repository objects.

    There doesn't seem to be a good way to get notified on cascaded delete
    operations, which means that when deleting a repository, there's no
    good way to update the review counts that are shown to users. This
    method clears them out entirely to be regenerated. Deleting
    repositories should be a very rare occurrance, so it's not too
    upsetting to do this.
    """
    fix_review_counts()


class ToolAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'class_name')


admin.site.register(Repository, RepositoryAdmin)
admin.site.register(Tool, ToolAdmin)
