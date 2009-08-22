from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from reviewboard.scmtools.forms import RepositoryForm
from reviewboard.scmtools.models import Repository, Tool


class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'path')
    fieldsets = (
        (_('General Information'), {
            'fields': ('name',),
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
                'username',
                'password',
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
        (_('Advanced'), {
            'fields': ('encoding',),
            'classes': ('wide',),
        }),
    )
    form = RepositoryForm


class ToolAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'class_name')


admin.site.register(Repository, RepositoryAdmin)
admin.site.register(Tool, ToolAdmin)
