from django.contrib import admin

from reviewboard.accounts.models import ReviewRequestVisit, Profile


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'first_time_setup_done')
    raw_id_fields = ('user', 'starred_review_requests', 'starred_groups')


admin.site.register(ReviewRequestVisit)
admin.site.register(Profile, ProfileAdmin)
