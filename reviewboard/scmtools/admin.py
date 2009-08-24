from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from reviewboard.scmtools.forms import RepositoryForm
from reviewboard.scmtools.models import Repository, Tool


class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'path')
    fieldsets = (
        (_('General Information'), {
            'fields': ('name', 'path', 'mirror_path', 'tool', 'bug_tracker'),
            'classes': ('wide',),
        }),
        (_('Authentication'), {
            'fields': ('username', 'password'),
        }),
        (_('Advanced'), {
            'fields': ('encoding',),
        }),
    )
    form = RepositoryForm


class ToolAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'class_name')


admin.site.register(Repository, RepositoryAdmin)
admin.site.register(Tool, ToolAdmin)
