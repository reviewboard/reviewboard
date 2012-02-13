from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from reviewboard.scmtools.forms import RepositoryForm
from reviewboard.scmtools.models import Repository, Tool


class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'path', 'visible')
    fieldsets = (
        (_('General Information'), {
            'fields': ('name', 'visible',),
            'classes': ('wide',),
        }),
        (_('Repository Hosting'), {
            'fields': (
                'hosting_type',
                'tool',
                'hosting_owner',
                'hosting_project_name',
                'path',
                'mirror_path',
                'raw_file_url',
                'github_api_token',
                'username',
                'password',
                'project_slug',
                'repository_name',
                'codebase_repo_name',
                'codebase_group_name',
                'codebase_api_username',
                'codebase_api_key',
            ),
            'classes': ('wide',),
        }),
        (_('Bug Tracker'), {
            'fields': (
                'bug_tracker_use_hosting',
                'bug_tracker_type',
                'bug_tracker_owner',
                'bug_tracker_project_name',
                'bug_tracker_base_url',
                'bug_tracker',
            ),
            'classes': ('wide',),
        }),
        (_('Access Control'), {
            'fields': ('public', 'users', 'review_groups'),
            'classes': ('wide',),
        }),
        (_('Advanced'), {
            'fields': ('encoding',),
            'classes': ('wide',),
        }),
        (_('State'), {
            'description': _('<p>This is advanced state that should not be '
                             'modified unless something is wrong.</p>'),
            'fields': ('local_site',),
            'classes': ['collapse'],
        }),
    )
    form = RepositoryForm


class ToolAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'class_name')


admin.site.register(Repository, RepositoryAdmin)
admin.site.register(Tool, ToolAdmin)
