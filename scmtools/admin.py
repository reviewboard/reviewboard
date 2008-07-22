from django.contrib import admin

from reviewboard.scmtools.models import Repository, Tool


class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'path')


class ToolAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'class_name')


admin.site.register(Repository, RepositoryAdmin)
admin.site.register(Tool, ToolAdmin)
