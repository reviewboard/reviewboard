from __future__ import unicode_literals

from django.contrib import admin
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from reviewboard.accounts.admin import fix_review_counts
from reviewboard.scmtools.forms import RepositoryForm
from reviewboard.scmtools.models import Repository, Tool


class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'path', 'hosting', 'visible')
    raw_id_fields = ('local_site',)
    fieldsets = (
        (_('General Information'), {
            'fields': ('name', 'visible',),
            'classes': ('wide',),
        }),
        (_('Repository Hosting'), {
            'fields': (
                'hosting_type',
                'hosting_url',
                'hosting_account',
                'hosting_account_username',
                'hosting_account_password',
                'hosting_account_two_factor_auth_code',
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
            'fields': ('local_site', 'extra_data'),
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
